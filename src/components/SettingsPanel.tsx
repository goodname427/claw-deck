/**
 * SettingsPanel - Configuration panel for OpenClaw Gateway connection.
 * Allows users to set HTTP and WebSocket URLs, toggle streaming mode,
 * and manage WebSocket connection.
 */
import { useState, useEffect, VFC } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  TextField,
  ToggleField,
} from "@decky/ui";
import { call } from "@decky/api";
import { colors, componentStyles, fontSize, spacing } from "../styles/theme";

interface SettingsPanelProps {
  onBack: () => void;
}

export const SettingsPanel: VFC<SettingsPanelProps> = ({ onBack }) => {
  const [httpUrl, setHttpUrl] = useState("http://localhost:18789");
  const [wsUrl, setWsUrl] = useState("ws://localhost:18789/ws");
  const [useStreaming, setUseStreaming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [wsConnected, setWsConnected] = useState(false);

  // Load current config on mount
  useEffect(() => {
    loadConfig();
    checkWsStatus();
  }, []);

  /** Fetch current configuration from backend */
  const loadConfig = async () => {
    try {
      const config = await call<[], { http_url: string; ws_url: string; use_streaming: boolean }>(
        "get_config"
      );
      setHttpUrl(config.http_url);
      setWsUrl(config.ws_url);
      setUseStreaming(config.use_streaming || false);
    } catch {
      setStatus("Failed to load config");
    }
  };

  /** Check current WebSocket connection status */
  const checkWsStatus = async () => {
    try {
      const result = await call<[], { connected: boolean; ws_connected: boolean }>(
        "check_connection"
      );
      setWsConnected(result.ws_connected || false);
    } catch {
      setWsConnected(false);
    }
  };

  /** Save configuration to backend */
  const saveConfig = async () => {
    setSaving(true);
    setStatus("");
    try {
      const result = await call<[string, string, boolean], { success: boolean }>(
        "set_config",
        httpUrl,
        wsUrl,
        useStreaming
      );
      if (result.success) {
        setStatus("Saved ✓");
        // Test connection with new config
        const check = await call<[], { connected: boolean; ws_connected: boolean }>(
          "check_connection"
        );
        if (check.connected) {
          setStatus("Saved ✓ — Connected");
        } else {
          setStatus("Saved ✓ — Cannot connect (check URL)");
        }
        setWsConnected(check.ws_connected || false);
      } else {
        setStatus("Failed to save");
      }
    } catch (e: any) {
      setStatus(`Error: ${e?.message || "Unknown"}`);
    } finally {
      setSaving(false);
    }
  };

  /** Manually connect WebSocket */
  const connectWs = async () => {
    setStatus("Connecting WebSocket...");
    try {
      const result = await call<[], { success: boolean; error?: string }>(
        "connect_websocket"
      );
      if (result.success) {
        setWsConnected(true);
        setStatus("WebSocket connected ✓");
      } else {
        setStatus(`WS failed: ${result.error || "Unknown"}`);
      }
    } catch (e: any) {
      setStatus(`WS error: ${e?.message || "Unknown"}`);
    }
  };

  /** Manually disconnect WebSocket */
  const disconnectWs = async () => {
    await call<[], { success: boolean }>("disconnect_websocket");
    setWsConnected(false);
    setStatus("WebSocket disconnected");
  };

  return (
    <>
      <PanelSection title="Settings">
        <PanelSectionRow>
          <div style={{ width: "100%", marginBottom: "8px" }}>
            <div style={componentStyles.fieldLabel}>
              OpenClaw HTTP URL
            </div>
            <TextField
              value={httpUrl}
              onChange={(e) => setHttpUrl(e.target.value)}
              placeholder="http://localhost:18789"
            />
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ width: "100%", marginBottom: "8px" }}>
            <div style={componentStyles.fieldLabel}>
              OpenClaw WebSocket URL
            </div>
            <TextField
              value={wsUrl}
              onChange={(e) => setWsUrl(e.target.value)}
              placeholder="ws://localhost:18789/ws"
            />
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ToggleField
            label="Enable Streaming"
            description="Use WebSocket for token-by-token responses"
            checked={useStreaming}
            onChange={(val) => setUseStreaming(val)}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={saveConfig} disabled={saving}>
            {saving ? "Saving..." : "Save & Test"}
          </ButtonItem>
        </PanelSectionRow>
        {status && (
          <PanelSectionRow>
            <div
              style={{
                ...componentStyles.statusLine,
                color: status.includes("✓") ? colors.statusOnline : colors.statusOffline,
              }}
            >
              {status}
            </div>
          </PanelSectionRow>
        )}
      </PanelSection>

      {/* WebSocket connection controls */}
      <PanelSection title="WebSocket">
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
                color: wsConnected ? colors.statusOnline : colors.statusOffline,
                ...componentStyles.statusDot,
              }}
            >
              {wsConnected ? "● WS Connected" : "● WS Disconnected"}
            </span>
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          {wsConnected ? (
            <ButtonItem layout="below" onClick={disconnectWs}>
              Disconnect WS
            </ButtonItem>
          ) : (
            <ButtonItem layout="below" onClick={connectWs}>
              Connect WS
            </ButtonItem>
          )}
        </PanelSectionRow>
      </PanelSection>

      <PanelSection>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={onBack}>
            ← Back to Chat
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
};
