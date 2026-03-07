"""
Waterfall Display module for the Mercury QT application.

Wraps the WaterfallWidget and SpectrumProvider into a QGroupBox
with the same visual style as other Mercury QT panels (ConnectionInfo,
Controls, etc.).  Provides start/stop and demo-mode toggling.
"""

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Slot
from core.components.waterfall_widget import WaterfallWidget
from core.components.spectrum_provider import SpectrumProvider

import numpy as np


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

        # ---- Spectrum data source ----
        self.provider = SpectrumProvider(
            self,
            demo_mode=True,     # start in demo mode; switch when backend connects
            fft_size=512,
            sample_rate=8000,
        )
        self.provider.spectrum_ready.connect(self._on_spectrum)

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

        # Auto-start the provider
        self.provider.start()

    # ------------------------------------------------------------------
    #  Slots
    # ------------------------------------------------------------------

    @Slot(object, int)
    def _on_spectrum(self, power_db, sample_rate: int):
        """Forward spectrum line (and sample rate) to the waterfall widget."""
        self.waterfall.push_spectrum(power_db, sample_rate)

    @Slot(dict)
    def handle_status(self, data: dict):
        """Update waterfall overlay from modem status messages."""
        snr = data.get("snr")
        if snr is not None:
            self.waterfall.set_snr(float(snr))
        sync = data.get("sync")
        if sync is not None:
            self.waterfall.set_sync(bool(sync))

    def set_demo_mode(self, enabled: bool):
        self.provider.set_demo_mode(enabled)
