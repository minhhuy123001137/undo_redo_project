"""Layer data structure for Pixel Studio."""
import uuid
from typing import Optional, Tuple
from PIL import Image


class Layer:
    """Represents a single raster RGBA layer in a multi-layer document."""

    def __init__(
        self,
        name: str,
        width: int,
        height: int,
        initial_image: Optional[Image.Image] = None,
        layer_id: Optional[str] = None,
        visible: bool = True,
        opacity: float = 1.0,
    ) -> None:
        self.id: str = layer_id or str(uuid.uuid4())
        self.name: str = name
        self.width: int = width
        self.height: int = height
        self.visible: bool = visible
        self.opacity: float = max(0.0, min(1.0, float(opacity)))

        if initial_image is not None:
            if initial_image.mode != "RGBA":
                self.image: Image.Image = initial_image.convert("RGBA")
            else:
                self.image = initial_image.copy()
            if self.image.size != (width, height):
                self.image = self.image.resize((width, height), Image.Resampling.NEAREST)
        else:
            self.image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    def clone(self, new_name: Optional[str] = None) -> "Layer":
        """Create a deep clone of this layer."""
        return Layer(
            name=new_name or f"{self.name} Copy",
            width=self.width,
            height=self.height,
            initial_image=self.image.copy(),
            visible=self.visible,
            opacity=self.opacity,
        )

    def get_memory_size(self) -> int:
        """Estimate memory consumption of layer image in bytes."""
        return self.width * self.height * 4

    def copy_image(self) -> Image.Image:
        """Return a copy of the layer image."""
        return self.image.copy()

    def set_image(self, img: Image.Image) -> None:
        """Set layer image."""
        if img.mode != "RGBA":
            self.image = img.convert("RGBA")
        else:
            self.image = img.copy()

    def __repr__(self) -> str:
        return f"<Layer id={self.id[:8]} name={self.name!r} visible={self.visible} opacity={self.opacity:.2f}>"
