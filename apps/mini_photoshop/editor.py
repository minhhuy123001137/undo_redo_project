"""Editor controller binding Document, Tools, Commands, and UI views."""
from typing import Callable, Dict, List, Optional, Tuple

from apps.mini_photoshop.document import Document
from apps.mini_photoshop.layers import Layer
from apps.mini_photoshop.tools import (
    BrushTool,
    EllipseTool,
    EraserTool,
    EyedropperTool,
    FillTool,
    HandTool,
    MoveTool,
    PencilTool,
    RectangleTool,
    Tool,
    ZoomTool,
)
from apps.mini_photoshop.commands import (
    AddLayerCommand,
    DeleteLayerCommand,
    MergeDownCommand,
    RenameLayerCommand,
    ReorderLayerCommand,
    SetLayerOpacityCommand,
    SetLayerVisibilityCommand,
)


class Editor:
    """Central state and controller for the Pixel Studio session."""

    def __init__(self, initial_document: Optional[Document] = None) -> None:
        self.document: Optional[Document] = initial_document or Document(800, 600, name="Untitled-1")

        # Available Tools map
        self.tools: Dict[str, Tool] = {
            "brush": BrushTool(),
            "eraser": EraserTool(),
            "pencil": PencilTool(),
            "fill": FillTool(),
            "rectangle": RectangleTool(),
            "ellipse": EllipseTool(),
            "move": MoveTool(),
            "eyedropper": EyedropperTool(),
            "hand": HandTool(),
            "zoom": ZoomTool(),
        }
        self.active_tool: Tool = self.tools["brush"]

        # Tool parameters
        self.primary_color: Tuple[int, int, int, int] = (0, 229, 255, 255)  # Cyan
        self.secondary_color: Optional[Tuple[int, int, int, int]] = None
        self.tool_size: int = 8
        self.fill_tolerance: int = 20

        # Viewport navigation
        self.zoom: float = 1.0
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0

        # UI Notification Callbacks
        self.on_canvas_needs_repaint: Optional[Callable[[], None]] = None
        self.on_layers_changed: Optional[Callable[[], None]] = None
        self.on_history_changed: Optional[Callable[[], None]] = None
        self.on_tool_changed: Optional[Callable[[str], None]] = None
        self.on_color_changed: Optional[Callable[[Tuple[int, int, int, int]], None]] = None
        self.on_status_changed: Optional[Callable[[str], None]] = None

    def set_tool(self, tool_key: str) -> None:
        """Switch active tool."""
        if tool_key in self.tools:
            self.active_tool = self.tools[tool_key]
            if self.on_tool_changed:
                self.on_tool_changed(tool_key)
            if self.on_status_changed:
                self.on_status_changed(f"Active Tool: {self.active_tool.name}")

    def set_primary_color(self, color: Tuple[int, int, int, int]) -> None:
        """Update active painting color."""
        self.primary_color = color
        if self.on_color_changed:
            self.on_color_changed(color)

    def set_document(self, doc: Document) -> None:
        """Switch or set document."""
        self.document = doc
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.notify_all()

    def zoom_canvas(self, factor: float) -> None:
        """Adjust viewport zoom level."""
        new_zoom = max(0.1, min(16.0, self.zoom * factor))
        self.zoom = new_zoom
        if self.on_canvas_needs_repaint:
            self.on_canvas_needs_repaint()

    def notify_all(self) -> None:
        """Trigger update across all connected UI panels."""
        if self.on_canvas_needs_repaint:
            self.on_canvas_needs_repaint()
        if self.on_layers_changed:
            self.on_layers_changed()
        if self.on_history_changed:
            self.on_history_changed()

    # ---------------------------------------------------------
    # Undo / Redo Operations
    # ---------------------------------------------------------
    def undo(self) -> bool:
        if not self.document:
            return False
        success = self.document.history_manager.undo()
        if success:
            self.document.invalidate_composite()
            self.notify_all()
        return success

    def redo(self) -> bool:
        if not self.document:
            return False
        success = self.document.history_manager.redo()
        if success:
            self.document.invalidate_composite()
            self.notify_all()
        return success

    def can_undo(self) -> bool:
        return self.document is not None and self.document.history_manager.can_undo()

    def can_redo(self) -> bool:
        return self.document is not None and self.document.history_manager.can_redo()

    # ---------------------------------------------------------
    # Layer Reversible Commands
    # ---------------------------------------------------------
    def add_new_layer(self, name: Optional[str] = None) -> Optional[Layer]:
        if not self.document:
            return None
        new_name = name or f"Layer {len(self.document.layers) + 1}"
        new_layer = Layer(new_name, self.document.width, self.document.height)
        cmd = AddLayerCommand(self.document, new_layer, len(self.document.layers))
        if self.document.history_manager.execute(cmd):
            self.notify_all()
            return new_layer
        return None

    def delete_active_layer(self) -> bool:
        if not self.document or len(self.document.layers) <= 1:
            return False
        idx = self.document.active_layer_index
        cmd = DeleteLayerCommand(self.document, idx)
        if self.document.history_manager.execute(cmd):
            self.notify_all()
            return True
        return False

    def rename_layer(self, index: int, new_name: str) -> bool:
        if not self.document or not (0 <= index < len(self.document.layers)):
            return False
        layer = self.document.layers[index]
        cmd = RenameLayerCommand(self.document, layer, new_name)
        if self.document.history_manager.execute(cmd):
            self.notify_all()
            return True
        return False

    def reorder_layer(self, from_index: int, to_index: int) -> bool:
        if not self.document:
            return False
        cmd = ReorderLayerCommand(self.document, from_index, to_index)
        if self.document.history_manager.execute(cmd):
            self.notify_all()
            return True
        return False

    def set_layer_visibility(self, index: int, visible: bool) -> bool:
        if not self.document or not (0 <= index < len(self.document.layers)):
            return False
        layer = self.document.layers[index]
        cmd = SetLayerVisibilityCommand(self.document, layer, visible)
        if self.document.history_manager.execute(cmd):
            self.notify_all()
            return True
        return False

    def set_layer_opacity(self, index: int, opacity: float) -> bool:
        if not self.document or not (0 <= index < len(self.document.layers)):
            return False
        layer = self.document.layers[index]
        cmd = SetLayerOpacityCommand(self.document, layer, opacity)
        if self.document.history_manager.execute(cmd):
            self.notify_all()
            return True
        return False

    def merge_down(self, index: int) -> bool:
        if not self.document or index <= 0 or index >= len(self.document.layers):
            return False
        cmd = MergeDownCommand(self.document, index)
        if self.document.history_manager.execute(cmd):
            self.notify_all()
            return True
        return False
