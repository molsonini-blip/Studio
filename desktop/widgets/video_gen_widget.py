from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSlider, QSpinBox,
    QTextEdit, QVBoxLayout, QWidget, QFileDialog,
)

from core.pipelines.video_gen import VideoGenRequest, generate
from core.processing.video import pil_frames_to_video


class _Signals(QObject):
    finished = Signal(str)    # output path
    error = Signal(str)


_STYLE_BTN = (
    "QPushButton { background:#7c3aed; color:#fff; border:none; padding:8px 20px;"
    " border-radius:6px; font-weight:600; }"
    "QPushButton:hover { background:#a855f7; }"
    "QPushButton:disabled { background:#333; color:#666; }"
)


class VideoGenWidget(QWidget):
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

        # Prompt group
        prompt_box = QGroupBox("Prompt")
        pf = QVBoxLayout(prompt_box)
        self.prompt = QTextEdit()
        self.prompt.setPlaceholderText("A professional news anchor in a modern studio…")
        self.prompt.setFixedHeight(80)
        self.neg_prompt = QLineEdit()
        self.neg_prompt.setPlaceholderText("Negative prompt: blurry, low quality…")
        pf.addWidget(self.prompt)
        pf.addWidget(self.neg_prompt)
        root.addWidget(prompt_box)

        # Settings row
        settings_box = QGroupBox("Settings")
        sf = QFormLayout(settings_box)

        self.pipeline_cb = QComboBox()
        self.pipeline_cb.addItems(["animatediff", "stable_video_diffusion", "cogvideox"])
        sf.addRow("Pipeline", self.pipeline_cb)

        self.frames_spin = QSpinBox()
        self.frames_spin.setRange(4, 128)
        self.frames_spin.setValue(16)
        sf.addRow("Frames", self.frames_spin)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(8)
        sf.addRow("FPS", self.fps_spin)

        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(10, 100)
        self.steps_spin.setValue(25)
        sf.addRow("Inference steps", self.steps_spin)

        self.guidance_spin = QSpinBox()
        self.guidance_spin.setRange(1, 20)
        self.guidance_spin.setValue(8)
        sf.addRow("Guidance scale", self.guidance_spin)

        self.seed_edit = QLineEdit("-1")
        sf.addRow("Seed (-1 = random)", self.seed_edit)
        root.addWidget(settings_box)

        # Controls
        btn_row = QHBoxLayout()
        self.gen_btn = QPushButton("Generate Video")
        self.gen_btn.setStyleSheet(_STYLE_BTN)
        self.gen_btn.clicked.connect(self._run)
        self.save_btn = QPushButton("Save…")
        self.save_btn.setStyleSheet(_STYLE_BTN)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.gen_btn)
        btn_row.addWidget(self.save_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color:#888; font-size:12px;")
        root.addWidget(self.status_lbl)
        root.addStretch()

        self._last_output: Path | None = None

    def _run(self) -> None:
        self.gen_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.status_lbl.setText("Generating… (first run downloads models)")

        req = VideoGenRequest(
            prompt=self.prompt.toPlainText(),
            negative_prompt=self.neg_prompt.text(),
            pipeline=self.pipeline_cb.currentText(),
            num_frames=self.frames_spin.value(),
            fps=self.fps_spin.value(),
            num_inference_steps=self.steps_spin.value(),
            guidance_scale=float(self.guidance_spin.value()),
            seed=int(self.seed_edit.text() or "-1"),
        )

        def _worker() -> None:
            try:
                result = generate(req)
                out = Path("outputs") / "video_gen" / "preview.mp4"
                out.parent.mkdir(parents=True, exist_ok=True)
                pil_frames_to_video(result.frames, out, fps=result.fps)
                self._signals.finished.emit(str(out))
            except Exception as e:
                self._signals.error.emit(str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_done(self, path: str) -> None:
        self._last_output = Path(path)
        self.gen_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_lbl.setText(f"Done — {path}")
        self.status_lbl.setStyleSheet("color:#22c55e; font-size:12px;")

    def _on_error(self, msg: str) -> None:
        self.gen_btn.setEnabled(True)
        self.status_lbl.setText(f"Error: {msg}")
        self.status_lbl.setStyleSheet("color:#ef4444; font-size:12px;")

    def _save(self) -> None:
        if not self._last_output:
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save Video", "", "MP4 (*.mp4)")
        if dest:
            import shutil
            shutil.copy2(self._last_output, dest)
