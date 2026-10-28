"""Left vertical toolbar widget designed with QPainter and QPalette (No QSS)."""
from typing import Dict, Optional
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup

from apps.mini_photoshop.editor import Editor


class CustomToolButton(QPushButton):
    """Button rendered with QPainter featuring dark theme, hover, and active state."""

    def __init__(self, text: str, shortcut: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.tool_label = text
        self.tool_shortcut = shortcut
        self.is_active_tool = False
        self.setFixedSize(44, 44)
        self.setToolTip(f"{text} ({shortcut})")

    def set_active(self, active: bool) -> None:
        self.is_active_tool = active
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()

        # Background color based on state
        if self.is_active_tool:
            bg_color = QColor(0, 229, 255, 45)
            border_color = QColor(0, 229, 255)
            text_color = QColor(255, 255, 255)
        elif self.underMouse():
            bg_color = QColor(36, 46, 68)
            border_color = QColor(59, 82, 135)
            text_color = QColor(226, 232, 240)
        else:
            bg_color = QColor(22, 28, 42)
            border_color = QColor(38, 52, 86)
            text_color = QColor(148, 163, 184)

        # Draw rounded card body
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2 if self.is_active_tool else 1))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)

        # Draw tool shortcut letter
        font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.tool_shortcut)

        painter.end()


class ToolBarWidget(QWidget):
    """Vertical tools strip on the left side of the studio."""

    def __init__(self, editor: Editor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.editor = editor
        self.setFixedWidth(56)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(6)

        tool_defs = [
            ("brush", "Brush", "B"),
            ("pencil", "Pencil", "P"),
            ("eraser", "Eraser", "E"),
            ("fill", "Bucket", "G"),
            ("rectangle", "Rect", "U"),
            ("ellipse", "Circle", "O"),
            ("move", "Move", "V"),
            ("eyedropper", "Picker", "I"),
            ("hand", "Hand", "H"),
            ("zoom", "Zoom", "Z"),
        ]

        self.buttons: Dict[str, CustomToolButton] = {}
        for key, name, sc in tool_defs:
            btn = CustomToolButton(name, sc, self)
            btn.clicked.connect(lambda checked=False, k=key: self.editor.set_tool(k))
            layout.addWidget(btn)
            self.buttons[key] = btn

        layout.addStretch()

        # Connect editor tool change signal
        self.editor.on_tool_changed = self._on_tool_changed
        self._on_tool_changed("brush")

    def _on_tool_changed(self, active_key: str) -> None:
        for key, btn in self.buttons.items():
            btn.set_active(key == active_key)

    def paintEvent(self, event) -> None:
        # Dark panel backdrop
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(16, 20, 32))
        painter.setPen(QPen(QColor(32, 42, 65), 1))
        painter.drawLine(self.rect().topRight(), self.rect().bottomRight())
        painter.end()
