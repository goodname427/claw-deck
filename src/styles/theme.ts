/**
 * Steam Deck UI Theme Tokens
 * Centralized design tokens matching SteamOS dark theme.
 * All components should reference these tokens instead of hardcoded values.
 */

/** Color palette aligned with Steam Deck's dark mode */
export const colors = {
  /** Primary backgrounds */
  bgPrimary: "#1a1a2e",
  bgSecondary: "#23263a",
  bgTertiary: "#2a2d42",
  bgCard: "#2a2d42",
  bgInput: "#23263a",

  /** Accent / interactive */
  accent: "#1a9fff",
  accentHover: "#47b4ff",
  accentDim: "#1a6fbf",

  /** User message bubble */
  bubbleUser: "#1a6fbf",
  /** Assistant message bubble */
  bubbleAssistant: "#23263a",
  /** Error message bubble */
  bubbleError: "#4a1a1a",

  /** Text */
  textPrimary: "#e8eaed",
  textSecondary: "#b0b3ba",
  textMuted: "#6c7086",
  textError: "#ff6b6b",
  textSuccess: "#4caf50",

  /** Status indicators */
  statusOnline: "#4caf50",
  statusOffline: "#f44336",
  statusWarning: "#ff9800",

  /** Borders */
  border: "#363a52",
  borderFocus: "#1a9fff",

  /** Streaming cursor */
  streamCursor: "#1a9fff",
} as const;

/** Spacing scale (px) */
export const spacing = {
  xs: 2,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  xxl: 20,
} as const;

/** Border radius (px) */
export const radius = {
  sm: 4,
  md: 8,
  lg: 12,
  pill: 999,
} as const;

/** Font sizes (px) */
export const fontSize = {
  xs: 10,
  sm: 11,
  md: 13,
  lg: 15,
} as const;

/** Common component styles as CSSProperties for reuse */
export const componentStyles = {
  /** Scrollable message container */
  messageList: {
    maxHeight: "340px",
    overflowY: "auto" as const,
    width: "100%",
    paddingRight: `${spacing.sm}px`,
  },

  /** Chat bubble base */
  bubbleBase: {
    padding: `${spacing.md}px ${spacing.lg}px`,
    borderRadius: `${radius.lg}px`,
    maxWidth: "85%",
    fontSize: `${fontSize.md}px`,
    lineHeight: "1.45",
    wordBreak: "break-word" as const,
    color: colors.textPrimary,
  },

  /** Skill card */
  skillCard: {
    backgroundColor: colors.bgCard,
    borderRadius: `${radius.md}px`,
    border: `1px solid ${colors.border}`,
    padding: `${spacing.md}px ${spacing.lg}px`,
    marginBottom: `${spacing.sm + 2}px`,
    cursor: "pointer",
    transition: "background-color 0.15s ease",
  },

  /** Status dot shared style */
  statusDot: {
    fontSize: `${fontSize.md}px`,
    fontWeight: 500 as const,
  },

  /** Nav link in header */
  navLink: {
    fontSize: `${fontSize.sm}px`,
    color: colors.textMuted,
    cursor: "pointer",
    textDecoration: "underline" as const,
  },

  /** Empty state text */
  emptyState: {
    color: colors.textMuted,
    fontSize: `${fontSize.sm + 1}px`,
    textAlign: "center" as const,
    padding: `${spacing.xxl}px 0`,
  },

  /** Field label above inputs */
  fieldLabel: {
    fontSize: `${fontSize.sm + 1}px`,
    color: colors.textSecondary,
    marginBottom: `${spacing.sm}px`,
  },

  /** Feedback status line */
  statusLine: {
    fontSize: `${fontSize.sm + 1}px`,
    textAlign: "center" as const,
    width: "100%",
  },
} as const;
