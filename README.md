# Python UDP Communication with Qt GUI

This project demonstrates a simple Python application that utilizes **UDP** for network communication and provides a graphical user interface (**GUI**) built with Qt for Python (**PySide6**).

-----

## Features

  * **UDP Communication**: Sends and receives UDP datagrams.
  * **Qt GUI**: Provides an intuitive graphical interface for interacting with the UDP communication.
  * **Python 3**: Developed using Python 3.

-----

## Prerequisites

Before you begin, ensure you have the following installed on your system:

  * **Python 3.8 or newer**: This project is developed and tested with Python 3.8+.
  * **pip**: The Python package installer, usually included with Python.

-----

## Installation

Follow these steps to set up and install the project dependencies:

1.  **Install Python 3.8 (if not already installed)**:
    If you are on a Linux system that supports Snap, you can install Python 3.8 using the following command:

    ```bash
    sudo snap install python38
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

This project assumes default UDP host and port settings. If you need to modify these (e.g., the listening port or the target address for sending messages), you will typically find these parameters defined within the `app.py` file.

  * **Listening Port**: The port on which the application listens for incoming UDP messages.
  * **Target Host/Port**: The IP address and port to which the application sends UDP messages.

Please refer to the `app.py` file for specific configuration variables.

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

3.  **Run the UDP `server.py`** (located in `modules/udp`):

    ```bash
    python3 modules/udp/server.py
    ```

This command will launch the Qt GUI application.

-----

## Example Usage

After running `python3 app.py`, a GUI window will appear. This application is designed to:

  * **Receive UDP Messages**: It will listen for incoming UDP datagrams on a specified port (e.g., `12345`). Any received messages will be displayed within the GUI.
  * **Send UDP Messages**: The GUI will likely provide an input field and a button to compose and send UDP messages to a target IP address and port.

**Note**: For the application to function correctly, ensure that no other process is using the same UDP port that this application is configured to listen on.