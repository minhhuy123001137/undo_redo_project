"""Document model managing multi-layer canvas, composition, and history."""
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image

from core.history_manager import HistoryManager
from apps.mini_photoshop.layers import Layer


class Document:
    """Represents an active multi-layer image editing document."""

    def __init__(
        self,
        width: int,
        height: int,
        name: str = "Untitled",
        max_history: Optional[int] = 100,
        max_memory_bytes: Optional[int] = 200 * 1024 * 1024,  # 200 MB limit
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.name: str = name
        self.file_path: Optional[str] = None
        self.is_dirty: bool = False

        # Independent HistoryManager for this document
        self.history_manager: HistoryManager = HistoryManager(
            max_history=max_history,
            max_memory_bytes=max_memory_bytes,
        )

        self.layers: List[Layer] = []
        self.active_layer_index: int = 0
        self._cached_composite: Optional[Image.Image] = None
        self._dirty_composite: bool = True

        # Create default initial background layer (white or transparent)
        bg_layer = Layer(
            name="Background",
            width=width,
            height=height,
            initial_image=Image.new("RGBA", (width, height), (255, 255, 255, 255)),
        )
        self.layers.append(bg_layer)

    @property
    def active_layer(self) -> Optional[Layer]:
        """Return the currently selected Layer."""
        if 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]
        return None

    def invalidate_composite(self) -> None:
        """Mark composite image as needing re-rendering."""
        self._dirty_composite = True
        self.is_dirty = True

    def get_composite_image(self) -> Image.Image:
        """Render and return the composite of all visible layers from bottom to top."""
        if not self._dirty_composite and self._cached_composite is not None:
            return self._cached_composite

        composite = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))

        for layer in self.layers:
            if not layer.visible or layer.opacity <= 0.0:
                continue

            img = layer.image
            if layer.opacity < 1.0:
                # Modulate alpha channel by layer opacity
                r, g, b, a = img.split()
                alpha_mod = int(layer.opacity * 255)
                a = a.point(lambda p: (p * alpha_mod) // 255)
                img = Image.merge("RGBA", (r, g, b, a))

            composite = Image.alpha_composite(composite, img)

        self._cached_composite = composite
        self._dirty_composite = False
        return composite

    # ---------------------------------------------------------
    # Layer Manipulation API
    # ---------------------------------------------------------
    def add_layer(
        self,
        name: Optional[str] = None,
        image: Optional[Image.Image] = None,
        index: Optional[int] = None,
    ) -> Layer:
        """Add a new layer at the specified index or on top."""
        layer_name = name or f"Layer {len(self.layers) + 1}"
        new_layer = Layer(layer_name, self.width, self.height, initial_image=image)

        if index is None or index < 0 or index > len(self.layers):
            self.layers.append(new_layer)
            self.active_layer_index = len(self.layers) - 1
        else:
            self.layers.insert(index, new_layer)
            self.active_layer_index = index

        self.invalidate_composite()
        return new_layer

    def remove_layer(self, index: int) -> Optional[Layer]:
        """Remove layer at index. Document must maintain at least one layer."""
        if len(self.layers) <= 1:
            return None
        if not (0 <= index < len(self.layers)):
            return None

        removed = self.layers.pop(index)
        self.active_layer_index = max(0, min(self.active_layer_index, len(self.layers) - 1))
        self.invalidate_composite()
        return removed

    def insert_layer(self, index: int, layer: Layer) -> None:
        """Insert existing layer at index (used by undo/redo)."""
        idx = max(0, min(index, len(self.layers)))
        self.layers.insert(idx, layer)
        self.active_layer_index = idx
        self.invalidate_composite()

    def reorder_layer(self, from_index: int, to_index: int) -> bool:
        """Move layer from one z-index to another."""
        if not (0 <= from_index < len(self.layers)) or not (0 <= to_index < len(self.layers)):
            return False
        if from_index == to_index:
            return True

        layer = self.layers.pop(from_index)
        self.layers.insert(to_index, layer)
        self.active_layer_index = to_index
        self.invalidate_composite()
        return True

    def duplicate_layer(self, index: int) -> Optional[Layer]:
        """Duplicate layer at index and insert it right above."""
        if not (0 <= index < len(self.layers)):
            return None
        original = self.layers[index]
        clone = original.clone()
        self.layers.insert(index + 1, clone)
        self.active_layer_index = index + 1
        self.invalidate_composite()
        return clone

    def merge_down(self, index: int) -> Optional[Layer]:
        """Merge layer at index with the layer directly underneath it."""
        if index <= 0 or index >= len(self.layers):
            return None

        upper = self.layers[index]
        lower = self.layers[index - 1]

        # Composite upper onto lower
        upper_img = upper.image
        if upper.opacity < 1.0:
            r, g, b, a = upper_img.split()
            alpha_mod = int(upper.opacity * 255)
            a = a.point(lambda p: (p * alpha_mod) // 255)
            upper_img = Image.merge("RGBA", (r, g, b, a))

        merged_img = Image.alpha_composite(lower.image, upper_img)
        lower.set_image(merged_img)

        # Remove upper layer
        self.layers.pop(index)
        self.active_layer_index = index - 1
        self.invalidate_composite()
        return lower
