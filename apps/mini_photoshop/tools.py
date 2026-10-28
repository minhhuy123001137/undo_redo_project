"""Drawing and editing tools for Pixel Studio."""
from collections import deque
import math
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw

from apps.mini_photoshop.commands import ImagePatchCommand, MoveLayerContentCommand


class Tool:
    """Base class for all interactive canvas tools."""

    name: str = "Base Tool"
    shortcut: str = ""

    def on_press(self, editor, x: int, y: int) -> None:
        pass

    def on_drag(self, editor, x: int, y: int) -> None:
        pass

    def on_release(self, editor, x: int, y: int) -> None:
        pass


class StrokeBasedTool(Tool):
    """Base class for tools that modify pixels with a stroke and generate ImagePatchCommand."""

    def __init__(self) -> None:
        self.is_active = False
        self.points: List[Tuple[int, int]] = []
        self.before_layer_image: Optional[Image.Image] = None
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0

    def _start_stroke(self, editor, x: int, y: int) -> bool:
        doc = editor.document
        layer = doc.active_layer
        if layer is None or not layer.visible:
            return False

        self.is_active = True
        self.points = [(x, y)]
        self.before_layer_image = layer.image.copy()

        pad = editor.tool_size + 4
        self.min_x = max(0, x - pad)
        self.max_x = min(doc.width, x + pad)
        self.min_y = max(0, y - pad)
        self.max_y = min(doc.height, y + pad)
        return True

    def _update_bbox(self, editor, x: int, y: int) -> None:
        doc = editor.document
        pad = editor.tool_size + 4
        self.min_x = max(0, min(self.min_x, x - pad))
        self.max_x = min(doc.width, max(self.max_x, x + pad))
        self.min_y = max(0, min(self.min_y, y - pad))
        self.max_y = min(doc.height, max(self.max_y, y + pad))

    def _finish_stroke(self, editor, command_name: str) -> None:
        if not self.is_active or self.before_layer_image is None:
            return

        doc = editor.document
        layer = doc.active_layer
        if layer is None:
            self.is_active = False
            return

        # Ensure valid bounding box
        bx0 = max(0, int(self.min_x))
        by0 = max(0, int(self.min_y))
        bx1 = min(doc.width, max(bx0 + 1, int(self.max_x)))
        by1 = min(doc.height, max(by0 + 1, int(self.max_y)))

        before_patch = self.before_layer_image.crop((bx0, by0, bx1, by1))
        after_patch = layer.image.crop((bx0, by0, bx1, by1))

        # Create reversible command
        cmd = ImagePatchCommand(
            document=doc,
            layer=layer,
            bbox=(bx0, by0, bx1, by1),
            before_patch=before_patch,
            after_patch=after_patch,
            name=command_name,
        )
        # Execute via HistoryManager so it is recorded in the undo stack
        # Note: image is already modified, execute will paste after_patch and keep it dirty
        doc.history_manager.execute(cmd)
        doc.invalidate_composite()

        self.is_active = False
        self.before_layer_image = None
        self.points.clear()


