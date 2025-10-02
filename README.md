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

## Example Usage

After running `python3 app.py`, a GUI window will appear. This application is designed to:

  * **Receive UDP Messages**: It will listen for incoming UDP datagrams from Mercury on a specified port (e.g., `12345`). Any received messages will be displayed within the GUI.
  * **Send UDP Messages**: The GUI will provide an input field and a button to compose and send UDP messages to the Mercury system.

**Note**: For the application to function correctly, ensure that no other process is using the same UDP port that this application is configured to listen on.