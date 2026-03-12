/**
 * ClawDeck - OpenClaw AI Assistant plugin for Steam Deck
 * Frontend entry point for Decky Loader sidebar
 */
import { definePlugin, staticClasses } from "@decky/ui";
import { routerHook } from "@decky/api";
import { FaRobot } from "react-icons/fa";

import { ChatPanel } from "./components/ChatPanel";

export default definePlugin(() => {
  return {
    name: "ClawDeck",
    title: <div className={staticClasses.Title}>ClawDeck</div>,
    content: <ChatPanel />,
    icon: <FaRobot />,
    onDismount() {
      // Cleanup if needed
    },
  };
});
