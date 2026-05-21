import math

from PySide6 import QtWidgets, QtCore, QtGui
from core.components.combobox import ComboBox, _NoScrollComboBox


class TxPeakMeter(QtWidgets.QWidget):
    """Horizontal TX peak-level bar with a held-peak hairline.

    Maps dBFS range [-60, 0] to the full widget width.
    Fill colour: green below -6 dBFS, yellow at or above -6 dBFS,
    red at or above -1 dBFS.  Held-peak hairline is white and decays
    roughly 0.5 dB per 100 ms after the 2 s hold window expires.
    """

    _DB_MIN    = -60.0
    _DB_MAX    =   0.0
    _DB_WARN   =  -6.0
    _DB_DANGER =  -1.0

    _COL_BG     = QtGui.QColor("#121212")
    _COL_BORDER = QtGui.QColor("#464646")
    _COL_GREEN  = QtGui.QColor("#22cc77")
    _COL_YELLOW = QtGui.QColor("#ffcc44")
    _COL_RED    = QtGui.QColor("#ff4444")
    _COL_PEAK   = QtGui.QColor("#ffffff")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level_dbfs: float = -120.0
        self._peak_dbfs:  float = -120.0
        self._peak_hold_until: int = 0   # milliseconds epoch

        self.setMinimumHeight(14)
        self.setMaximumHeight(18)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setToolTip("Per-burst TX peak (dBFS, 0 = clip)")

        self._decay_timer = QtCore.QTimer(self)
        self._decay_timer.timeout.connect(self._decay_peak)
        self._decay_timer.start(100)

    def set_level(self, dbfs: float) -> None:
        if not math.isfinite(dbfs):
            dbfs = -120.0
        self._level_dbfs = dbfs
        now_ms = QtCore.QDateTime.currentMSecsSinceEpoch()
        if dbfs > self._peak_dbfs:
            self._peak_dbfs = dbfs
            self._peak_hold_until = now_ms + 2000
        self.update()

    def _decay_peak(self) -> None:
        now_ms = QtCore.QDateTime.currentMSecsSinceEpoch()
        if now_ms > self._peak_hold_until:
            new_peak = max(self._level_dbfs, self._peak_dbfs - 0.5)
            if abs(new_peak - self._peak_dbfs) > 1e-6:
                self._peak_dbfs = new_peak
                self.update()

    def _db_to_frac(self, db: float) -> float:
        return max(0.0, min(1.0, (db - self._DB_MIN) / (self._DB_MAX - self._DB_MIN)))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        if w < 3 or h < 3:
            painter.end()
            return

        # Background
        painter.fillRect(0, 0, w, h, self._COL_BG)

        # Level fill
        frac = self._db_to_frac(self._level_dbfs)
        fill_w = max(0, int(frac * w))
        if fill_w > 0:
            if self._level_dbfs >= self._DB_DANGER:
                col = self._COL_RED
            elif self._level_dbfs >= self._DB_WARN:
                col = self._COL_YELLOW
            else:
                col = self._COL_GREEN
            painter.fillRect(0, 0, fill_w, h, col)

        # Border
        painter.setPen(QtGui.QPen(self._COL_BORDER, 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        # Held-peak hairline
        if self._peak_dbfs > self._DB_MIN:
            px = min(w - 2, max(1, int(self._db_to_frac(self._peak_dbfs) * w)))
            painter.setPen(QtGui.QPen(self._COL_PEAK, 2))
            painter.drawLine(px, 0, px, h)

        painter.end()


class RadioControls(QtWidgets.QWidget):
    """Componente que agrega os controles de Soundcard e Radio."""

    # Signal emitted when Apply is clicked with both radio model and device path
    radio_config_command = QtCore.Signal(dict)
    # Signal emitted when audio Apply is clicked with capture/playback/channel
    audio_config_command = QtCore.Signal(dict)
    # Signal emitted when the Connect button is clicked with valid host and port
    connect_requested = QtCore.Signal(str, int)
    # Signal emitted on slider release with the set_tx_gain command dict
    tx_gain_command = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()

        self.capture_dev_control = ComboBox("capture_dev")
        self.playback_dev_control = ComboBox("playback_dev")
        self.input_channel_control = ComboBox("input_channel")
        self.radio_control = ComboBox("radio_model")

        # Prevent audio ComboBoxes from auto-sending on selection change
        self._disable_auto_emit(self.capture_dev_control)
        self._disable_auto_emit(self.playback_dev_control)
        self._disable_auto_emit(self.input_channel_control)

        # Prevent the radio ComboBox from auto-sending on selection change
        self._disable_auto_emit(self.radio_control)

        # Plain QLineEdit for device path
        self.device_path_line_edit = QtWidgets.QLineEdit()
        self.device_path_line_edit.setMaxLength(255)
        self.device_path_line_edit.setPlaceholderText(
            "/dev/ttyUSB0 or 127.0.0.1:4532")

        # Baud Rate ComboBox (fixed options, no auto-emit needed)
        self.baud_rate_control = _NoScrollComboBox()
        self.baud_rate_control.addItem("Auto", "0")
        self.baud_rate_control.addItem("4800", "4800")
        self.baud_rate_control.addItem("9600", "9600")
        self.baud_rate_control.addItem("19200", "19200")
        self.baud_rate_control.addItem("38400", "38400")
        self.baud_rate_control.addItem("115200", "115200")

        # Apply button for audio config (capture/playback/channel)
        self.audio_apply_button = QtWidgets.QPushButton("Apply")
        self.audio_apply_button.clicked.connect(self._on_audio_apply)

        # Track applied audio values so backend refreshes don't lose user choices
        self._applied_capture_dev = ""
        self._applied_playback_dev = ""
        self._applied_input_channel = ""

        # Shared Apply button for HAMLIB radio model + device file path
        self.radio_apply_button = QtWidgets.QPushButton("Apply")
        self.radio_apply_button.clicked.connect(self._on_radio_apply)
        self.device_path_line_edit.returnPressed.connect(self._on_radio_apply)

        # Track applied values so backend refreshes don't lose user choices
        self._applied_radio_model = ""
        self._applied_device_path = ""
        self._applied_baud_rate = ""

        # TX Audio Level: -20..+20 dB slider (step 0.5 dB → integer ×2)
        self._tx_gain_user_active = False
        # Debounce timer: commits the gain 400 ms after the last value change.
        # sliderReleased short-circuits this and commits immediately.
        self._tx_gain_commit_timer = QtCore.QTimer(self)
        self._tx_gain_commit_timer.setSingleShot(True)
        self._tx_gain_commit_timer.setInterval(400)
        self._tx_gain_commit_timer.timeout.connect(self._commit_tx_gain)

        self.tx_gain_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.tx_gain_slider.setRange(-40, 40)   # 1 unit = 0.5 dB
        self.tx_gain_slider.setValue(0)
        self.tx_gain_slider.setToolTip("TX audio gain: -20 to +20 dB (step 0.5 dB)")
        self.tx_gain_value_label = QtWidgets.QLabel("0.0 dB")
        self.tx_gain_value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight |
                                              QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.tx_peak_meter = TxPeakMeter()
        self.tx_peak_value_label = QtWidgets.QLabel("TX peak: \u2014 dBFS")

        self.tx_gain_slider.valueChanged.connect(self._on_tx_gain_value_changed)
        self.tx_gain_slider.sliderReleased.connect(self._on_tx_gain_slider_released)

        # Host / Port / Connect
        self.host_line_edit = QtWidgets.QLineEdit()
        self.host_line_edit.setMaxLength(255)
        self.host_line_edit.setPlaceholderText("127.0.0.1")

        self.port_line_edit = QtWidgets.QLineEdit()
        self.port_line_edit.setMaxLength(5)
        self.port_line_edit.setPlaceholderText("10000")
        self.port_line_edit.setValidator(QtGui.QIntValidator(1, 65535, self))

        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.clicked.connect(self._on_connect_clicked)
        self.host_line_edit.returnPressed.connect(self._on_connect_clicked)
        self.port_line_edit.returnPressed.connect(self._on_connect_clicked)

        controls_layout = QtWidgets.QVBoxLayout()

        # Audio config section with shared Apply button
        audio_layout = QtWidgets.QVBoxLayout()

        # Radio Capture Device
        capture_label = QtWidgets.QLabel("Capture Device")
        audio_layout.addWidget(capture_label)
        audio_layout.addWidget(self.capture_dev_control)

        # Radio Playback Device
        playback_label = QtWidgets.QLabel("Playback Device")
        audio_layout.addWidget(playback_label)
        audio_layout.addWidget(self.playback_dev_control)

        # Capture Input Channel
        input_channel_label = QtWidgets.QLabel("Capture Input Channel")
        audio_layout.addWidget(input_channel_label)
        audio_layout.addWidget(self.input_channel_control)

        audio_layout.addWidget(self.audio_apply_button)

        audio_box = QtWidgets.QGroupBox()
        audio_box.setLayout(audio_layout)

        controls_layout.addWidget(audio_box)

        # TX Audio Level section
        tx_layout = QtWidgets.QVBoxLayout()

        tx_header = QtWidgets.QHBoxLayout()
        tx_header.addWidget(QtWidgets.QLabel("TX Audio Level"))
        tx_header.addStretch()
        tx_header.addWidget(self.tx_gain_value_label)
        tx_layout.addLayout(tx_header)
        tx_layout.addWidget(self.tx_gain_slider)
        tx_layout.addWidget(self.tx_peak_meter)

        # Scale ticks: space-between the five reference markers
        scale_widget = QtWidgets.QWidget()
        scale_layout = QtWidgets.QHBoxLayout(scale_widget)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.setSpacing(0)
        scale_widget.setStyleSheet("QLabel { font-size: 10px; color: #777; padding: 0px; }")
        for i, mark in enumerate(("-60", "-30", "-12", "-6", "0")):
            lbl = QtWidgets.QLabel(mark)
            lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            scale_layout.addWidget(lbl)
            if i < 4:
                scale_layout.addStretch()
        tx_layout.addWidget(scale_widget)
        tx_layout.addWidget(self.tx_peak_value_label)

        tx_box = QtWidgets.QGroupBox()
        tx_box.setLayout(tx_layout)

        controls_layout.addWidget(tx_box)

        # Visually separated HAMLIB Radio Models + Device Path section
        hamlib_layout = QtWidgets.QVBoxLayout()

        radio_model_label = QtWidgets.QLabel("HAMLIB Model")
        hamlib_layout.addWidget(radio_model_label)
        hamlib_layout.addWidget(self.radio_control)

        device_path_label = QtWidgets.QLabel("Device Path")
        hamlib_layout.addWidget(device_path_label)
        hamlib_layout.addWidget(self.device_path_line_edit)

        baud_rate_label = QtWidgets.QLabel("Baud Rate")
        hamlib_layout.addWidget(baud_rate_label)
        hamlib_layout.addWidget(self.baud_rate_control)

        hamlib_layout.addWidget(self.radio_apply_button)

        hamlib_box = QtWidgets.QGroupBox() # no need title to this section
        hamlib_box.setLayout(hamlib_layout)

        controls_layout.addWidget(hamlib_box)

        # Connection section
        connection_layout = QtWidgets.QVBoxLayout()

        host_label = QtWidgets.QLabel("Host")
        connection_layout.addWidget(host_label)
        connection_layout.addWidget(self.host_line_edit)

        port_label = QtWidgets.QLabel("Port")
        connection_layout.addWidget(port_label)
        connection_layout.addWidget(self.port_line_edit)

        connection_layout.addWidget(self.connect_button)

        connection_box = QtWidgets.QGroupBox()
        connection_box.setLayout(connection_layout)

        controls_layout.addWidget(connection_box)

        controls_layout.addStretch()

        self.group_box = QtWidgets.QGroupBox("Radio Controls")
        self.group_box.setLayout(controls_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    # ---- Apply audio config ----

    def _on_audio_apply(self):
        """Send combined capture/playback/channel config to the backend."""
        capture_dev = self._get_selected_value(self.capture_dev_control) or "default"
        playback_dev = self._get_selected_value(self.playback_dev_control) or "default"
        input_channel = self._get_selected_value(self.input_channel_control) or "left"

        # Persist the applied values for later restoration
        self._applied_capture_dev = capture_dev
        self._applied_playback_dev = playback_dev
        self._applied_input_channel = input_channel

        command = {
            "command": "set_audio_config",
            "value": capture_dev,
            "value2": playback_dev,
            "value3": input_channel,
        }
        self.audio_config_command.emit(command)

    # ---- TX gain slider handlers ----

    def _on_tx_gain_value_changed(self, value: int) -> None:
        """Fires for every user interaction (drag, click-on-track, keyboard).

        Sets the echo-suppression guard and restarts the debounce timer so
        that a commit is issued even when sliderReleased does not fire
        (e.g. click-on-track or keyboard navigation).
        """
        db = value / 2.0
        self.tx_gain_value_label.setText(f"{db:.1f} dB")
        self._tx_gain_user_active = True
        self._tx_gain_commit_timer.start()   # restart debounce

    def _on_tx_gain_slider_released(self) -> None:
        """Mouse-drag release: cancel debounce and commit immediately."""
        self._tx_gain_commit_timer.stop()
        self._commit_tx_gain()

    def _commit_tx_gain(self) -> None:
        """Send set_tx_gain and open the 600 ms echo-suppression window."""
        db = self.tx_gain_slider.value() / 2.0
        self.tx_gain_command.emit({"command": "set_tx_gain", "value": f"{db:.2f}"})
        QtCore.QTimer.singleShot(600, self._clear_tx_gain_active)

    def _clear_tx_gain_active(self) -> None:
        self._tx_gain_user_active = False

    # ---- Public TX gain/meter update API ----

    def update_tx_gain_from_backend(self, db: float) -> None:
        """Sync slider to backend value — no-op while the user is dragging."""
        if self._tx_gain_user_active:
            return
        slider_val = max(-40, min(40, int(round(db * 2))))
        if abs(slider_val - self.tx_gain_slider.value()) >= 1:
            self.tx_gain_slider.blockSignals(True)
            self.tx_gain_slider.setValue(slider_val)
            self.tx_gain_slider.blockSignals(False)
            self.tx_gain_value_label.setText(f"{db:.1f} dB")

    def update_tx_meter(self, dbfs: float) -> None:
        """Feed a new TX peak reading into the peak-meter widget."""
        self.tx_peak_meter.set_level(dbfs)
        if dbfs <= -120:
            self.tx_peak_value_label.setText("TX peak: \u2014 dBFS")
        else:
            self.tx_peak_value_label.setText(f"TX peak: {dbfs:.1f} dBFS")

    def _get_selected_value(self, control: ComboBox) -> str:
        """Return the currently selected value (userData) of a ComboBox."""
        idx = control.combo_box.currentIndex()
        if idx < 0:
            return ""
        val = control.combo_box.itemData(idx)
        return "" if val is None else str(val)

    # ---- Apply radio config ----

    def _on_radio_apply(self):
        """Send combined radio model + device path + baud rate to the backend."""
        model_id = self._get_selected_radio_id()
        device_path = self.device_path_line_edit.text().strip()
        baud_rate = self.baud_rate_control.currentData() or "0"

        if not model_id:
            return

        # Persist the applied values for later restoration
        self._applied_radio_model = model_id
        self._applied_device_path = device_path
        self._applied_baud_rate = baud_rate

        if model_id == "-1":
            self.device_path_line_edit.clear()

        command = {
            "command": "set_radio_config",
            "value": model_id,
            "value2": device_path,
            "value3": baud_rate,
        }
        self.radio_config_command.emit(command)

    def _get_selected_radio_id(self) -> str:
        """Return the currently selected radio model id (userData)."""
        idx = self.radio_control.combo_box.currentIndex()
        if idx < 0:
            return ""
        val = self.radio_control.combo_box.itemData(idx)
        return "" if val is None else str(val)
    
    def _disable_auto_emit(self, control: ComboBox):
        """Safely disable automatic emission on selection change for a ComboBox.
        This avoids relying on the presence of a specific internal handler or
        connection; if either is missing, it simply becomes a no-op.
        """
        handler = getattr(control, "_on_index_changed", None)
        if handler is None:
            return
        try:
            control.combo_box.currentIndexChanged.disconnect(handler)
        except (TypeError, RuntimeError):
            # If handler not connected or signal is invalid, treat as a no-op.
            pass

    # ---- Public helpers for main.py ----

    def clear_applied_state(self):
        """Discard remembered selections so the next backend push is used as-is.

        Call this when the backend restarts so stale UI choices don't override
        the fresh configuration data sent on reconnect.
        """
        self._applied_capture_dev = ""
        self._applied_playback_dev = ""
        self._applied_input_channel = ""
        self._applied_radio_model = ""
        self._applied_device_path = ""
        self._applied_baud_rate = ""

    def reset_controls(self):
        """Clear all dropdowns and text fields so no stale UI state remains."""
        for ctrl in (self.capture_dev_control, self.playback_dev_control,
                     self.input_channel_control, self.radio_control):
            ctrl.combo_box.blockSignals(True)
            ctrl.combo_box.clear()
            ctrl.combo_box.blockSignals(False)
        self.device_path_line_edit.clear()
        self.baud_rate_control.setCurrentIndex(0)

    def restore_radio_selection(self):
        """After the radio list is repopulated, restore the previously applied
        selection so it stays in sync with the backend."""
        if self._applied_radio_model:
            self.radio_control.set_selected(self._applied_radio_model)
        if self._applied_device_path:
            self.device_path_line_edit.setText(self._applied_device_path)
        if self._applied_baud_rate:
            self.set_baud_rate(self._applied_baud_rate)

    def restore_audio_selection(self):
        """After device lists are repopulated, restore the previously applied
        audio selections so they stay in sync with the backend."""
        if self._applied_capture_dev:
            self.capture_dev_control.set_selected(self._applied_capture_dev)
        if self._applied_playback_dev:
            self.playback_dev_control.set_selected(self._applied_playback_dev)
        if self._applied_input_channel:
            self.input_channel_control.set_selected(self._applied_input_channel)

    def set_device_path_text(self, text: str):
        """Set device path without triggering signals (initial sync)."""
        if not self._applied_device_path:
            self.device_path_line_edit.setText(text)

    def set_baud_rate(self, value: str):
        """Set baud rate ComboBox by value string (e.g. '0', '9600')."""
        idx = self.baud_rate_control.findData(value)
        if idx >= 0:
            self.baud_rate_control.setCurrentIndex(idx)

    def get_radio_control(self) -> ComboBox:
        return self.radio_control

    def get_capture_dev_control(self) -> ComboBox:
        return self.capture_dev_control

    def get_playback_dev_control(self) -> ComboBox:
        return self.playback_dev_control

    def get_input_channel_control(self) -> ComboBox:
        return self.input_channel_control

    def set_connection_defaults(self, host: str, port: int):
        """Populate the Host and Port fields with initial values."""
        self.host_line_edit.setText(host)
        self.port_line_edit.setText(str(port))

    def _on_connect_clicked(self):
        """Validate host and port fields, then emit connect_requested."""
        host = self.host_line_edit.text().strip()
        port_text = self.port_line_edit.text().strip()
        if not host or not port_text:
            return
        try:
            port = int(port_text)
        except ValueError:
            return
        self.connect_requested.emit(host, port)
