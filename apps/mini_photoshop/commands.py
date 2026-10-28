"""Reversible commands for Pixel Studio implementing Command Pattern."""
import sys
from typing import Optional, Tuple
from PIL import Image

from core.command import Command
from apps.mini_photoshop.document import Document
from apps.mini_photoshop.layers import Layer


class ImagePatchCommand(Command):
    """Reversible command that modifies a localized rectangular patch of a layer.
    
    Optimizes memory by storing only the cropped bounding-box area rather than
    the full document canvas.
    """

    def __init__(
        self,
        document: Document,
        layer: Layer,
        bbox: Tuple[int, int, int, int],  # (min_x, min_y, max_x, max_y)
        before_patch: Image.Image,
        after_patch: Image.Image,
        name: str = "Paint Stroke",
    ) -> None:
        super().__init__(name=name)
        self.document = document
        self.layer_id = layer.id
        self.bbox = bbox
        self.before_patch = before_patch.copy()
        self.after_patch = after_patch.copy()

    def _find_layer(self) -> Optional[Layer]:
        for lyr in self.document.layers:
            if lyr.id == self.layer_id:
                return lyr
        return None

    def execute(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        # Paste after patch
        layer.image.paste(self.after_patch, (self.bbox[0], self.bbox[1]))
        self.document.invalidate_composite()
        return True

    def undo(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        # Restore before patch
        layer.image.paste(self.before_patch, (self.bbox[0], self.bbox[1]))
        self.document.invalidate_composite()
        return True

    def get_memory_size(self) -> int:
        w = max(1, self.bbox[2] - self.bbox[0])
        h = max(1, self.bbox[3] - self.bbox[1])
        return w * h * 4 * 2 + sys.getsizeof(self)


class MoveLayerContentCommand(Command):
    """Reversible command for translating layer contents."""

    def __init__(self, document: Document, layer: Layer, dx: int, dy: int) -> None:
        super().__init__(name="Move Layer Content")
        self.document = document
        self.layer_id = layer.id
        self.dx = dx
        self.dy = dy

    def _find_layer(self) -> Optional[Layer]:
        for lyr in self.document.layers:
            if lyr.id == self.layer_id:
                return lyr
        return None

    def _shift_image(self, img: Image.Image, offset_x: int, offset_y: int) -> Image.Image:
        shifted = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shifted.paste(img, (offset_x, offset_y))
        return shifted

    def execute(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        layer.image = self._shift_image(layer.image, self.dx, self.dy)
        self.document.invalidate_composite()
        return True

    def undo(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        layer.image = self._shift_image(layer.image, -self.dx, -self.dy)
        self.document.invalidate_composite()
        return True


class AddLayerCommand(Command):
    """Reversible command for creating and adding a new layer."""

    def __init__(self, document: Document, layer: Layer, index: int) -> None:
        super().__init__(name=f"Add Layer '{layer.name}'")
        self.document = document
        self.layer = layer
        self.index = index

    def execute(self) -> bool:
        self.document.insert_layer(self.index, self.layer)
        return True

    def undo(self) -> bool:
        self.document.remove_layer(self.index)
        return True

    def get_memory_size(self) -> int:
        return self.layer.get_memory_size()


class DeleteLayerCommand(Command):
    """Reversible command for deleting a layer."""

    def __init__(self, document: Document, index: int) -> None:
        layer = document.layers[index]
        super().__init__(name=f"Delete Layer '{layer.name}'")
        self.document = document
        self.index = index
        self.deleted_layer = layer.clone(new_name=layer.name)
        self.deleted_layer.id = layer.id

    def execute(self) -> bool:
        res = self.document.remove_layer(self.index)
        return res is not None

    def undo(self) -> bool:
        self.document.insert_layer(self.index, self.deleted_layer.clone(new_name=self.deleted_layer.name))
        return True

    def get_memory_size(self) -> int:
        return self.deleted_layer.get_memory_size()


class RenameLayerCommand(Command):
    """Reversible command for renaming a layer."""

    def __init__(self, document: Document, layer: Layer, new_name: str) -> None:
        super().__init__(name=f"Rename Layer to '{new_name}'")
        self.document = document
        self.layer_id = layer.id
        self.old_name = layer.name
        self.new_name = new_name

    def _find_layer(self) -> Optional[Layer]:
        for lyr in self.document.layers:
            if lyr.id == self.layer_id:
                return lyr
        return None

    def execute(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        layer.name = self.new_name
        self.document.is_dirty = True
        return True

    def undo(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        layer.name = self.old_name
        self.document.is_dirty = True
        return True


class ReorderLayerCommand(Command):
    """Reversible command for moving layer order in stack."""

    def __init__(self, document: Document, from_index: int, to_index: int) -> None:
        super().__init__(name=f"Reorder Layer ({from_index} -> {to_index})")
        self.document = document
        self.from_index = from_index
        self.to_index = to_index

    def execute(self) -> bool:
        return self.document.reorder_layer(self.from_index, self.to_index)

    def undo(self) -> bool:
        return self.document.reorder_layer(self.to_index, self.from_index)


class SetLayerVisibilityCommand(Command):
    """Reversible command for toggling layer visibility."""

    def __init__(self, document: Document, layer: Layer, visible: bool) -> None:
        state_str = "Show" if visible else "Hide"
        super().__init__(name=f"{state_str} Layer '{layer.name}'")
        self.document = document
        self.layer_id = layer.id
        self.old_visible = layer.visible
        self.new_visible = visible

    def _find_layer(self) -> Optional[Layer]:
        for lyr in self.document.layers:
            if lyr.id == self.layer_id:
                return lyr
        return None

    def execute(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        layer.visible = self.new_visible
        self.document.invalidate_composite()
        return True

    def undo(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        layer.visible = self.old_visible
        self.document.invalidate_composite()
        return True


class SetLayerOpacityCommand(Command):
    """Reversible command for altering layer opacity."""

    def __init__(self, document: Document, layer: Layer, new_opacity: float) -> None:
        super().__init__(name=f"Set Opacity ({int(new_opacity * 100)}%)")
        self.document = document
        self.layer_id = layer.id
        self.old_opacity = layer.opacity
        self.new_opacity = new_opacity

    def _find_layer(self) -> Optional[Layer]:
        for lyr in self.document.layers:
            if lyr.id == self.layer_id:
                return lyr
        return None

    def execute(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        layer.opacity = self.new_opacity
        self.document.invalidate_composite()
        return True

    def undo(self) -> bool:
        layer = self._find_layer()
        if layer is None:
            return False
        layer.opacity = self.old_opacity
        self.document.invalidate_composite()
        return True


class MergeDownCommand(Command):
    """Reversible command for merging a layer down onto the one below it."""

    def __init__(self, document: Document, index: int) -> None:
        super().__init__(name=f"Merge Down Layer '{document.layers[index].name}'")
        self.document = document
        self.index = index
        self.upper_layer_snapshot = document.layers[index].clone(new_name=document.layers[index].name)
        self.upper_layer_snapshot.id = document.layers[index].id
        self.lower_layer_snapshot = document.layers[index - 1].clone(new_name=document.layers[index - 1].name)
        self.lower_layer_snapshot.id = document.layers[index - 1].id

    def execute(self) -> bool:
        return self.document.merge_down(self.index) is not None

    def undo(self) -> bool:
        # Restore lower layer image
        lower = self.document.layers[self.index - 1]
        lower.set_image(self.lower_layer_snapshot.image)
        lower.name = self.lower_layer_snapshot.name
        lower.opacity = self.lower_layer_snapshot.opacity
        lower.visible = self.lower_layer_snapshot.visible

        # Re-insert upper layer
        upper = self.upper_layer_snapshot.clone(new_name=self.upper_layer_snapshot.name)
        upper.id = self.upper_layer_snapshot.id
        self.document.insert_layer(self.index, upper)
        return True
