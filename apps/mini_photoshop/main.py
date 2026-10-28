"""Main application entry point for PIXEL STUDIO – Mini Photoshop."""
import sys
from PySide6.QtWidgets import QApplication
from apps.mini_photoshop.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("PIXEL STUDIO")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
