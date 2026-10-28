"""History panel dock widget displaying live Undo and Redo stacks."""
from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
)

from apps.mini_photoshop.editor import Editor


class HistoryPanel(QWidget):
    """Live history panel showing all executed commands and undone redo commands."""

    def __init__(self, editor: Editor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.editor = editor
        self.setMinimumWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header controls
        hdr_layout = QHBoxLayout()
        self.lbl_info = QLabel("History (0 steps)")
        self.lbl_info.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        hdr_layout.addWidget(self.lbl_info)

        self.btn_undo = QPushButton("⮌ Undo")
        self.btn_undo.clicked.connect(self.editor.undo)
        hdr_layout.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("Redo ⮎")
        self.btn_redo.clicked.connect(self.editor.redo)
        hdr_layout.addWidget(self.btn_redo)

        layout.addLayout(hdr_layout)

        # History list
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

        self.editor.on_history_changed = self.refresh_history
        self.refresh_history()

    def refresh_history(self) -> None:
        """Re-populate list with undo and redo stack items."""
        doc = self.editor.document
        if not doc:
            self.list_widget.clear()
            self.btn_undo.setEnabled(False)
            self.btn_redo.setEnabled(False)
            return

        hm = doc.history_manager
        self.btn_undo.setEnabled(hm.can_undo())
        self.btn_redo.setEnabled(hm.can_redo())
        self.lbl_info.setText(f"History ({hm.undo_count} actions)")

        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        # Initial state baseline
        base_item = QListWidgetItem("✦ New Document")
        base_font = QFont("Segoe UI", 9)
        base_item.setFont(base_font)
        self.list_widget.addItem(base_item)

        # Executed undo stack commands (active)
        for cmd in hm._undo_stack:
            item = QListWidgetItem(f"✓ {cmd.name}")
            font = QFont("Segoe UI", 9)
            item.setFont(font)
            item.setForeground(QColor(0, 229, 255))
            self.list_widget.addItem(item)

        # Undone redo stack commands (dimmed / future)
        for cmd in reversed(hm._redo_stack):
            item = QListWidgetItem(f"↷ {cmd.name}")
            font = QFont("Segoe UI", 9)
            font.setItalic(True)
            item.setFont(font)
            item.setForeground(QColor(120, 130, 150))
            self.list_widget.addItem(item)

        # Select the top of the undo stack
        active_row = hm.undo_count
        self.list_widget.setCurrentRow(active_row)
        self.list_widget.blockSignals(False)

    def _on_item_clicked(self, row: int) -> None:
        doc = self.editor.document
        if not doc or row < 0:
            return
        hm = doc.history_manager
        target_undo_count = row  # row 0 = baseline

        # If target is less than current undo count, perform undos
        while hm.undo_count > target_undo_count and hm.can_undo():
            hm.undo()

        # If target is greater than current undo count, perform redos
        while hm.undo_count < target_undo_count and hm.can_redo():
            hm.redo()

        doc.invalidate_composite()
        self.editor.notify_all()
