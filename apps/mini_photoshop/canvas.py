"""Interactive canvas widget displaying the document with zoom, pan, and tool dispatch."""
from typing import Optional, Tuple
from PIL import Image

try:
    from PySide6.QtCore import Qt, QPoint, QRect, QRectF, Signal
    from PySide6.QtGui import QPainter, QColor, QImage, QPixmap, QPen, QBrush, QCursor, QMouseEvent, QWheelEvent, QPaintEvent
    from PySide6.QtWidgets import QWidget
except ImportError:
    # Allows headless testing or tools import before PySide6 loads
    pass

from apps.mini_photoshop.editor import Editor


class CanvasWidget(QWidget):
    """Custom canvas view widget supporting panning, zooming, and drawing tool dispatch."""

    mouse_coords_changed = Signal(int, int)
    zoom_changed = Signal(float)

    def __init__(self, editor: Editor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.editor = editor
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Pan state
        self.is_panning = False
        self.last_mouse_pos = QPoint()
        self.space_held = False

        # Checkerboard cache
        self._checkerboard_tile: Optional[QPixmap] = None
        self._init_checkerboard()

        # Connect editor callbacks
        self.editor.on_canvas_needs_repaint = self.update

    def _init_checkerboard(self) -> None:
        """Create a 16x16 checkerboard pattern for transparency representation."""
        size = 16
        pix = QPixmap(size * 2, size * 2)
        painter = QPainter(pix)
        c1 = QColor(42, 48, 62)
        c2 = QColor(32, 38, 50)
        painter.fillRect(0, 0, size, size, c1)
        painter.fillRect(size, size, size, size, c1)
        painter.fillRect(size, 0, size, size, c2)
        painter.fillRect(0, size, size, size, c2)
        painter.end()
        self._checkerboard_tile = pix

    def widget_to_canvas(self, pos: QPoint) -> Tuple[int, int]:
        """Convert widget pixel coordinates to canvas image pixel coordinates."""
        doc = self.editor.document
        if not doc:
            return 0, 0
        cx = (pos.x() - self.width() / 2.0 - self.editor.pan_x) / self.editor.zoom + doc.width / 2.0
        cy = (pos.y() - self.height() / 2.0 - self.editor.pan_y) / self.editor.zoom + doc.height / 2.0
        return int(cx), int(cy)

    def canvas_to_widget_rect(self) -> QRectF:
        """Calculate document canvas bounding rectangle in widget space."""
        doc = self.editor.document
        if not doc:
            return QRectF()
        w = doc.width * self.editor.zoom
        h = doc.height * self.editor.zoom
        x = self.width() / 2.0 + self.editor.pan_x - w / 2.0
        y = self.height() / 2.0 + self.editor.pan_y - h / 2.0
        return QRectF(x, y, w, h)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space_held = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space_held = False
            self.setCursor(Qt.CursorShape.CrossCursor)
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Check panning with Space or Middle click or Hand tool
        if (
            self.space_held
            or event.button() == Qt.MouseButton.MiddleButton
            or self.editor.active_tool.name == "Hand"
        ):
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            cx, cy = self.widget_to_canvas(event.pos())
            self.editor.active_tool.on_press(self.editor, cx, cy)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        cx, cy = self.widget_to_canvas(event.pos())
        self.mouse_coords_changed.emit(cx, cy)

        if self.is_panning:
            delta = event.pos() - self.last_mouse_pos
            self.editor.pan_x += delta.x()
            self.editor.pan_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()
            return

        if event.buttons() & Qt.MouseButton.LeftButton:
            self.editor.active_tool.on_drag(self.editor, cx, cy)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.OpenHandCursor if self.space_held else Qt.CursorShape.CrossCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            cx, cy = self.widget_to_canvas(event.pos())
            self.editor.active_tool.on_release(self.editor, cx, cy)
            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Zoom centered on cursor
            angle = event.angleDelta().y()
            factor = 1.15 if angle > 0 else (1.0 / 1.15)
            self.editor.zoom_canvas(factor)
            self.zoom_changed.emit(self.editor.zoom)
            self.update()
        else:
            # Scroll pan
            delta = event.pixelDelta()
            if delta.isNull():
                delta = event.angleDelta() / 4
            self.editor.pan_x += delta.x()
            self.editor.pan_y += delta.y()
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 1. Background (Dark charcoal studio)
        painter.fillRect(self.rect(), QColor(22, 26, 36))

        doc = self.editor.document
        if not doc:
            painter.end()
            return

        dest_rect = self.canvas_to_widget_rect()

        # 2. Draw soft drop shadow behind canvas
        shadow_rect = dest_rect.adjusted(4, 6, 4, 6)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 90))

        # 3. Draw transparency checkerboard pattern
        if self._checkerboard_tile:
            painter.setClipRect(dest_rect)
            brush = QBrush(self._checkerboard_tile)
            painter.fillRect(dest_rect, brush)

        # 4. Draw Document Composite Image
        comp_img = doc.get_composite_image()
        raw_data = comp_img.tobytes("raw", "RGBA")
        q_img = QImage(
            raw_data,
            doc.width,
            doc.height,
            doc.width * 4,
            QImage.Format.Format_RGBA8888,
        )

        # Use smooth transformation if zoomed out, nearest neighbor if zoomed in (pixel art)
        if self.editor.zoom < 1.0:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        else:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        painter.drawImage(dest_rect, q_img)
        painter.setClipping(False)

        # 5. Canvas outline border
        pen = QPen(QColor(0, 229, 255, 180), 1)
        painter.setPen(pen)
        painter.drawRect(dest_rect)

        painter.end()
