from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

from desktop.widgets.face_swap_widget import FaceSwapWidget
from desktop.widgets.talking_head_widget import TalkingHeadWidget
from desktop.widgets.video_gen_widget import VideoGenWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Studio — AI Video Lab")
        self.resize(1440, 900)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("  Studio  —  AI Video Lab")
        header.setFixedHeight(42)
        header.setStyleSheet(
            "background:#1a1a1a; color:#a855f7; font-size:15px; font-weight:700;"
            "border-bottom:1px solid #333; padding-left:12px;"
        )
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #1a1a1a; color: #888; padding: 8px 20px;
                border: none; border-right: 1px solid #333;
            }
            QTabBar::tab:selected { background: #252525; color: #f0f0f0; border-bottom: 2px solid #7c3aed; }
            QTabBar::tab:hover { color: #f0f0f0; }
        """)
        self.tabs.addTab(VideoGenWidget(), "Video Generation")
        self.tabs.addTab(FaceSwapWidget(), "Face Swap")
        self.tabs.addTab(TalkingHeadWidget(), "News Anchor")
        layout.addWidget(self.tabs)

        # Status bar
        self.status = QStatusBar()
        self.status.showMessage("Ready")
        self.setStatusBar(self.status)
