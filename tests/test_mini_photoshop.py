"""Comprehensive unit tests for Mini Photoshop (Pixel Studio).

Covers all 20 mandatory test cases specified in the project requirements.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from apps.mini_photoshop.document import Document
from apps.mini_photoshop.layers import Layer
from apps.mini_photoshop.editor import Editor
from apps.mini_photoshop.file_manager import FileManager
from apps.mini_photoshop.tools import BrushTool, EraserTool, FillTool
from apps.mini_photoshop.commands import (
    AddLayerCommand,
    DeleteLayerCommand,
    MoveLayerContentCommand,
    ReorderLayerCommand,
    SetLayerOpacityCommand,
)
from core.history_manager import HistoryManager


class TestMiniPhotoshop(unittest.TestCase):
    """Test suite covering 20 mandatory Mini Photoshop specifications."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.doc = Document(100, 100, name="TestDoc")
        self.editor = Editor(self.doc)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # 1. Tạo canvas
    def test_01_create_canvas(self) -> None:
        self.assertEqual(self.doc.width, 100)
        self.assertEqual(self.doc.height, 100)
        self.assertEqual(len(self.doc.layers), 1)
        self.assertEqual(self.doc.layers[0].name, "Background")
        comp = self.doc.get_composite_image()
        self.assertEqual(comp.size, (100, 100))
        self.assertEqual(comp.mode, "RGBA")

    # 2. Mở ảnh
    def test_02_open_image(self) -> None:
        sample_path = self.temp_dir / "sample.png"
        sample_img = Image.new("RGBA", (64, 48), (255, 0, 0, 255))
        sample_img.save(sample_path)

        opened_doc = FileManager.open_image(str(sample_path))
        self.assertEqual(opened_doc.width, 64)
        self.assertEqual(opened_doc.height, 48)
        self.assertEqual(len(opened_doc.layers), 1)
        self.assertEqual(opened_doc.layers[0].image.getpixel((10, 10)), (255, 0, 0, 255))

    # 3. Tạo layer
    def test_03_create_layer(self) -> None:
        self.assertEqual(len(self.doc.layers), 1)
        new_layer = self.editor.add_new_layer("Overlay")
        self.assertIsNotNone(new_layer)
        self.assertEqual(len(self.doc.layers), 2)
        self.assertEqual(self.doc.layers[1].name, "Overlay")
        self.assertTrue(self.doc.history_manager.can_undo())

    # 4. Xóa layer
    def test_04_delete_layer(self) -> None:
        self.editor.add_new_layer("Layer To Delete")
        self.assertEqual(len(self.doc.layers), 2)

        success = self.editor.delete_active_layer()
        self.assertTrue(success)
        self.assertEqual(len(self.doc.layers), 1)

        # Undo delete
        self.editor.undo()
        self.assertEqual(len(self.doc.layers), 2)
        self.assertEqual(self.doc.layers[1].name, "Layer To Delete")

    # 5. Vẽ brush
    def test_05_brush_stroke(self) -> None:
        brush = BrushTool()
        self.editor.set_primary_color((255, 100, 50, 255))
        self.editor.tool_size = 4

        # Paint stroke at (50, 50)
        brush.on_press(self.editor, 50, 50)
        brush.on_drag(self.editor, 55, 55)
        brush.on_release(self.editor, 55, 55)

        active_layer = self.doc.active_layer
        # Pixel at (50, 50) should be painted with primary color
        px = active_layer.image.getpixel((50, 50))
        self.assertEqual(px, (255, 100, 50, 255))
        self.assertTrue(self.doc.history_manager.can_undo())

    # 6. Undo brush
    def test_06_undo_brush(self) -> None:
        orig_color = self.doc.active_layer.image.getpixel((20, 20))
        brush = BrushTool()
        self.editor.set_primary_color((0, 255, 0, 255))

        brush.on_press(self.editor, 20, 20)
        brush.on_release(self.editor, 20, 20)
        self.assertEqual(self.doc.active_layer.image.getpixel((20, 20)), (0, 255, 0, 255))

        # Undo
        self.assertTrue(self.editor.undo())
        self.assertEqual(self.doc.active_layer.image.getpixel((20, 20)), orig_color)
        self.assertTrue(self.editor.can_redo())

    # 7. Redo brush
    def test_07_redo_brush(self) -> None:
        brush = BrushTool()
        self.editor.set_primary_color((0, 0, 255, 255))

        brush.on_press(self.editor, 30, 30)
        brush.on_release(self.editor, 30, 30)

        self.editor.undo()
        self.assertNotEqual(self.doc.active_layer.image.getpixel((30, 30)), (0, 0, 255, 255))

        self.assertTrue(self.editor.redo())
        self.assertEqual(self.doc.active_layer.image.getpixel((30, 30)), (0, 0, 255, 255))

    # 8. Undo nhiều nét vẽ
    def test_08_undo_multiple_strokes(self) -> None:
        brush = BrushTool()
        self.editor.tool_size = 2

        # Stroke 1
        self.editor.set_primary_color((10, 10, 10, 255))
        brush.on_press(self.editor, 10, 10)
        brush.on_release(self.editor, 10, 10)

        # Stroke 2
        self.editor.set_primary_color((20, 20, 20, 255))
        brush.on_press(self.editor, 40, 40)
        brush.on_release(self.editor, 40, 40)

        # Stroke 3
        self.editor.set_primary_color((30, 30, 30, 255))
        brush.on_press(self.editor, 70, 70)
        brush.on_release(self.editor, 70, 70)

        self.assertEqual(self.doc.history_manager.undo_count, 3)

        self.editor.undo()
        self.assertEqual(self.doc.history_manager.undo_count, 2)
        self.editor.undo()
        self.assertEqual(self.doc.history_manager.undo_count, 1)
        self.editor.undo()
        self.assertEqual(self.doc.history_manager.undo_count, 0)
        self.assertFalse(self.editor.can_undo())

    # 9. Undo rồi vẽ nét mới
    def test_09_undo_then_new_stroke_clears_redo(self) -> None:
        brush = BrushTool()
        self.editor.set_primary_color((10, 10, 10, 255))
        brush.on_press(self.editor, 10, 10)
        brush.on_release(self.editor, 10, 10)

        self.editor.undo()
        self.assertTrue(self.editor.can_redo())
        self.assertEqual(self.doc.history_manager.redo_count, 1)

        # Paint new stroke
        self.editor.set_primary_color((99, 99, 99, 255))
        brush.on_press(self.editor, 50, 50)
        brush.on_release(self.editor, 50, 50)

        # Redo stack must be completely cleared
        self.assertFalse(self.editor.can_redo())
        self.assertEqual(self.doc.history_manager.redo_count, 0)

    # 10. Eraser và Undo
    def test_10_eraser_and_undo(self) -> None:
        eraser = EraserTool()
        # Initial pixel has alpha 255
        self.assertEqual(self.doc.active_layer.image.getpixel((25, 25))[3], 255)

        eraser.on_press(self.editor, 25, 25)
        eraser.on_release(self.editor, 25, 25)

        # Erased pixel has alpha 0
        self.assertEqual(self.doc.active_layer.image.getpixel((25, 25)), (0, 0, 0, 0))

        # Undo restores alpha 255
        self.editor.undo()
        self.assertEqual(self.doc.active_layer.image.getpixel((25, 25))[3], 255)

    # 11. Fill và Undo
    def test_11_fill_and_undo(self) -> None:
        fill = FillTool()
        self.editor.set_primary_color((123, 45, 67, 255))

        fill.on_press(self.editor, 5, 5)

        # Background should be flooded with new color
        self.assertEqual(self.doc.active_layer.image.getpixel((5, 5)), (123, 45, 67, 255))
        self.assertEqual(self.doc.active_layer.image.getpixel((50, 50)), (123, 45, 67, 255))

        # Undo restores original white
        self.editor.undo()
        self.assertEqual(self.doc.active_layer.image.getpixel((5, 5)), (255, 255, 255, 255))

    # 12. Di chuyển layer và Undo
    def test_12_move_layer_content_and_undo(self) -> None:
        # Paint a spot at (10, 10)
        self.doc.active_layer.image.putpixel((10, 10), (255, 0, 0, 255))

        cmd = MoveLayerContentCommand(self.doc, self.doc.active_layer, dx=20, dy=15)
        self.doc.history_manager.execute(cmd)

        # Spot should have moved to (30, 25)
        self.assertEqual(self.doc.active_layer.image.getpixel((30, 25)), (255, 0, 0, 255))

        # Undo moves it back
        self.editor.undo()
        self.assertEqual(self.doc.active_layer.image.getpixel((10, 10)), (255, 0, 0, 255))

    # 13. Đổi opacity và Undo
    def test_13_layer_opacity_and_undo(self) -> None:
        layer = self.doc.active_layer
        self.assertEqual(layer.opacity, 1.0)

        self.editor.set_layer_opacity(0, 0.45)
        self.assertAlmostEqual(layer.opacity, 0.45)

        self.editor.undo()
        self.assertAlmostEqual(layer.opacity, 1.0)

    # 14. Reorder layer và Undo
    def test_14_reorder_layer_and_undo(self) -> None:
        self.editor.add_new_layer("Top Layer")
        self.assertEqual(self.doc.layers[0].name, "Background")
        self.assertEqual(self.doc.layers[1].name, "Top Layer")

        self.editor.reorder_layer(0, 1)
        self.assertEqual(self.doc.layers[0].name, "Top Layer")
        self.assertEqual(self.doc.layers[1].name, "Background")

        self.editor.undo()
        self.assertEqual(self.doc.layers[0].name, "Background")
        self.assertEqual(self.doc.layers[1].name, "Top Layer")

    # 15. Save Project
    def test_15_save_project(self) -> None:
        self.editor.add_new_layer("Art Layer")
        proj_path = self.temp_dir / "my_artwork.pstudio"

        FileManager.save_project(self.doc, str(proj_path))
        self.assertTrue(proj_path.exists())
        self.assertGreater(proj_path.stat().st_size, 0)

    # 16. Load Project
    def test_16_load_project(self) -> None:
        self.editor.add_new_layer("SpecialLayer")
        self.doc.layers[1].image.putpixel((5, 5), (42, 84, 126, 255))
        proj_path = self.temp_dir / "save_load_test.pstudio"
        FileManager.save_project(self.doc, str(proj_path))

        loaded = FileManager.load_project(str(proj_path))
        self.assertEqual(loaded.width, 100)
        self.assertEqual(loaded.height, 100)
        self.assertEqual(len(loaded.layers), 2)
        self.assertEqual(loaded.layers[1].name, "SpecialLayer")
        self.assertEqual(loaded.layers[1].image.getpixel((5, 5)), (42, 84, 126, 255))

    # 17. Export PNG
    def test_17_export_png(self) -> None:
        export_path = self.temp_dir / "render.png"
        FileManager.export_png(self.doc, str(export_path))
        self.assertTrue(export_path.exists())

        with Image.open(export_path) as img:
            self.assertEqual(img.size, (100, 100))
            self.assertEqual(img.format, "PNG")

    # 18. Export JPEG
    def test_18_export_jpeg(self) -> None:
        export_path = self.temp_dir / "render.jpg"
        FileManager.export_jpeg(self.doc, str(export_path))
        self.assertTrue(export_path.exists())

        with Image.open(export_path) as img:
            self.assertEqual(img.size, (100, 100))
            self.assertEqual(img.format, "JPEG")
        self.assertEqual(img.format, "JPEG")

    # 19. Hai HistoryManager hoạt động độc lập
    def test_19_independent_history_managers(self) -> None:
        doc_a = Document(50, 50, name="DocA")
        doc_b = Document(50, 50, name="DocB")

        # Check separate instances
        self.assertIsNot(doc_a.history_manager, doc_b.history_manager)

        # Action in doc_a
        cmd_a = AddLayerCommand(doc_a, Layer("LayerA", 50, 50), 1)
        doc_a.history_manager.execute(cmd_a)

        self.assertEqual(doc_a.history_manager.undo_count, 1)
        self.assertEqual(doc_b.history_manager.undo_count, 0)

        # doc_b can NOT undo
        self.assertFalse(doc_b.history_manager.can_undo())
        self.assertTrue(doc_a.history_manager.can_undo())

    # 20. Sokoban unit tests vẫn thành công
    def test_20_core_sokoban_remains_intact(self) -> None:
        # Import Sokoban and verify independence
        from apps.sokoban.game import SokobanGame
        game = SokobanGame()
        self.assertIsNotNone(game.history_manager)
        self.assertEqual(game.move_count, 0)
        self.assertFalse(game.can_undo())


if __name__ == "__main__":
    unittest.main()
