/**
 * ChatPanel - Main chat interface component for the Decky sidebar.
 * Handles message sending, display, and connection status.
 */
import { useState, useEffect, useRef, VFC } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  TextField,
  ToggleField,
} from "@decky/ui";
import { call } from "@decky/api";

import { MessageBubble, ChatMessage } from "./MessageBubble";
import { SettingsPanel } from "./SettingsPanel";

export const ChatPanel: VFC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check connection on mount
  useEffect(() => {
    checkConnection();
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** Check if OpenClaw Gateway is reachable */
  const checkConnection = async () => {
    try {
      const result = await call<[], { connected: boolean }>("check_connection");
      setConnected(result.connected);
    } catch {
      setConnected(false);
    }
  };

  /** Send user message to OpenClaw and display response */
  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const result = await call<[string], { success: boolean; data?: any; error?: string }>(
        "send_message",
        text
      );

      if (result.success && result.data) {
        // Extract response text from OpenClaw result
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
          {
            role: "error",
            content: result.error || "Failed to get response",
          },
        ]);
      }
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: e?.message || "Request failed" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  /** Clear all chat messages */
  const clearChat = () => {
    setMessages([]);
    call<[], any>("clear_history");
  };

  // Show settings panel if toggled
  if (showSettings) {
    return (
      <SettingsPanel
        onBack={() => {
          setShowSettings(false);
          checkConnection();
        }}
      />
    );
  }

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
            <span
              style={{
                color: connected ? "#4caf50" : "#f44336",
                fontSize: "13px",
              }}
            >
              {connected ? "● Connected" : "● Disconnected"}
            </span>
            <span
              style={{
                fontSize: "11px",
                color: "#888",
                cursor: "pointer",
                textDecoration: "underline",
              }}
              onClick={() => setShowSettings(true)}
            >
              Settings
            </span>
          </div>
        </PanelSectionRow>
      </PanelSection>

      {/* Messages area */}
      <PanelSection title="Chat">
        <PanelSectionRow>
          <div
            style={{
              maxHeight: "320px",
              overflowY: "auto",
              width: "100%",
              paddingRight: "4px",
            }}
          >
            {messages.length === 0 && (
              <div
                style={{
                  color: "#666",
                  fontSize: "12px",
                  textAlign: "center",
                  padding: "20px 0",
                }}
              >
                Send a message to start chatting with OpenClaw
              </div>
            )}
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            {loading && (
              <div
                style={{
                  color: "#888",
                  fontSize: "12px",
                  padding: "6px 10px",
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
            {loading ? "Sending..." : "Send"}
          </ButtonItem>
        </PanelSectionRow>
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
