/**
 * MessageBubble - Renders a single chat message with role-based styling.
 * Supports a streaming cursor indicator for in-progress responses.
 */
import { VFC } from "react";
import { colors, componentStyles, fontSize } from "../styles/theme";

/** Chat message data structure */
export interface ChatMessage {
  role: "user" | "assistant" | "error";
  content: string;
  /** True while the message is still receiving streaming tokens */
  streaming?: boolean;
}

interface MessageBubbleProps {
  message: ChatMessage;
}

/** Role-based color mapping */
const BUBBLE_STYLES: Record<ChatMessage["role"], { bg: string; align: string }> = {
  user: { bg: colors.bubbleUser, align: "flex-end" },
  assistant: { bg: colors.bubbleAssistant, align: "flex-start" },
  error: { bg: colors.bubbleError, align: "flex-start" },
};

export const MessageBubble: VFC<MessageBubbleProps> = ({ message }) => {
  const style = BUBBLE_STYLES[message.role] || BUBBLE_STYLES.assistant;

  return (
    <div
      style={{
        display: "flex",
        justifyContent: style.align,
        width: "100%",
        marginBottom: "6px",
      }}
    >
      <div
        style={{
          ...componentStyles.bubbleBase,
          backgroundColor: style.bg,
        }}
      >
        {message.role === "error" && (
          <span style={{ color: colors.textError, fontSize: `${fontSize.sm}px` }}>⚠ Error: </span>
        )}
        {message.content}
        {message.streaming && (
          <span
            style={{
              display: "inline-block",
              width: "6px",
              height: "14px",
              backgroundColor: colors.streamCursor,
              marginLeft: "2px",
              verticalAlign: "text-bottom",
              animation: "blink 1s step-end infinite",
            }}
          />
        )}
      </div>
    </div>
  );
};
