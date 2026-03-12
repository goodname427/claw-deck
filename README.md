# ClawDeck

OpenClaw AI Assistant plugin for Steam Deck, powered by [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader).

在 Steam Deck 的 Quick Access 侧边栏中直接与 [OpenClaw](https://github.com/openclaw/openclaw) AI 对话。

## Features

- 🤖 Sidebar chat panel integrated into Decky Loader
- 🔗 Connect to OpenClaw Gateway via HTTP REST API
- ⚙️ Configurable Gateway address (HTTP / WebSocket)
- 💬 Real-time connection status indicator
- 🎮 Designed for Steam Deck gamepad & touchscreen interaction

## Project Structure

```
ClawDeck/
├── plugin.json                  # Decky Loader plugin metadata
├── package.json                 # Frontend dependencies & scripts
├── tsconfig.json                # TypeScript configuration
├── rollup.config.js             # Frontend bundler config
├── main.py                      # Python backend entry point
├── py_modules/
│   └── openclaw_client.py       # OpenClaw HTTP client
├── defaults/
│   └── config.json              # Default configuration
└── src/
    ├── index.tsx                # Plugin entry point
    └── components/
        ├── ChatPanel.tsx        # Main chat interface
        ├── MessageBubble.tsx    # Message bubble component
        └── SettingsPanel.tsx    # Gateway settings panel
```

## Prerequisites

- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) installed on Steam Deck
- [OpenClaw](https://github.com/openclaw/openclaw) Gateway running and accessible
- Node.js 18+ and pnpm (for building)

## Build

```bash
# Install dependencies
pnpm install

# Build frontend
pnpm build
```

## Install

Copy the entire `ClawDeck/` directory (with `dist/`, `main.py`, `py_modules/`, `defaults/`, `plugin.json`) to:

```
~/homebrew/plugins/ClawDeck/
```

Then restart Decky Loader or reboot Steam Deck.

## Configuration

Open the plugin sidebar → click **Settings** to configure:

| Field | Default | Description |
|-------|---------|-------------|
| HTTP URL | `http://localhost:18789` | OpenClaw Gateway HTTP endpoint |
| WebSocket URL | `ws://localhost:18789/ws` | OpenClaw Gateway WebSocket endpoint (reserved) |

Configuration is persisted to `~/homebrew/settings/ClawDeck/config.json`.

## Backend API

The Python backend exposes the following methods to the frontend via Decky's `call()` bridge:

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `send_message` | `message: str, session_key?: str` | `{success, data/error}` | Send chat message to OpenClaw |
| `check_connection` | — | `{connected: bool}` | Test Gateway connectivity |
| `get_config` | — | `{http_url, ws_url}` | Get current config |
| `set_config` | `http_url: str, ws_url: str` | `{success: bool}` | Update & persist config |
| `clear_history` | — | `{success: bool}` | Acknowledge history clear |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | TypeScript, React (Steam SP_REACT), @decky/ui, @decky/api |
| Backend | Python 3, stdlib urllib (zero external dependencies) |
| Bundler | Rollup |
| Target | SteamOS 3.x (Arch Linux) |

## License

[MIT](LICENSE)
