/**
 * VoiceButton - Push-to-talk style voice input button.
 * Hold to record, release to transcribe via OpenClaw STT.
 * Transcribed text is passed back to the parent via callback.
 */
import { useState, useRef, VFC } from "react";
import {
  PanelSectionRow,
  ButtonItem,
} from "@decky/ui";
import { call } from "@decky/api";
import { colors, fontSize } from "../styles/theme";

interface VoiceButtonProps {
  /** Called with transcribed text when recording completes */
  onTranscription: (text: string) => void;
  /** Whether the button should be disabled */
  disabled?: boolean;
}

export const VoiceButton: VFC<VoiceButtonProps> = ({ onTranscription, disabled }) => {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState("");
  const holdTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Start recording on press */
  const handlePressStart = async () => {
    if (disabled || recording || transcribing) return;
    setError("");

    try {
      const result = await call<[], { success: boolean; error?: string }>("voice_start");
      if (result.success) {
        setRecording(true);
      } else {
        setError(result.error || "Cannot start recording");
      }
    } catch (e: any) {
      setError(e?.message || "Recording failed");
    }
  };

  /** Stop recording and transcribe on release */
  const handlePressEnd = async () => {
    if (!recording) return;
    setRecording(false);
    setTranscribing(true);
    setError("");

    try {
      const result = await call<[], { success: boolean; text: string; error?: string }>(
        "voice_stop"
      );
      if (result.success && result.text) {
        onTranscription(result.text);
      } else {
        setError(result.error || "No speech detected");
      }
    } catch (e: any) {
      setError(e?.message || "Transcription failed");
    } finally {
      setTranscribing(false);
    }
  };

  /** Toggle mode: tap to start, tap again to stop */
  const handleClick = async () => {
    if (recording) {
      await handlePressEnd();
    } else {
      await handlePressStart();
    }
  };

  const buttonLabel = transcribing
    ? "🎙 Transcribing..."
    : recording
      ? "🔴 Recording... (tap to stop)"
      : "🎤 Voice Input";

  return (
    <>
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleClick}
          disabled={disabled || transcribing}
        >
          {buttonLabel}
        </ButtonItem>
      </PanelSectionRow>
      {error && (
        <PanelSectionRow>
          <div
            style={{
              fontSize: `${fontSize.sm}px`,
              color: colors.textError,
              textAlign: "center",
              width: "100%",
            }}
          >
            {error}
          </div>
        </PanelSectionRow>
      )}
    </>
  );
};
