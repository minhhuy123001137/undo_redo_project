"""Layers panel dock widget implemented with pure PySide6 APIs (No QSS)."""
from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPalette
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QInputDialog,
    QMessageBox,
)

from apps.mini_photoshop.editor import Editor


class LayerItemWidget(QWidget):
    """Custom widget for a single layer row in the list."""

    def __init__(self, editor: Editor, layer_index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.editor = editor
        self.layer_index = layer_index
        layer = self.editor.document.layers[layer_index]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # Visibility toggle button
        self.btn_vis = QPushButton("👁" if layer.visible else "–")
        self.btn_vis.setFixedSize(28, 24)
        self.btn_vis.clicked.connect(self._toggle_visibility)
        layout.addWidget(self.btn_vis)

        # Layer Name Label
        self.lbl_name = QLabel(layer.name)
        font = QFont("Segoe UI", 11)
        self.lbl_name.setFont(font)
        palette = self.lbl_name.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(226, 232, 240) if layer.visible else QColor(100, 116, 139))
        self.lbl_name.setPalette(palette)
        layout.addWidget(self.lbl_name)

        layout.addStretch()

    def _toggle_visibility(self) -> None:
        layer = self.editor.document.layers[self.layer_index]
        self.editor.set_layer_visibility(self.layer_index, not layer.visible)


class LayersPanel(QWidget):
    """Layers dock panel allowing layer management, opacity, reordering, and visibility."""

    def __init__(self, editor: Editor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.editor = editor
        self.setMinimumWidth(220)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Opacity Row
        op_layout = QHBoxLayout()
        lbl_op = QLabel("Opacity:")
        lbl_op.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        op_layout.addWidget(lbl_op)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(100)
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider_changed)
        op_layout.addWidget(self.slider_opacity)

        self.lbl_opacity_val = QLabel("100%")
        self.lbl_opacity_val.setFont(QFont("Consolas", 10))
        self.lbl_opacity_val.setFixedWidth(42)
        op_layout.addWidget(self.lbl_opacity_val)

        main_layout.addLayout(op_layout)

        # 2. Layers ListWidget
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_list_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self.list_widget)

        # 3. Layer Action Buttons Strip
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self.btn_add = QPushButton("+")
        self.btn_add.setToolTip("Add New Layer")
        self.btn_add.clicked.connect(lambda: self.editor.add_new_layer())
        btn_layout.addWidget(self.btn_add)

        self.btn_del = QPushButton("−")
        self.btn_del.setToolTip("Delete Active Layer")
        self.btn_del.clicked.connect(self.editor.delete_active_layer)
        btn_layout.addWidget(self.btn_del)

        self.btn_dup = QPushButton("Dup")
        self.btn_dup.setToolTip("Duplicate Active Layer")
        self.btn_dup.clicked.connect(self._duplicate_layer)
        btn_layout.addWidget(self.btn_dup)

        self.btn_up = QPushButton("▲")
        self.btn_up.setToolTip("Move Layer Up")
        self.btn_up.clicked.connect(self._move_up)
        btn_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setToolTip("Move Layer Down")
        self.btn_down.clicked.connect(self._move_down)
        btn_layout.addWidget(self.btn_down)

        self.btn_merge = QPushButton("Merge")
        self.btn_merge.setToolTip("Merge Layer Down")
        self.btn_merge.clicked.connect(self._merge_down)
        btn_layout.addWidget(self.btn_merge)

        main_layout.addLayout(btn_layout)

        # Connect editor signals
        self.editor.on_layers_changed = self.refresh_list
        self.refresh_list()

    def refresh_list(self) -> None:
        """Rebuild layer items list matching document layer stack."""
        doc = self.editor.document
        if not doc:
            self.list_widget.clear()
            return

        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        # Display top layers at the top of the list (reverse order)
        for i in reversed(range(len(doc.layers))):
            item = QListWidgetItem()
            item.setSizeHint(QSize(180, 32))
            self.list_widget.addItem(item)
            widget = LayerItemWidget(self.editor, i)
            self.list_widget.setItemWidget(item, widget)

        # Select currently active layer
        active_idx = doc.active_layer_index
        list_row = len(doc.layers) - 1 - active_idx
        if 0 <= list_row < self.list_widget.count():
            self.list_widget.setCurrentRow(list_row)

        # Update opacity slider
        layer = doc.active_layer
        if layer:
            val = int(layer.opacity * 100)
            self.slider_opacity.blockSignals(True)
            self.slider_opacity.setValue(val)
            self.slider_opacity.blockSignals(False)
            self.lbl_opacity_val.setText(f"{val}%")

        self.list_widget.blockSignals(False)

    def _on_list_selection_changed(self, row: int) -> None:
        doc = self.editor.document
        if not doc or row < 0:
            return
        layer_idx = len(doc.layers) - 1 - row
        doc.active_layer_index = max(0, min(layer_idx, len(doc.layers) - 1))
        layer = doc.active_layer
        if layer:
            val = int(layer.opacity * 100)
            self.slider_opacity.blockSignals(True)
            self.slider_opacity.setValue(val)
            self.slider_opacity.blockSignals(False)
            self.lbl_opacity_val.setText(f"{val}%")
        self.editor.notify_all()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        row = self.list_widget.row(item)
        doc = self.editor.document
        if not doc:
            return
        layer_idx = len(doc.layers) - 1 - row
        current_name = doc.layers[layer_idx].name

        new_name, ok = QInputDialog.getText(self, "Rename Layer", "New layer name:", text=current_name)
        if ok and new_name.strip():
            self.editor.rename_layer(layer_idx, new_name.strip())

    def _on_opacity_slider_changed(self, val: int) -> None:
        doc = self.editor.document
        if not doc or not doc.active_layer:
            return
        self.lbl_opacity_val.setText(f"{val}%")
        self.editor.set_layer_opacity(doc.active_layer_index, val / 100.0)

    def _duplicate_layer(self) -> None:
        doc = self.editor.document
        if not doc or not doc.active_layer:
            return
        doc.duplicate_layer(doc.active_layer_index)
        self.editor.notify_all()

    def _move_up(self) -> None:
        doc = self.editor.document
        if not doc:
            return
        idx = doc.active_layer_index
        if idx < len(doc.layers) - 1:
            self.editor.reorder_layer(idx, idx + 1)

    def _move_down(self) -> None:
        doc = self.editor.document
        if not doc:
            return
        idx = doc.active_layer_index
        if idx > 0:
            self.editor.reorder_layer(idx, idx - 1)

    def _merge_down(self) -> None:
        doc = self.editor.document
        if not doc:
            return
        self.editor.merge_down(doc.active_layer_index)
