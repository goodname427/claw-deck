/**
 * MessageBubble - Renders a single chat message with role-based styling.
 */
import { VFC } from "react";

/** Chat message data structure */
export interface ChatMessage {
  role: "user" | "assistant" | "error";
  content: string;
}

interface MessageBubbleProps {
  message: ChatMessage;
}

/** Role-based color mapping */
const BUBBLE_STYLES: Record<ChatMessage["role"], { bg: string; align: string }> = {
  user: { bg: "#1a73e8", align: "flex-end" },
  assistant: { bg: "#2d2d2d", align: "flex-start" },
  error: { bg: "#5c1010", align: "flex-start" },
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
          backgroundColor: style.bg,
          padding: "8px 12px",
          borderRadius: "10px",
          maxWidth: "85%",
          fontSize: "13px",
          lineHeight: "1.4",
          wordBreak: "break-word",
          color: "#e8e8e8",
        }}
      >
        {message.role === "error" && (
          <span style={{ color: "#ff6b6b", fontSize: "11px" }}>⚠ Error: </span>
        )}
        {message.content}
      </div>
    </div>
  );
};
