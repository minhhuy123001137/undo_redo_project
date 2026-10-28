"""File operations for Pixel Studio: project save/load, image open, and export."""
import io
import json
import zipfile
from pathlib import Path
from typing import Optional
from PIL import Image

from apps.mini_photoshop.document import Document
from apps.mini_photoshop.layers import Layer


class FileManagerError(Exception):
    """Raised when file reading or writing fails."""
    pass


class FileManager:
    """Handles serialization of .pstudio archives and image imports/exports."""

    @staticmethod
    def save_project(document: Document, filepath: str) -> None:
        """Save multi-layer project to a .pstudio ZIP archive."""
        dest_path = Path(filepath)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        manifest = {
            "format": "PIXEL_STUDIO",
            "version": "1.0",
            "name": document.name,
            "width": document.width,
            "height": document.height,
            "layers": [],
        }

        with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i, layer in enumerate(document.layers):
                img_filename = f"layer_{i}_{layer.id}.png"
                manifest["layers"].append({
                    "id": layer.id,
                    "name": layer.name,
                    "visible": layer.visible,
                    "opacity": layer.opacity,
                    "filename": img_filename,
                })

                # Write layer PNG into zip
                buf = io.BytesIO()
                layer.image.save(buf, format="PNG")
                zf.writestr(img_filename, buf.getvalue())

            # Write manifest JSON into zip
            zf.writestr("project.json", json.dumps(manifest, indent=2))

        document.file_path = str(dest_path)
        document.is_dirty = False

    @staticmethod
    def load_project(filepath: str) -> Document:
        """Load project from a .pstudio archive."""
        src_path = Path(filepath)
        if not src_path.exists():
            raise FileManagerError(f"File not found: {filepath}")

        try:
            with zipfile.ZipFile(src_path, "r") as zf:
                if "project.json" not in zf.namelist():
                    raise FileManagerError("Invalid .pstudio file: missing project.json")

                manifest_data = zf.read("project.json").decode("utf-8")
                manifest = json.loads(manifest_data)

                width = int(manifest["width"])
                height = int(manifest["height"])
                name = manifest.get("name", "Untitled")

                # Create new document with empty layer list
                doc = Document(width, height, name=name)
                doc.layers.clear()  # Remove default background layer

                for l_data in manifest.get("layers", []):
                    fname = l_data["filename"]
                    if fname in zf.namelist():
                        layer_bytes = zf.read(fname)
                        layer_img = Image.open(io.BytesIO(layer_bytes)).convert("RGBA")
                    else:
                        layer_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

                    layer = Layer(
                        name=l_data["name"],
                        width=width,
                        height=height,
                        initial_image=layer_img,
                        layer_id=l_data["id"],
                        visible=l_data.get("visible", True),
                        opacity=float(l_data.get("opacity", 1.0)),
                    )
                    doc.layers.append(layer)

                if not doc.layers:
                    doc.add_layer("Background")

                doc.active_layer_index = len(doc.layers) - 1
                doc.file_path = str(src_path)
                doc.is_dirty = False
                doc.invalidate_composite()
                return doc

        except Exception as exc:
            raise FileManagerError(f"Failed to load project: {exc}") from exc

    @staticmethod
    def export_png(document: Document, filepath: str) -> None:
        """Export composited image as PNG."""
        composite = document.get_composite_image()
        composite.save(filepath, format="PNG")

    @staticmethod
    def export_jpeg(document: Document, filepath: str, quality: int = 95) -> None:
        """Export composited image as JPEG over white background."""
        composite = document.get_composite_image()
        # Create solid white backdrop for JPEG (since JPEG doesn't support transparency)
        rgb_image = Image.new("RGB", composite.size, (255, 255, 255))
        rgb_image.paste(composite, mask=composite.split()[3])  # Paste using alpha mask
        rgb_image.save(filepath, format="JPEG", quality=quality)

    @staticmethod
    def open_image(filepath: str) -> Document:
        """Open a standard raster image file as a new Document."""
        img = Image.open(filepath).convert("RGBA")
        name = Path(filepath).stem
        doc = Document(img.width, img.height, name=name)
        doc.layers[0].set_image(img)
        doc.layers[0].name = "Background"
        doc.file_path = filepath
        doc.is_dirty = False
        doc.invalidate_composite()
        return doc
