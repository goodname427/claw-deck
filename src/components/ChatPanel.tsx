/**
 * ChatPanel - Main chat interface component for the Decky sidebar.
 * Handles message sending (HTTP + WebSocket streaming), display, and connection status.
 */
import { useState, useEffect, useRef, useCallback, VFC } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  TextField,
} from "@decky/ui";
import { call } from "@decky/api";

import { MessageBubble, ChatMessage } from "./MessageBubble";
import { SettingsPanel } from "./SettingsPanel";
import { SkillList } from "./SkillList";
import { VoiceButton } from "./VoiceButton";
import { colors, componentStyles, fontSize, spacing } from "../styles/theme";

/** Interval for polling connection status (ms) */
const CONNECTION_POLL_INTERVAL = 15000;
/** Interval for polling stream chunks (ms) */
const STREAM_POLL_INTERVAL = 200;

export const ChatPanel: VFC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showSkills, setShowSkills] = useState(false);
  const [useStreaming, setUseStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Check connection on mount and start polling
  useEffect(() => {
    checkConnection();
    loadStreamingPref();
    // Start periodic connection polling
    pollTimerRef.current = setInterval(checkConnection, CONNECTION_POLL_INTERVAL);
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** Load streaming preference from backend config */
  const loadStreamingPref = async () => {
    try {
      const config = await call<[], { use_streaming: boolean }>("get_config");
      setUseStreaming(config.use_streaming || false);
    } catch {
      // Ignore
    }
  };

  /** Check if OpenClaw Gateway is reachable */
  const checkConnection = async () => {
    try {
      const result = await call<[], { connected: boolean; ws_connected: boolean }>(
        "check_connection"
      );
      setConnected(result.connected);
      setWsConnected(result.ws_connected || false);
    } catch {
      setConnected(false);
      setWsConnected(false);
    }
  };

  /** Send user message — dispatches to HTTP or streaming based on config */
  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      if (useStreaming) {
        await sendMessageStreaming(text);
      } else {
        await sendMessageHttp(text);
      }
    } finally {
      setLoading(false);
    }
  };

  /** Send via HTTP REST (full response) */
  const sendMessageHttp = async (text: string) => {
    try {
      const result = await call<[string], { success: boolean; data?: any; error?: string }>(
        "send_message",
        text
      );

      if (result.success && result.data) {
        const responseText =
          result.data.response ||
          result.data.content ||
          result.data.message ||
          JSON.stringify(result.data);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: responseText },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "error", content: result.error || "Failed to get response" },
        ]);
      }
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: e?.message || "Request failed" },
      ]);
    }
  };

  /** Send via WebSocket streaming (token-by-token) */
  const sendMessageStreaming = async (text: string) => {
    try {
      // Start stream
      const startResult = await call<[string], { success: boolean; stream_id?: string; error?: string }>(
        "send_message_stream",
        text
      );

      if (!startResult.success || !startResult.stream_id) {
        // Fallback to HTTP if streaming fails
        await sendMessageHttp(text);
        return;
      }

      const streamId = startResult.stream_id;

      // Add a placeholder assistant message for streaming
      const streamMsgIndex = messages.length + 1; // +1 for user msg already added
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", streaming: true },
      ]);

      // Poll for chunks
      let accumulated = "";
      let done = false;

      while (!done) {
        await new Promise((resolve) => setTimeout(resolve, STREAM_POLL_INTERVAL));

        const pollResult = await call<[string], {
          chunks: Array<{ type: string; content: string }>;
          done: boolean;
          error: string | null;
        }>("poll_stream", streamId);

        for (const chunk of pollResult.chunks) {
          if (chunk.type === "token") {
            accumulated += chunk.content;
          } else if (chunk.type === "done") {
            if (chunk.content) {
              accumulated = chunk.content; // Final full content may replace accumulated
            }
          } else if (chunk.type === "error") {
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].streaming) {
                updated[lastIdx] = {
                  role: "error",
                  content: chunk.content || "Stream error",
                };
              }
              return updated;
            });
            return;
          }
        }

        // Update the streaming message with accumulated content
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (lastIdx >= 0 && updated[lastIdx].streaming) {
            updated[lastIdx] = {
              role: "assistant",
              content: accumulated,
              streaming: !pollResult.done,
            };
          }
          return updated;
        });

        if (pollResult.done) {
          done = true;
        }

        if (pollResult.error) {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0) {
              updated[lastIdx] = {
                role: "error",
                content: pollResult.error || "Stream error",
              };
            }
            return updated;
          });
          return;
        }
      }
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: e?.message || "Streaming failed" },
      ]);
    }
  };

  /** Clear all chat messages */
  const clearChat = () => {
    setMessages([]);
    call<[], any>("clear_history");
  };

  /** Handle skill trigger from SkillList — sends skill name as a chat message */
  const handleTriggerSkill = (skillName: string) => {
    setShowSkills(false);
    setInput(`Use skill: ${skillName}`);
  };

  /** Handle voice transcription — populates the input field */
  const handleVoiceTranscription = (text: string) => {
    setInput((prev) => (prev ? prev + " " + text : text));
  };

  // Show settings panel if toggled
  if (showSettings) {
    return (
      <SettingsPanel
        onBack={() => {
          setShowSettings(false);
          checkConnection();
          loadStreamingPref();
        }}
      />
    );
  }

  // Show skills panel if toggled
  if (showSkills) {
    return (
      <SkillList
        onTriggerSkill={handleTriggerSkill}
        onBack={() => setShowSkills(false)}
      />
    );
  }

  /** Connection status label */
  const statusLabel = connected
    ? wsConnected
      ? "● Connected (WS)"
      : "● Connected"
    : "● Disconnected";
  const statusColor = connected ? colors.statusOnline : colors.statusOffline;

  return (
    <>
      {/* Connection status & controls */}
      <PanelSection title="OpenClaw AI">
        <PanelSectionRow>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              width: "100%",
            }}
          >
            <span style={{ ...componentStyles.statusDot, color: statusColor }}>
              {statusLabel}
            </span>
            <div style={{ display: "flex", gap: "10px" }}>
              <span
                style={componentStyles.navLink}
                onClick={() => setShowSkills(true)}
              >
                Skills
              </span>
              <span
                style={componentStyles.navLink}
                onClick={() => setShowSettings(true)}
              >
                Settings
              </span>
            </div>
          </div>
        </PanelSectionRow>
      </PanelSection>

      {/* Messages area */}
      <PanelSection title="Chat">
        <PanelSectionRow>
          <div style={componentStyles.messageList}>
            {messages.length === 0 && (
              <div style={componentStyles.emptyState}>
                Send a message to start chatting with OpenClaw
              </div>
            )}
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            {loading && messages[messages.length - 1]?.role !== "assistant" && (
              <div
                style={{
                  color: colors.textMuted,
                  fontSize: `${fontSize.sm + 1}px`,
                  padding: `${spacing.sm + 2}px ${spacing.lg - 2}px`,
                }}
              >
                Thinking...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </PanelSectionRow>
      </PanelSection>

      {/* Input area */}
      <PanelSection>
        <PanelSectionRow>
          <TextField
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
            placeholder="Ask OpenClaw..."
            disabled={loading || !connected}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={sendMessage}
            disabled={loading || !connected || !input.trim()}
          >
            {loading ? "Sending..." : useStreaming ? "Send (Stream)" : "Send"}
          </ButtonItem>
        </PanelSectionRow>
        <VoiceButton
          onTranscription={handleVoiceTranscription}
          disabled={loading || !connected}
        />
        {messages.length > 0 && (
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={clearChat}>
              Clear Chat
            </ButtonItem>
          </PanelSectionRow>
        )}
      </PanelSection>
    </>
  );
};
