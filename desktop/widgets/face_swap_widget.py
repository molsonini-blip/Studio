from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from core.pipelines.face_swap import FaceSwapRequest, swap

_STYLE_BTN = (
    "QPushButton { background:#7c3aed; color:#fff; border:none; padding:8px 20px;"
    " border-radius:6px; font-weight:600; }"
    "QPushButton:hover { background:#a855f7; }"
    "QPushButton:disabled { background:#333; color:#666; }"
)


class _Signals(QObject):
    finished = Signal(str, int)   # output_path, faces_count
    error = Signal(str)


class FaceSwapWidget(QWidget):
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

        src_row = QHBoxLayout()
        self.src_edit = QLineEdit()
        self.src_edit.setPlaceholderText("Source face image…")
        src_btn = QPushButton("Browse")
        src_btn.clicked.connect(lambda: self._pick_file(self.src_edit, "Images (*.jpg *.jpeg *.png)"))
        src_row.addWidget(self.src_edit)
        src_row.addWidget(src_btn)
        ff.addRow("Source face", src_row)

        tgt_row = QHBoxLayout()
        self.tgt_edit = QLineEdit()
        self.tgt_edit.setPlaceholderText("Target image or video…")
        tgt_btn = QPushButton("Browse")
        tgt_btn.clicked.connect(lambda: self._pick_file(self.tgt_edit, "Media (*.jpg *.jpeg *.png *.mp4 *.avi *.mov)"))
        tgt_row.addWidget(self.tgt_edit)
        tgt_row.addWidget(tgt_btn)
        ff.addRow("Target media", tgt_row)
        root.addWidget(files_box)

        opt_box = QGroupBox("Options")
        of = QFormLayout(opt_box)

        self.alpha_slider = QSlider()
        from PySide6.QtCore import Qt
        self.alpha_slider.setOrientation(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(95)
        self.alpha_lbl = QLabel("0.95")
        self.alpha_slider.valueChanged.connect(lambda v: self.alpha_lbl.setText(f"{v/100:.2f}"))
        alpha_row = QHBoxLayout()
        alpha_row.addWidget(self.alpha_slider)
        alpha_row.addWidget(self.alpha_lbl)
        of.addRow("Blend alpha", alpha_row)

        self.enhance_cb = QCheckBox("Face enhance (GFPGAN)")
        self.enhance_cb.setChecked(True)
        of.addRow("", self.enhance_cb)
        root.addWidget(opt_box)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Swap Face")
        self.run_btn.setStyleSheet(_STYLE_BTN)
        self.run_btn.clicked.connect(self._run)
        btn_row.addWidget(self.run_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color:#888; font-size:12px;")
        root.addWidget(self.status_lbl)
        root.addStretch()

    def _pick_file(self, edit: QLineEdit, filt: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", filt)
        if path:
            edit.setText(path)

    def _run(self) -> None:
        src = self.src_edit.text()
        tgt = self.tgt_edit.text()
        if not src or not tgt:
            self.status_lbl.setText("Select source and target files first.")
            return

        self.run_btn.setEnabled(False)
        self.status_lbl.setText("Swapping…")
        alpha = self.alpha_slider.value() / 100.0
        enhance = self.enhance_cb.isChecked()

        def _worker() -> None:
            try:
                result = swap(FaceSwapRequest(
                    source_image=Path(src),
                    target_media=Path(tgt),
                    blend_alpha=alpha,
                    enhance=enhance,
                ))
                self._signals.finished.emit(str(result.output_path), result.faces_swapped)
            except Exception as e:
                self._signals.error.emit(str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_done(self, path: str, n: int) -> None:
        self.run_btn.setEnabled(True)
        self.status_lbl.setText(f"Done — {n} face(s) swapped → {path}")
        self.status_lbl.setStyleSheet("color:#22c55e; font-size:12px;")

    def _on_error(self, msg: str) -> None:
        self.run_btn.setEnabled(True)
        self.status_lbl.setText(f"Error: {msg}")
        self.status_lbl.setStyleSheet("color:#ef4444; font-size:12px;")
