from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from core.pipelines.talking_head import TalkingHeadRequest, animate

_STYLE_BTN = (
    "QPushButton { background:#7c3aed; color:#fff; border:none; padding:8px 20px;"
    " border-radius:6px; font-weight:600; }"
    "QPushButton:hover { background:#a855f7; }"
    "QPushButton:disabled { background:#333; color:#666; }"
)


class _Signals(QObject):
    finished = Signal(str, float)   # output_path, duration_seconds
    error = Signal(str)


class TalkingHeadWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._signals = _Signals()
        self._signals.finished.connect(self._on_done)
        self._signals.error.connect(self._on_error)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        files_box = QGroupBox("Input Files")
        ff = QFormLayout(files_box)

        img_row = QHBoxLayout()
        self.img_edit = QLineEdit()
        self.img_edit.setPlaceholderText("Anchor portrait image…")
        img_btn = QPushButton("Browse")
        img_btn.clicked.connect(lambda: self._pick(self.img_edit, "Images (*.jpg *.jpeg *.png)"))
        img_row.addWidget(self.img_edit)
        img_row.addWidget(img_btn)
        ff.addRow("Portrait", img_row)

        aud_row = QHBoxLayout()
        self.aud_edit = QLineEdit()
        self.aud_edit.setPlaceholderText("Driving audio WAV / MP3…")
        aud_btn = QPushButton("Browse")
        aud_btn.clicked.connect(lambda: self._pick(self.aud_edit, "Audio (*.wav *.mp3 *.flac)"))
        aud_row.addWidget(self.aud_edit)
        aud_row.addWidget(aud_btn)
        ff.addRow("Audio", aud_row)
        root.addWidget(files_box)

        opt_box = QGroupBox("Options")
        of = QFormLayout(opt_box)

        self.model_cb = QComboBox()
        self.model_cb.addItems(["sadtalker", "wav2lip"])
        of.addRow("Model", self.model_cb)

        self.preprocess_cb = QComboBox()
        self.preprocess_cb.addItems(["crop", "resize", "full"])
        of.addRow("Preprocess", self.preprocess_cb)

        self.still_cb = QCheckBox("Still mode (minimal head motion — anchor look)")
        self.still_cb.setChecked(True)
        of.addRow("", self.still_cb)

        self.enhance_cb = QCheckBox("Face enhance (GFPGAN)")
        self.enhance_cb.setChecked(True)
        of.addRow("", self.enhance_cb)
        root.addWidget(opt_box)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Animate Anchor")
        self.run_btn.setStyleSheet(_STYLE_BTN)
        self.run_btn.clicked.connect(self._run)
        btn_row.addWidget(self.run_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color:#888; font-size:12px;")
        root.addWidget(self.status_lbl)
        root.addStretch()

    def _pick(self, edit: QLineEdit, filt: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", filt)
        if path:
            edit.setText(path)

    def _run(self) -> None:
        img = self.img_edit.text()
        aud = self.aud_edit.text()
        if not img or not aud:
            self.status_lbl.setText("Select portrait and audio files first.")
            return

        self.run_btn.setEnabled(False)
        self.status_lbl.setText("Animating anchor…")

        req = TalkingHeadRequest(
            source_image=Path(img),
            audio_path=Path(aud),
            model=self.model_cb.currentText(),
            still_mode=self.still_cb.isChecked(),
            preprocess=self.preprocess_cb.currentText(),
            enhance_face=self.enhance_cb.isChecked(),
        )

        def _worker() -> None:
            try:
                result = animate(req)
                self._signals.finished.emit(str(result.output_path), result.duration_seconds)
            except Exception as e:
                self._signals.error.emit(str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_done(self, path: str, duration: float) -> None:
        self.run_btn.setEnabled(True)
        self.status_lbl.setText(f"Done — {duration:.1f}s video → {path}")
        self.status_lbl.setStyleSheet("color:#22c55e; font-size:12px;")

    def _on_error(self, msg: str) -> None:
        self.run_btn.setEnabled(True)
        self.status_lbl.setText(f"Error: {msg}")
        self.status_lbl.setStyleSheet("color:#ef4444; font-size:12px;")
