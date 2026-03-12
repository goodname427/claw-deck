/**
 * ClawDeck - OpenClaw AI Assistant plugin for Steam Deck
 * Frontend entry point for Decky Loader sidebar.
 * Registers hotkey polling to open QAM when backend detects button combo.
 */
import { definePlugin, staticClasses } from "@decky/ui";
import { routerHook, call } from "@decky/api";
import { FaRobot } from "react-icons/fa";

import { ChatPanel } from "./components/ChatPanel";

/** Interval for polling hotkey trigger from backend (ms) */
const HOTKEY_POLL_INTERVAL = 500;

export default definePlugin(() => {
  let hotkeyPollTimer: ReturnType<typeof setInterval> | null = null;

  /**
   * Poll backend for hotkey trigger.
   * When detected, navigate to QAM and focus on ClawDeck plugin tab.
   */
  const startHotkeyPolling = () => {
    hotkeyPollTimer = setInterval(async () => {
      try {
        const result = await call<[], { triggered: boolean }>("poll_hotkey");
        if (result.triggered) {
          // Open Quick Access Menu — SteamClient exposes Navigation.OpenQuickAccessMenu
          try {
            // @ts-ignore - SteamClient is injected by Steam at runtime
            if (typeof SteamClient !== "undefined" && SteamClient?.Navigation) {
              SteamClient.Navigation.OpenQuickAccessMenu(7); // 7 = Decky plugin tab index
            }
          } catch {
            // Fallback: silently ignore if Navigation API unavailable
          }
        }
      } catch {
        // Backend not ready yet, ignore
      }
    }, HOTKEY_POLL_INTERVAL);
  };

  // Start polling immediately
  startHotkeyPolling();

  return {
    name: "ClawDeck",
    title: <div className={staticClasses.Title}>ClawDeck</div>,
    content: <ChatPanel />,
    icon: <FaRobot />,
    onDismount() {
      if (hotkeyPollTimer) {
        clearInterval(hotkeyPollTimer);
        hotkeyPollTimer = null;
      }
    },
  };
});
