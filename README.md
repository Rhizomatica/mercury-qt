### README.md

# Python UDP Communication with Qt GUI for Mercury

This project provides a Python application with a **Qt GUI** (**PySide6**) for interacting with the **Mercury** software. It uses **UDP** for network communication, allowing users to send and receive messages from the Mercury system.

-----

## Features

  * **UDP Communication**: Sends and receives UDP datagrams to and from Mercury.
  * **Qt GUI**: Provides an intuitive graphical interface for interacting with the Mercury software.
  * **Python 3**: Developed using Python 3.8 or newer.

-----

## Prerequisites

Before you begin, ensure you have the following installed on your system:

  * **Python 3.8 or newer**: This project is developed and tested with Python 3.8+.
  * **pip**: The Python package installer, usually included with Python.

-----

## Installation

Follow these steps to set up and install the project dependencies:

1.  **Clone the Repository**:

    ```bash
    git clone https://github.com/Rhizomatica/mercury.git
    cd mercury-qt
    ```

2.  **Create and Activate a Virtual Environment**:
    It's highly recommended to use a virtual environment to manage project dependencies. This isolates your project's dependencies from your system's global Python packages.

    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

    (On Windows, use `.\env\Scripts\activate` instead of `source env/bin/activate`)

3.  **Install Project Dependencies**:
    With your virtual environment activated, install PySide6 (Qt for Python) using pip:

    ```bash
    pip install pyside6
    ```

-----

## Configuration

This project assumes default UDP host and port settings, which are typically defined in `app.py`. If you need to modify these, such as the listening port or the target address, please refer to the `app.py` file.

  * **Listening Port**: The port on which the application listens for incoming UDP messages from Mercury.
  * **Target Host/Port**: The IP address and port to which the application sends UDP messages to Mercury.

-----

## Running the Project

Once you have completed the installation and configuration steps, you can run the application:

1.  **Activate your virtual environment (if not already active)**:

    ```bash
    source env/bin/activate
    ```

2.  **Run the main application file**:

    ```bash
    python3 app.py
    ```

This command will launch the Qt GUI application, ready to communicate with Mercury.

-----

## Packaging

### Linux (Debian packages)

The repository now includes a `debian/` directory so you can build a Debian
package with the standard Debian packaging tools, for example:

```bash
dpkg-buildpackage -us -uc -b
```

The resulting package declares the local `mercury` backend and `python3-numpy`
as runtime dependencies, matching the current GUI/runtime assumptions.

### Linux bundle

For a local Linux bundle, use the wrapper below. It rebuilds the sibling
`../mercury` checkout with `make clean && make -j4`, then stages `mercury`
next to a bundled GUI runtime:

```bash
bash scripts/build_linux_bundle.sh
```

By default the wrapper tries a native `pyside6-deploy` standalone build when
`pyside6-deploy`, `python -m nuitka`, and `patchelf` are already available in
the selected Python environment. If that standalone toolchain is not available,
it falls back to a runnable source bundle under `deployment-linux/mercury-qt/`
with a local `mercury-qt` launcher that uses the selected Python interpreter.

Override the defaults with `MERCURY_QT_LINUX_BUNDLE_DIR`,
`MERCURY_QT_MERCURY_DIR`, `MERCURY_QT_PYTHON`, `MERCURY_QT_APP_TITLE`, and
`MERCURY_QT_LINUX_BUNDLE_MODE`, or pass wrapper options such as `--bundle-dir`,
`--mercury-dir`, `--python`, `--mode`, and `--skip-mercury-build`. Extra
arguments after `--` are forwarded directly to `pyside6-deploy` when standalone
mode is selected, for example:

```bash
bash scripts/build_linux_bundle.sh --mode standalone -- --verbose
```

### Windows bundle

The supported Linux-hosted Windows flow uses a full Windows Python **3.12**
installation under Wine together with `PySide6` and `Nuitka 2.7.11`. The helper
below installs that toolchain into a dedicated Wine prefix and stages the ICU
runtime DLLs from the Cygwin `mingw64-x86_64-icu` package:

```bash
python3 scripts/setup_wine_python.py \
  /path/to/python-3.12.x-amd64.exe \
  --wine-prefix /path/to/wine-python312
```

Once that prefix is ready, build the GUI bundle and stage `mercury.exe` from the
sibling `../mercury` checkout:

```bash
bash scripts/build_windows_bundle_wine.sh -- --force --keep-deployment-files
```

That wrapper defaults to the sibling `../mercury` checkout and the Wine Python
3.12 prefix at `../wine-python312`. Override the defaults with
`MERCURY_QT_MERCURY_DIR`, `MERCURY_QT_WINE_PREFIX`,
`MERCURY_QT_WINE_PYTHON`, and `MERCURY_QT_BUNDLE_DIR`, or call the Python
helper directly:

```bash
python3 scripts/build_windows_bundle.py \
  --wine-python /path/to/wine-python312/drive_c/Python312/python.exe \
  --wine-prefix /path/to/wine-python312 \
  -- --force --keep-deployment-files
```

The helper installs the app's Python dependencies in the Wine prefix, stages
the ICU runtime from the Cygwin `mingw64-x86_64-icu` package, invokes Nuitka
directly under Wine with PE-file dependency scanning, includes the Qt
stylesheet assets used at runtime, and produces a standalone runtime directory
at `deployment/mercury-qt.dist/`. The GUI launcher ends up at
`deployment/mercury-qt.dist/mercury-qt.exe`, with the cross-built
`deployment/mercury-qt.dist/mercury.exe` staged next to it together with the
extra Hamlib-side DLLs that `mercury` includes in its `make windows-zip`
target. If you have already built `mercury.exe`, pass `--skip-mercury-build`.

For local Wine testing of an already-built bundle, run:

```bash
bash scripts/run_windows_bundle_wine.sh
```

That helper starts `mercury.exe -G -u 127.0.0.1 -U 10000` from
`deployment/mercury-qt.dist/`, then launches `mercury-qt.exe` with the same
Wine prefix. Override the defaults with `WINEPREFIX=/path/to/prefix` and
`MERCURY_QT_BUNDLE_DIR=/path/to/mercury-qt.dist` if needed.

-----

## Example Usage

After running `python3 app.py [app_name]` 

eg. `python3 app.py mercury` , 

a GUI window will appear. This application is designed to:

  * **Receive UDP Messages**: It will listen for incoming UDP datagrams from Mercury on a specified port (e.g., `12345`). Any received messages will be displayed within the GUI.
  * **Send UDP Messages**: The GUI will provide an input field and a button to compose and send UDP messages to the Mercury system.

**Note**: For the application to function correctly, ensure that no other process is using the same UDP port that this application is configured to listen on.


## HERMES-MODEM

To make the real connection with HERMES-MODEM clone the project from

**GITHUB REPO**

`https://github.com/Rhizomatica/hermes-modem`


and run 

```
 ./ui_communication 127.0.0.1 10000 9999
```
in /hermes-modem/gui_interface
