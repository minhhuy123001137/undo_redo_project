"""Main Application Window for Pixel Studio (Pure PySide6, No QSS)."""
import os
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QLabel,
    QStatusBar,
    QDialog,
    QFormLayout,
    QSpinBox,
    QDialogButtonBox,
)

from apps.mini_photoshop.editor import Editor
from apps.mini_photoshop.document import Document
from apps.mini_photoshop.canvas import CanvasWidget
from apps.mini_photoshop.file_manager import FileManager
from apps.mini_photoshop.ui.toolbar import ToolBarWidget
from apps.mini_photoshop.ui.layers_panel import LayersPanel
from apps.mini_photoshop.ui.history_panel import HistoryPanel
from apps.mini_photoshop.ui.color_picker import ColorPickerPanel


class NewCanvasDialog(QDialog):
    """Dialog prompting for new document dimensions."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Canvas")
        self.setFixedSize(300, 160)

        layout = QFormLayout(self)
        self.spin_w = QSpinBox()
        self.spin_w.setRange(16, 8192)
        self.spin_w.setValue(800)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(16, 8192)
        self.spin_h.setValue(600)

        layout.addRow("Width (px):", self.spin_w)
        layout.addRow("Height (px):", self.spin_h)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_dimensions(self) -> tuple[int, int]:
        return self.spin_w.value(), self.spin_h.value()


class MainWindow(QMainWindow):
    """Master Creative Studio Window."""

    def __init__(self, editor: Optional[Editor] = None) -> None:
        super().__init__()
        self.editor = editor or Editor()
        self.setWindowTitle("PIXEL STUDIO – Mini Photoshop")
        self.resize(1200, 800)

        self._setup_dark_palette()
        self._init_central_view()
        self._init_menus()
        self._init_docks()
        self._init_status_bar()

        # Connect editor signals
        self.editor.on_status_changed = self._on_status_message
        self.editor.on_document_changed = self._on_document_changed

    def _setup_dark_palette(self) -> None:
        """Apply sleek professional dark theme via QPalette without using QSS."""
        palette = QPalette()
        # Window & Surface
        palette.setColor(QPalette.ColorRole.Window, QColor(18, 24, 38))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(226, 232, 240))
        palette.setColor(QPalette.ColorRole.Base, QColor(14, 18, 30))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(24, 32, 48))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(18, 24, 38))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(226, 232, 240))
        palette.setColor(QPalette.ColorRole.Text, QColor(226, 232, 240))
        palette.setColor(QPalette.ColorRole.Button, QColor(28, 36, 56))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(226, 232, 240))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(0, 229, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 229, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(10, 14, 24))
        self.setPalette(palette)

    def _init_central_view(self) -> None:
        """Assemble central canvas and left toolbar."""
        central_container = QWidget()
        layout = QHBoxLayout(central_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left vertical tool strip
        self.toolbar_widget = ToolBarWidget(self.editor, self)
        layout.addWidget(self.toolbar_widget)

        # Main interactive canvas
        self.canvas_widget = CanvasWidget(self.editor, self)
        layout.addWidget(self.canvas_widget)

        self.setCentralWidget(central_container)

    def _init_menus(self) -> None:
        """Setup top menu bar actions and keyboard shortcuts."""
        mb = self.menuBar()

        # 1. File Menu
        menu_file = mb.addMenu("&File")

        act_new = QAction("&New Project...", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
        act_new.triggered.connect(self._file_new)
        menu_file.addAction(act_new)

        act_open = QAction("&Open Image...", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self._file_open)
        menu_file.addAction(act_open)

        act_open_proj = QAction("Open &Project (.pstudio)...", self)
        act_open_proj.triggered.connect(self._file_open_project)
        menu_file.addAction(act_open_proj)

        menu_file.addSeparator()

        act_save = QAction("&Save Project", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self._file_save)
        menu_file.addAction(act_save)

        act_save_as = QAction("Save &As...", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self._file_save_as)
        menu_file.addAction(act_save_as)

        menu_file.addSeparator()

        act_exp_png = QAction("Export as &PNG...", self)
        act_exp_png.triggered.connect(self._export_png)
        menu_file.addAction(act_exp_png)

        act_exp_jpg = QAction("Export as &JPEG...", self)
        act_exp_jpg.triggered.connect(self._export_jpeg)
        menu_file.addAction(act_exp_jpg)

        menu_file.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # 2. Edit Menu
        menu_edit = mb.addMenu("&Edit")

        self.act_undo = QAction("&Undo", self)
        self.act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.act_undo.triggered.connect(self.editor.undo)
        menu_edit.addAction(self.act_undo)

        self.act_redo = QAction("&Redo", self)
        self.act_redo.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.act_redo.triggered.connect(self.editor.redo)
        menu_edit.addAction(self.act_redo)

        # 3. Layer Menu
        menu_layer = mb.addMenu("&Layer")

        act_add_l = QAction("&New Layer", self)
        act_add_l.setShortcut(QKeySequence("Ctrl+Shift+N"))
        act_add_l.triggered.connect(lambda: self.editor.add_new_layer())
        menu_layer.addAction(act_add_l)

        act_dup_l = QAction("&Duplicate Layer", self)
        act_dup_l.triggered.connect(lambda: self.editor.document.duplicate_layer(self.editor.document.active_layer_index) if self.editor.document else None)
        menu_layer.addAction(act_dup_l)

        act_del_l = QAction("&Delete Layer", self)
        act_del_l.triggered.connect(self.editor.delete_active_layer)
        menu_layer.addAction(act_del_l)

        act_merge_l = QAction("&Merge Down", self)
        act_merge_l.setShortcut(QKeySequence("Ctrl+E"))
        act_merge_l.triggered.connect(lambda: self.editor.merge_down(self.editor.document.active_layer_index) if self.editor.document else None)
        menu_layer.addAction(act_merge_l)

        # 4. View Menu
        menu_view = mb.addMenu("&View")

        act_zoom_in = QAction("Zoom &In", self)
        act_zoom_in.setShortcut(QKeySequence("Ctrl+="))
        act_zoom_in.triggered.connect(lambda: self.editor.zoom_canvas(1.25))
        menu_view.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom &Out", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(lambda: self.editor.zoom_canvas(0.8))
        menu_view.addAction(act_zoom_out)

        act_zoom_100 = QAction("&Actual Pixels (100%)", self)
        act_zoom_100.setShortcut(QKeySequence("Ctrl+0"))
        act_zoom_100.triggered.connect(self._zoom_100)
        menu_view.addAction(act_zoom_100)

        # 5. Help Menu
        menu_help = mb.addMenu("&Help")
        act_about = QAction("&About Pixel Studio", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

    def _init_docks(self) -> None:
        """Setup right dock panels: Color/Properties, Layers, History."""
        # Dock 1: Color Picker & Tool Settings
        self.dock_color = QDockWidget("Color & Tool Settings", self)
        self.color_panel = ColorPickerPanel(self.editor, self)
        self.dock_color.setWidget(self.color_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_color)

        # Dock 2: Layers
        self.dock_layers = QDockWidget("Layers", self)
        self.layers_panel = LayersPanel(self.editor, self)
        self.dock_layers.setWidget(self.layers_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_layers)

        # Dock 3: History
        self.dock_history = QDockWidget("History", self)
        self.history_panel = HistoryPanel(self.editor, self)
        self.dock_history.setWidget(self.history_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_history)

    def _init_status_bar(self) -> None:
        """Setup bottom status bar with dimensions, zoom, tool, and mouse coords."""
        sb = self.statusBar()
        self.lbl_status_coords = QLabel("X: 0, Y: 0")
        self.lbl_status_coords.setFixedWidth(120)
        sb.addPermanentWidget(self.lbl_status_coords)

        self.lbl_status_dim = QLabel("800 x 600 px")
        self.lbl_status_dim.setFixedWidth(130)
        sb.addPermanentWidget(self.lbl_status_dim)

        self.lbl_status_zoom = QLabel("Zoom: 100%")
        self.lbl_status_zoom.setFixedWidth(100)
        sb.addPermanentWidget(self.lbl_status_zoom)

        self.lbl_status_tool = QLabel("Tool: Brush")
        self.lbl_status_tool.setFixedWidth(120)
        sb.addPermanentWidget(self.lbl_status_tool)

        # Connect canvas signals to status bar
        self.canvas_widget.mouse_coords_changed.connect(self._on_coords_changed)
        self.canvas_widget.zoom_changed.connect(self._on_zoom_changed)

    def _on_coords_changed(self, x: int, y: int) -> None:
        self.lbl_status_coords.setText(f"X: {x}, Y: {y}")

    def _on_zoom_changed(self, zoom: float) -> None:
        self.lbl_status_zoom.setText(f"Zoom: {int(zoom * 100)}%")

    def _on_status_message(self, msg: str) -> None:
        self.statusBar().showMessage(msg, 3000)

    def _on_document_changed(self) -> None:
        doc = self.editor.document
        if doc:
            self.lbl_status_dim.setText(f"{doc.width} x {doc.height} px")
            title = f"{doc.name}{'*' if doc.is_dirty else ''} - PIXEL STUDIO"
            self.setWindowTitle(title)

    def _zoom_100(self) -> None:
        self.editor.zoom = 1.0
        self.editor.pan_x = 0.0
        self.editor.pan_y = 0.0
        self.canvas_widget.update()
        self._on_zoom_changed(1.0)

    # ---------------------------------------------------------
    # File Operations
    # ---------------------------------------------------------
    def _file_new(self) -> None:
        dlg = NewCanvasDialog(self)
        if dlg.exec():
            w, h = dlg.get_dimensions()
            new_doc = Document(w, h, name="Untitled")
            self.editor.set_document(new_doc)
            self._on_document_changed()

    def _file_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*.*)",
        )
        if path:
            try:
                doc = FileManager.open_image(path)
                self.editor.set_document(doc)
                self._on_document_changed()
            except Exception as e:
                QMessageBox.critical(self, "Error Opening Image", str(e))

    def _file_open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Pixel Studio Project",
            "",
            "Pixel Studio (*.pstudio);;All Files (*.*)",
        )
        if path:
            try:
                doc = FileManager.load_project(path)
                self.editor.set_document(doc)
                self._on_document_changed()
            except Exception as e:
                QMessageBox.critical(self, "Error Opening Project", str(e))

    def _file_save(self) -> None:
        doc = self.editor.document
        if not doc:
            return
        if doc.file_path and doc.file_path.endswith(".pstudio"):
            try:
                FileManager.save_project(doc, doc.file_path)
                self._on_document_changed()
                self.statusBar().showMessage(f"Project saved to {doc.file_path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error Saving Project", str(e))
        else:
            self._file_save_as()

    def _file_save_as(self) -> None:
        doc = self.editor.document
        if not doc:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            f"{doc.name}.pstudio",
            "Pixel Studio Project (*.pstudio)",
        )
        if path:
            try:
                FileManager.save_project(doc, path)
                self._on_document_changed()
                self.statusBar().showMessage(f"Saved project: {path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error Saving Project", str(e))

    def _export_png(self) -> None:
        doc = self.editor.document
        if not doc:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", f"{doc.name}.png", "PNG Image (*.png)")
        if path:
            try:
                FileManager.export_png(doc, path)
                self.statusBar().showMessage(f"Exported PNG: {path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _export_jpeg(self) -> None:
        doc = self.editor.document
        if not doc:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export JPEG", f"{doc.name}.jpg", "JPEG Image (*.jpg *.jpeg)")
        if path:
            try:
                FileManager.export_jpeg(doc, path)
                self.statusBar().showMessage(f"Exported JPEG: {path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About Pixel Studio",
            "PIXEL STUDIO – Mini Photoshop\n\n"
            "Part of the PYTHON UNDO/REDO LAB project.\n"
            "Built with PySide6, Pillow, and the Core Dual-Stack Undo/Redo Engine.\n\n"
            "Developed by Senior Python Software Architect.",
        )