class BrushTool(StrokeBasedTool):
    """Soft/anti-aliased circular brush."""

    name = "Brush"
    shortcut = "B"

    def on_press(self, editor, x: int, y: int) -> None:
        if self._start_stroke(editor, x, y):
            self._draw_segment(editor, x, y, x, y)

    def on_drag(self, editor, x: int, y: int) -> None:
        if not self.is_active:
            return
        last_x, last_y = self.points[-1]
        self._draw_segment(editor, last_x, last_y, x, y)
        self.points.append((x, y))
        self._update_bbox(editor, x, y)

    def on_release(self, editor, x: int, y: int) -> None:
        self._finish_stroke(editor, "Brush Stroke")

    def _draw_segment(self, editor, x0: int, y0: int, x1: int, y1: int) -> None:
        layer = editor.document.active_layer
        draw = ImageDraw.Draw(layer.image)
        color = editor.primary_color  # (R, G, B, A)
        radius = max(1, editor.tool_size // 2)

        # Draw circle at endpoints and line connecting them
        draw.ellipse([x0 - radius, y0 - radius, x0 + radius, y0 + radius], fill=color)
        draw.ellipse([x1 - radius, y1 - radius, x1 + radius, y1 + radius], fill=color)
        if (x0, y0) != (x1, y1):
            draw.line([(x0, y0), (x1, y1)], fill=color, width=editor.tool_size)
        editor.document.invalidate_composite()


class EraserTool(StrokeBasedTool):
    """Eraser that removes pixels back to transparent."""

    name = "Eraser"
    shortcut = "E"

    def on_press(self, editor, x: int, y: int) -> None:
        if self._start_stroke(editor, x, y):
            self._erase_segment(editor, x, y, x, y)

    def on_drag(self, editor, x: int, y: int) -> None:
        if not self.is_active:
            return
        last_x, last_y = self.points[-1]
        self._erase_segment(editor, last_x, last_y, x, y)
        self.points.append((x, y))
        self._update_bbox(editor, x, y)

    def on_release(self, editor, x: int, y: int) -> None:
        self._finish_stroke(editor, "Eraser Stroke")

    def _erase_segment(self, editor, x0: int, y0: int, x1: int, y1: int) -> None:
        layer = editor.document.active_layer
        # Draw with transparent RGBA (0, 0, 0, 0) in "RGBA" mode requires masking or direct pixel editing
        draw = ImageDraw.Draw(layer.image)
        # Using (0, 0, 0, 0) replacement
        radius = max(1, editor.tool_size // 2)
        draw.ellipse([x0 - radius, y0 - radius, x0 + radius, y0 + radius], fill=(0, 0, 0, 0))
        draw.ellipse([x1 - radius, y1 - radius, x1 + radius, y1 + radius], fill=(0, 0, 0, 0))
        if (x0, y0) != (x1, y1):
            draw.line([(x0, y0), (x1, y1)], fill=(0, 0, 0, 0), width=editor.tool_size)
        editor.document.invalidate_composite()


class PencilTool(StrokeBasedTool):
    """Sharp non-aliased pixel drawing tool."""

    name = "Pencil"
    shortcut = "P"

    def on_press(self, editor, x: int, y: int) -> None:
        if self._start_stroke(editor, x, y):
            self._draw_pixel(editor, x, y)

    def on_drag(self, editor, x: int, y: int) -> None:
        if not self.is_active:
            return
        last_x, last_y = self.points[-1]
        # Bresenham-like linear interpolation
        dist = max(abs(x - last_x), abs(y - last_y))
        for step in range(1, dist + 1):
            t = step / max(1, dist)
            ix = int(last_x + (x - last_x) * t)
            iy = int(last_y + (y - last_y) * t)
            self._draw_pixel(editor, ix, iy)
            self._update_bbox(editor, ix, iy)
        self.points.append((x, y))

    def on_release(self, editor, x: int, y: int) -> None:
        self._finish_stroke(editor, "Pencil Stroke")

    def _draw_pixel(self, editor, x: int, y: int) -> None:
        layer = editor.document.active_layer
        w, h = layer.image.size
        sz = max(1, editor.tool_size)
        color = editor.primary_color
        draw = ImageDraw.Draw(layer.image)
        if sz == 1:
            if 0 <= x < w and 0 <= y < h:
                layer.image.putpixel((x, y), color)
        else:
            r = sz // 2
            draw.rectangle([x - r, y - r, x + r, y + r], fill=color)
        editor.document.invalidate_composite()


class FillTool(Tool):
    """Flood fill / paint bucket tool with tolerance."""

    name = "Paint Bucket"
    shortcut = "G"

    def on_press(self, editor, x: int, y: int) -> None:
        doc = editor.document
        layer = doc.active_layer
        if layer is None or not layer.visible:
            return
        if not (0 <= x < doc.width and 0 <= y < doc.height):
            return

        target_color = layer.image.getpixel((x, y))
        fill_color = editor.primary_color
        if target_color == fill_color:
            return

        before_patch = layer.image.copy()

        # BFS Flood Fill
        pixels = layer.image.load()
        w, h = doc.width, doc.height
        visited = set()
        queue = deque([(x, y)])
        visited.add((x, y))

        min_x, max_x = x, x
        min_y, max_y = y, y

        tolerance = getattr(editor, "fill_tolerance", 15)

        def color_match(c1, c2):
            return (
                abs(c1[0] - c2[0]) <= tolerance
                and abs(c1[1] - c2[1]) <= tolerance
                and abs(c1[2] - c2[2]) <= tolerance
                and abs(c1[3] - c2[3]) <= tolerance
            )

        while queue:
            cx, cy = queue.popleft()
            pixels[cx, cy] = fill_color

            min_x = min(min_x, cx)
            max_x = max(max_x, cx)
            min_y = min(min_y, cy)
            max_y = max(max_y, cy)

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    if color_match(pixels[nx, ny], target_color):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

        bbox = (min_x, min_y, max_x + 1, max_y + 1)
        after_patch = layer.image.crop(bbox)
        before_crop = before_patch.crop(bbox)

        cmd = ImagePatchCommand(
            document=doc,
            layer=layer,
            bbox=bbox,
            before_patch=before_crop,
            after_patch=after_patch,
            name="Flood Fill",
        )
        doc.history_manager.execute(cmd)
        doc.invalidate_composite()


class RectangleTool(Tool):
    """Draws outlined or filled rectangles."""

    name = "Rectangle"
    shortcut = "U"

    def __init__(self) -> None:
        self.start_pos = None
        self.before_layer_image = None

    def on_press(self, editor, x: int, y: int) -> None:
        layer = editor.document.active_layer
        if layer and layer.visible:
            self.start_pos = (x, y)
            self.before_layer_image = layer.image.copy()

    def on_release(self, editor, x: int, y: int) -> None:
        if not self.start_pos or not self.before_layer_image:
            return

        doc = editor.document
        layer = doc.active_layer
        if not layer:
            return

        x0, y0 = self.start_pos
        x1, y1 = x, y
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)

        if min_x == max_x or min_y == max_y:
            self.start_pos = None
            return

        draw = ImageDraw.Draw(layer.image)
        outline = editor.primary_color
        fill = getattr(editor, "secondary_color", None)
        width = max(1, editor.tool_size)

        draw.rectangle([min_x, min_y, max_x, max_y], outline=outline, fill=fill, width=width)

        pad = width + 2
        bx0 = max(0, min_x - pad)
        by0 = max(0, min_y - pad)
        bx1 = min(doc.width, max_x + pad)
        by1 = min(doc.height, max_y + pad)

        before_crop = self.before_layer_image.crop((bx0, by0, bx1, by1))
        after_crop = layer.image.crop((bx0, by0, bx1, by1))

        cmd = ImagePatchCommand(doc, layer, (bx0, by0, bx1, by1), before_crop, after_crop, name="Draw Rectangle")
        doc.history_manager.execute(cmd)
        doc.invalidate_composite()

        self.start_pos = None
        self.before_layer_image = None


class EllipseTool(Tool):
    """Draws outlined or filled ellipses."""

    name = "Ellipse"
    shortcut = "O"

    def __init__(self) -> None:
        self.start_pos = None
        self.before_layer_image = None

    def on_press(self, editor, x: int, y: int) -> None:
        layer = editor.document.active_layer
        if layer and layer.visible:
            self.start_pos = (x, y)
            self.before_layer_image = layer.image.copy()

    def on_release(self, editor, x: int, y: int) -> None:
        if not self.start_pos or not self.before_layer_image:
            return

        doc = editor.document
        layer = doc.active_layer
        if not layer:
            return

        x0, y0 = self.start_pos
        x1, y1 = x, y
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)

        if min_x == max_x or min_y == max_y:
            self.start_pos = None
            return

        draw = ImageDraw.Draw(layer.image)
        outline = editor.primary_color
        fill = getattr(editor, "secondary_color", None)
        width = max(1, editor.tool_size)

        draw.ellipse([min_x, min_y, max_x, max_y], outline=outline, fill=fill, width=width)

        pad = width + 2
        bx0 = max(0, min_x - pad)
        by0 = max(0, min_y - pad)
        bx1 = min(doc.width, max_x + pad)
        by1 = min(doc.height, max_y + pad)

        before_crop = self.before_layer_image.crop((bx0, by0, bx1, by1))
        after_crop = layer.image.crop((bx0, by0, bx1, by1))

        cmd = ImagePatchCommand(doc, layer, (bx0, by0, bx1, by1), before_crop, after_crop, name="Draw Ellipse")
        doc.history_manager.execute(cmd)
        doc.invalidate_composite()

        self.start_pos = None
        self.before_layer_image = None


