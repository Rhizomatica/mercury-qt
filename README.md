# Mercury Qt

**PySide6 desktop client for monitoring and controlling the
[Mercury](https://github.com/Rhizomatica/mercury) HF modem.**

Mercury Qt connects to the Mercury C backend over a **WebSocket** channel
(default host/port `127.0.0.1:10000`; the scheme is negotiated automatically). The client first attempts **WSS** and,
on failure, falls back to **WS**, alternating schemes on every failed attempt until one is accepted. Once connected, the working scheme is kept for the lifetime of that connection.

-----

## Features

* **WebSocket communication** - bidirectional JSON + binary protocol with
  automatic reconnection, inactivity watchdog, and automatic WSS↔WS scheme
  alternation until the backend accepts one.
* **Real-time waterfall display** - scrolling spectrogram with OFDM band
  overlay, SNR bar, sync indicator, and spectrum graph (20 fps).
* **Audio device controls** - select capture/playback devices and input channel,
  applied live to the running backend.
* **Radio control (Hamlib)** - choose radio model and serial/TCP device path.
* **Connection status** - User and destination callsigns, bitrate, SNR, sync state, TX/RX direction,
  and byte counters updated in real time.
* **Cross-platform** - runs on Linux (native & Debian package) and Windows
  (Wine-hosted Nuitka bundle).

-----

## Prerequisites

* **Python 3.8+**
* **pip**
* A running **Mercury** backend exposing its WebSocket server (port `10000` by
  default). Build Mercury from the parent repository or install the `mercury`
  Debian package.

-----

## Installation

### From source (development)

```bash
git clone https://github.com/Rhizomatica/mercury.git
cd mercury/mercury-qt

python3 -m venv env
source env/bin/activate      # Windows: .\env\Scripts\activate

pip install -r requirements.txt   # Install pyside6 and numpy in virtual environment
```

### Debian package

```bash
dpkg-buildpackage -us -uc -b
sudo apt install ../mercury-qt_*.deb
```

The package depends on `mercury`, `python3-numpy`, and the required
`python3-pyside6.*` modules. After installation the GUI is available as
`mercury-qt` from the desktop menu or command line.

-----

## Running

Start the Mercury backend first:

```bash
# Plain WS (default - no TLS required)
mercury -G

# WSS (TLS) - requires certificate and key on the server
mercury -G -T
```

**Note:** `-G` option is required to enable UI communication.

Then launch the GUI:

```bash
python3 app.py mercury [--host HOST] [--port PORT]
```

Defaults: host `127.0.0.1`, port `10000`.

The GUI tries **WSS** first. If that attempt fails the client automatically
switches to **WS** for the next attempt, then back to **WSS**, and so on,
alternating on every failure until the backend accepts a connection — no user
action is needed. Once connected, the working scheme is kept for the lifetime
of that connection. After a clean disconnect the cycle restarts from WSS.

If installed via the Debian package:

```bash
mercury-qt
```

The GUI connects to the backend WebSocket, populates the audio/radio device
lists, and begins displaying the waterfall and connection status.

-----

## Configuration

Connection parameters are passed on the command line. The default WebSocket
endpoint is `ws://127.0.0.1:10000`, matching Mercury's `UI_DEFAULT_PORT`.

Mercury Qt alternates between WSS and WS on every failed connection attempt
until the backend accepts one - no manual configuration is needed for the
connection scheme. To force WSS on the backend side, start Mercury with
`-G -T`. The required self-signed certificate and key must exist on the server.

Audio and radio settings are configured interactively through the GUI controls
and sent to the backend as JSON commands.

-----

## Project structure

```
mercury-qt/
├── app.py                        # Entry point
├── windows_bundle_entry.py       # Windows launcher stub
├── requirements.txt              # Python dependencies
├── apps/
│   └── mercury_qt/
│       ├── app.py                # QApplication setup
│       ├── assets/styles/        # Qt stylesheets
│       ├── components/           # Reusable UI components
│       └── modules/
│           ├── main.py           # Main widget / message router
│           ├── connection_info/  # Status display
│           ├── controls/         # Audio & radio controls
│           └── waterfall/        # Waterfall spectrogram
├── core/
│   ├── components/               # Shared widgets (waterfall engine, charts, etc.)
│   └── connection/websocket/     # QWebSocket client
├── scripts/                      # Build & bundle helpers
├── debian/                       # Debian packaging metadata
├── assets/                       # Branding assets
└── third_party/                  # Pre-downloaded wheels (Windows)
```

## Backend communication protocol

Mercury Qt talks to the Mercury backend over a single WebSocket connection.

### JSON messages (text frames)

**Commands sent to backend:**

| Command | Fields | Description |
|---------|--------|-------------|
| `set_audio_config` | `value` (capture device ID), `value2` (playback device ID), `value3` (input channel) | Apply audio device selection |
| `set_radio_config` | `value` (Hamlib radio model ID), `value2` (device path) | Apply radio/Hamlib settings |

**Status received from backend:**

| Type | Key fields | Description |
|------|-----------|-------------|
| `capture_dev_list` | `list`, `selected` | Available capture devices |
| `playback_dev_list` | `list`, `selected` | Available playback devices |
| `radio_list` | `list`, `selected` | Available Hamlib radio models |
| `input_channel` | `list`, `selected` | Input channel options |
| `status` | `snr`, `sync`, `bitrate`, `direction`, callsigns, byte counters, `waterfall` | Periodic status snapshot |

### Binary frames (spectrum data)

Each binary frame carries one FFT line:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 B | Magic (`0x4D435259` = "MCRY") |
| 4 | 2 B | FFT size (uint16) |
| 6 | 2 B | Sample rate (uint16) |
| 8 | N×4 B | float32 power values (dB) |

-----

## Packaging

### Linux (Debian package)

```bash
dpkg-buildpackage -us -uc -b
```

### Linux bundle

```bash
bash scripts/build_linux_bundle.sh
```

Modes: `auto` (default), `standalone` (Nuitka binary), or `source` (runnable
directory with launcher script). Override defaults with `--mode`, `--bundle-dir`,
`--mercury-dir`, `--python`, `--skip-mercury-build`, etc. Extra arguments after
`--` are forwarded to `pyside6-deploy` in standalone mode:

```bash
bash scripts/build_linux_bundle.sh --mode standalone -- --verbose
```

### Windows bundle (cross-built under Wine)

1. **Set up the Wine Python 3.12 environment:**

    ```bash
    python3 scripts/setup_wine_python.py \
      /path/to/python-3.12.x-amd64.exe \
      --wine-prefix /path/to/wine-python312
    ```

2. **Build the bundle:**

    ```bash
    bash scripts/build_windows_bundle_wine.sh -- --force --keep-deployment-files
    ```

    That wrapper defaults to the sibling `../mercury` checkout and the Wine
    Python 3.12 prefix at `../wine-python312`. Override the defaults with
    `MERCURY_QT_MERCURY_DIR`, `MERCURY_QT_WINE_PREFIX`,
    `MERCURY_QT_WINE_PYTHON`, `MERCURY_QT_BUNDLE_DIR`, and
    `MERCURY_QT_APP_TITLE`, or call the Python helper directly:

    ```bash
    python3 scripts/build_windows_bundle.py \
      --wine-python /path/to/wine-python312/drive_c/Python312/python.exe \
      --wine-prefix /path/to/wine-python312 \
      -- --force --keep-deployment-files
    ```

    The helper installs the app's Python dependencies in the Wine prefix,
    stages the ICU runtime from the Cygwin `mingw64-x86_64-icu` package,
    invokes Nuitka directly under Wine with PE-file dependency scanning,
    includes the Qt stylesheet assets used at runtime, and produces a
    standalone runtime directory at `deployment/mercury-qt.dist/`. The GUI
    launcher ends up at `deployment/mercury-qt.dist/mercury-qt.exe`, with the
    cross-built `deployment/mercury-qt.dist/mercury.exe` staged next to it
    together with the extra Hamlib-side DLLs that `mercury` includes in its
    `make windows-zip` target. The wrapper then zips that runtime directory
    into a publishable archive named like
    `deployment/mercury-qt-windows-gui-<gui_hash>-mercury-<mercury_hash>.zip`
    and prints the full path to that zip at the end. If you have already built
    `mercury.exe`, pass `--skip-mercury-build`.

3. **Test under Wine:**

    ```bash
    bash scripts/run_windows_bundle_wine.sh
    ```

-----

## License

This project is licensed under the GNU General Public License v3.0 - see
[LICENSE](../LICENSE) for details.

Copyright (C) 2025-2026 [Rhizomatica](https://www.rhizomatica.org/)
