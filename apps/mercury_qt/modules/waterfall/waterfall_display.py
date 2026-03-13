"""
Waterfall Display module for the Mercury QT application.

Wraps the WaterfallWidget into a QGroupBox.
Spectrum data is fed externally via push_spectrum() (from the WebSocket client).
"""

from PySide6 import QtWidgets
from PySide6.QtCore import Slot
from core.components.waterfall_widget import WaterfallWidget


class WaterfallDisplay(QtWidgets.QWidget):
    """Self-contained waterfall display panel."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # ---- Waterfall widget ----
        self.waterfall = WaterfallWidget(
            fft_size=512,
            sample_rate=8000,
            history_lines=350,
        )

        # ---- Layout inside a GroupBox ----
        self.group_box = QtWidgets.QGroupBox("Waterfall")
        inner = QtWidgets.QVBoxLayout()
        inner.setContentsMargins(4, 4, 4, 4)
        inner.setSpacing(2)
        inner.addWidget(self.waterfall, stretch=1)
        self.group_box.setLayout(inner)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.group_box)

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def push_spectrum(self, power_db, sample_rate: int):
        """Feed a spectrum line (from the WebSocket client) into the waterfall."""
        self.waterfall.push_spectrum(power_db, sample_rate)

    @Slot(dict)
    def handle_status(self, data: dict):
        """Update SNR and sync overlay from modem status messages."""
        snr = data.get("snr")
        if snr is not None:
            self.waterfall.set_snr(float(snr))
        sync = data.get("sync")
        if sync is not None:
            self.waterfall.set_sync(bool(sync))
