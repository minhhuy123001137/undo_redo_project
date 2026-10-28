"""Color Picker and Tool Properties panel (No QSS)."""
from typing import Optional, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QSlider,
    QColorDialog,
)

from apps.mini_photoshop.editor import Editor


class ColorSwatchButton(QPushButton):
    """Small square clickable color swatch."""

    def __init__(self, color: Tuple[int, int, int, int], on_selected, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.color = color
        self.on_selected = on_selected
        self.setFixedSize(22, 22)
        self.clicked.connect(lambda: self.on_selected(self.color))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        qc = QColor(self.color[0], self.color[1], self.color[2], self.color[3])
        painter.setBrush(QBrush(qc))
        border_col = QColor(255, 255, 255, 180) if self.underMouse() else QColor(30, 40, 60)
        painter.setPen(QPen(border_col, 1))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 3, 3)
        painter.end()


class ColorPickerPanel(QWidget):
    """Dock widget for selecting colors and adjusting tool properties."""

    def __init__(self, editor: Editor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.editor = editor
        self.setMinimumWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Color Preview & Custom Picker Button
        c_layout = QHBoxLayout()
        self.lbl_color_preview = QLabel()
        self.lbl_color_preview.setFixedSize(48, 36)
        c_layout.addWidget(self.lbl_color_preview)

        self.btn_pick_custom = QPushButton("Custom Color...")
        self.btn_pick_custom.clicked.connect(self._open_color_dialog)
        c_layout.addWidget(self.btn_pick_custom)
        layout.addLayout(c_layout)

        # 2. Preset Swatches Palette
        swatches = [
            (0, 0, 0, 255), (255, 255, 255, 255), (128, 128, 128, 255),
            (239, 68, 68, 255), (249, 115, 22, 255), (245, 158, 11, 255),
            (16, 185, 129, 255), (6, 182, 212, 255), (0, 229, 255, 255),
            (59, 130, 246, 255), (168, 85, 247, 255), (236, 72, 153, 255),
        ]
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, col in enumerate(swatches):
            r = i // 6
            c = i % 6
            btn = ColorSwatchButton(col, self._set_swatch_color)
            grid.addWidget(btn, r, c)
        layout.addLayout(grid)

        # 3. Tool Size Slider
        layout.addWidget(QLabel("Brush / Tool Size:"))
        size_layout = QHBoxLayout()
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(1, 100)
        self.slider_size.setValue(self.editor.tool_size)
        self.slider_size.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self.slider_size)

        self.lbl_size_val = QLabel(f"{self.editor.tool_size}px")
        self.lbl_size_val.setFixedWidth(40)
        size_layout.addWidget(self.lbl_size_val)
        layout.addLayout(size_layout)

        # 4. Fill Tolerance Slider
        layout.addWidget(QLabel("Fill Tolerance:"))
        tol_layout = QHBoxLayout()
        self.slider_tol = QSlider(Qt.Orientation.Horizontal)
        self.slider_tol.setRange(0, 100)
        self.slider_tol.setValue(self.editor.fill_tolerance)
        self.slider_tol.valueChanged.connect(self._on_tol_changed)
        tol_layout.addWidget(self.slider_tol)

        self.lbl_tol_val = QLabel(f"{self.editor.fill_tolerance}")
        self.lbl_tol_val.setFixedWidth(40)
        tol_layout.addWidget(self.lbl_tol_val)
        layout.addLayout(tol_layout)

        layout.addStretch()

        self.editor.on_color_changed = self._update_color_preview
        self._update_color_preview(self.editor.primary_color)

    def _set_swatch_color(self, color: Tuple[int, int, int, int]) -> None:
        self.editor.set_primary_color(color)

    def _open_color_dialog(self) -> None:
        cur = self.editor.primary_color
        initial = QColor(cur[0], cur[1], cur[2], cur[3])
        color = QColorDialog.getColor(initial, self, "Select Color")
        if color.isValid():
            rgba = (color.red(), color.green(), color.blue(), color.alpha())
            self.editor.set_primary_color(rgba)

    def _on_size_changed(self, val: int) -> None:
        self.editor.tool_size = val
        self.lbl_size_val.setText(f"{val}px")

    def _on_tol_changed(self, val: int) -> None:
        self.editor.fill_tolerance = val
        self.lbl_tol_val.setText(f"{val}")

    def _update_color_preview(self, color: Tuple[int, int, int, int]) -> None:
        # Paint preview label using QPainter / palette
        palette = self.lbl_color_preview.palette()
        qc = QColor(color[0], color[1], color[2], color[3])
        self.lbl_color_preview.setAutoFillBackground(True)
        palette.setColor(self.lbl_color_preview.backgroundRole(), qc)
        self.lbl_color_preview.setPalette(palette)
