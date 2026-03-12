/**
 * SettingsPanel - Configuration panel for OpenClaw Gateway connection.
 * Allows users to set HTTP and WebSocket URLs.
 */
import { useState, useEffect, VFC } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  TextField,
} from "@decky/ui";
import { call } from "@decky/api";

interface SettingsPanelProps {
  onBack: () => void;
}

export const SettingsPanel: VFC<SettingsPanelProps> = ({ onBack }) => {
  const [httpUrl, setHttpUrl] = useState("http://localhost:18789");
  const [wsUrl, setWsUrl] = useState("ws://localhost:18789/ws");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  // Load current config on mount
  useEffect(() => {
    loadConfig();
  }, []);

  /** Fetch current configuration from backend */
  const loadConfig = async () => {
    try {
      const config = await call<[], { http_url: string; ws_url: string }>("get_config");
      setHttpUrl(config.http_url);
      setWsUrl(config.ws_url);
    } catch {
      setStatus("Failed to load config");
    }
  };

  /** Save configuration to backend */
  const saveConfig = async () => {
    setSaving(true);
    setStatus("");
    try {
      const result = await call<[string, string], { success: boolean }>(
        "set_config",
        httpUrl,
        wsUrl
      );
      if (result.success) {
        setStatus("Saved ✓");
        // Test connection with new config
        const check = await call<[], { connected: boolean }>("check_connection");
        if (check.connected) {
          setStatus("Saved ✓ — Connected");
        } else {
          setStatus("Saved ✓ — Cannot connect (check URL)");
        }
      } else {
        setStatus("Failed to save");
      }
    } catch (e: any) {
      setStatus(`Error: ${e?.message || "Unknown"}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PanelSection title="Settings">
        <PanelSectionRow>
          <div style={{ width: "100%", marginBottom: "8px" }}>
            <div style={{ fontSize: "12px", color: "#aaa", marginBottom: "4px" }}>
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
            <div style={{ fontSize: "12px", color: "#aaa", marginBottom: "4px" }}>
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
          <ButtonItem layout="below" onClick={saveConfig} disabled={saving}>
            {saving ? "Saving..." : "Save & Test"}
          </ButtonItem>
        </PanelSectionRow>
        {status && (
          <PanelSectionRow>
            <div
              style={{
                fontSize: "12px",
                color: status.includes("✓") ? "#4caf50" : "#f44336",
                textAlign: "center",
                width: "100%",
              }}
            >
              {status}
            </div>
          </PanelSectionRow>
        )}
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