class MoveTool(Tool):
    """Moves content of the active layer."""

    name = "Move"
    shortcut = "V"

    def __init__(self) -> None:
        self.start_pos = None

    def on_press(self, editor, x: int, y: int) -> None:
        layer = editor.document.active_layer
        if layer and layer.visible:
            self.start_pos = (x, y)

    def on_release(self, editor, x: int, y: int) -> None:
        if not self.start_pos:
            return
        dx = x - self.start_pos[0]
        dy = y - self.start_pos[1]
        self.start_pos = None

        if dx == 0 and dy == 0:
            return

        doc = editor.document
        layer = doc.active_layer
        if layer:
            cmd = MoveLayerContentCommand(doc, layer, dx, dy)
            doc.history_manager.execute(cmd)


class EyedropperTool(Tool):
    """Samples color from the canvas composite."""

    name = "Eyedropper"
    shortcut = "I"

    def on_press(self, editor, x: int, y: int) -> None:
        doc = editor.document
        if 0 <= x < doc.width and 0 <= y < doc.height:
            comp = doc.get_composite_image()
            color = comp.getpixel((x, y))
            editor.set_primary_color(color)


class HandTool(Tool):
    """Pans the canvas view."""

    name = "Hand"
    shortcut = "H"


class ZoomTool(Tool):
    """Zooms the canvas view in or out."""

    name = "Zoom"
    shortcut = "Z"

    def on_press(self, editor, x: int, y: int) -> None:
        editor.zoom_canvas(1.25)
