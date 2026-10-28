# PYTHON UNDO/REDO LAB

**Dự án hoàn thiện của Huy - Nhân - Cường**

Dự án mẫu mực chứng minh sức mạnh của mô hình kiến trúc **Command Pattern kết hợp Dual-Stack Undo/Redo Engine** dùng chung cho hai ứng dụng hoàn toàn độc lập:
1. **TIME SHIFT – Escape the Timeline**: Trò chơi giải đố 2D phong cách Sokoban Neon Cyberpunk (Python + Pygame).
2. **PIXEL STUDIO – Mini Photoshop**: Ứng dụng đồ họa raster đa lớp chuyên nghiệp (Python + PySide6 + Pillow).

---

## 1. TỔNG QUAN KIẾN TRÚC DỰ ÁN

```text
PYTHON_UNDO_REDO/
│
├── core/                               # BỘ MÁY UNDO/REDO ENGINE DÙNG CHUNG
│   ├── __init__.py
│   ├── command.py                      # Abstract base class Command (execute, undo, name, memory_bytes)
│   ├── history_manager.py              # Dual-Stack HistoryManager (undo_stack, redo_stack, limits)
│   └── exceptions.py                   # Phân cấp ngoại lệ an toàn
│
├── apps/
│   ├── __init__.py
│   │
│   ├── sokoban/                        # ỨNG DỤNG 1: TIME SHIFT (Pygame)
│   │   ├── __init__.py
│   │   ├── main.py                     # Game loop, State Machine, tương tác người chơi
│   │   ├── game.py                     # Logic luật chơi, quản lý màn chơi, tích hợp HistoryManager
│   │   ├── player.py                   # Nhân vật người chơi & hướng di chuyển
│   │   ├── level.py                    # Dữ liệu màn chơi, parser JSON & BFS Solver
│   │   ├── commands.py                 # MoveCommand với hoàn tác/phục hồi nguyên tử
│   │   ├── renderer.py                 # Renderer 3D Cyberpunk, nội suy di chuyển, bóng đổ & hiệu ứng
│   │   ├── sound.py                    # Bộ tổng hợp âm thanh đa dạng (Procedural Synthesizer)
│   │   ├── particles.py                # Động cơ hạt hiệu năng cao (Dust, Sparks, Portals, Waves)
│   │   ├── theme.py                    # Hằng số giao diện, bảng màu Neon Cyberpunk & hàm Easing
│   │   ├── widgets.py                  # Button tương tác (scale, glow, ripple), ToggleSwitch, Slider
│   │   ├── ui.py                       # TimelineBar & non-blocking ScreenTransition
│   │   ├── save_manager.py             # Quản lý lưu tiến độ JSON an toàn (Atomic File Replace)
│   │   └── levels/                     # 10 màn chơi JSON đã xác minh bằng thuật toán BFS
│   │       ├── level_01.json
│   │       └── ...
│   │
│   └── mini_photoshop/                 # ỨNG DỤNG 2: PIXEL STUDIO (PySide6 + Pillow)
│       ├── __init__.py
│       ├── main.py                     # Entry point khởi chạy ứng dụng GUI
│       ├── layers.py                   # Thực thể Layer (PIL Image RGBA, opacity, visibility)
│       ├── document.py                 # Quản lý canvas, danh sách layers, alpha composite, HistoryManager
│       ├── commands.py                 # Bộ lệnh Reversible: ImagePatchCommand (crop bbox), Layer commands
│       ├── tools.py                    # 10 công cụ đồ họa (Brush, Eraser, Pencil, Fill BFS, Shapes, Move, ...)
│       ├── editor.py                   # State Controller điều phối Document, Tools, Commands, Colors
│       ├── canvas.py                   # CanvasWidget tương tác zoom/pan, checkerboard, QPainter render
│       ├── file_manager.py             # Định dạng .pstudio (ZIP + manifest), import/export PNG/JPEG
│       └── ui/
│           ├── __init__.py
│           ├── main_window.py          # MainWindow chuẩn Studio, Dark QPalette (không dùng QSS)
│           ├── toolbar.py              # Thanh công cụ đứng với icon vẽ bằng QPainter
│           ├── layers_panel.py         # Dock quản lý lớp (thêm, xóa, reorder, đổi opacity, gộp lớp)
│           ├── history_panel.py        # Dock lịch sử Undo/Redo trực quan, click nhảy tới bước bất kỳ
│           └── color_picker.py         # Bảng màu swatches, bộ chọn QColorDialog, thanh kích thước cọ
│
├── data/
│   ├── saves/                          # Lưu trữ tiến độ người chơi (progress.json)
│   └── settings/                       # Lưu trữ cấu hình trò chơi (settings.json)
│
├── tests/                              # BỘ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN (55 TESTS)
│   ├── test_history.py                 # 16 unit tests cho Undo/Redo Engine cốt lõi
│   ├── test_sokoban.py                 # 19 unit tests cho luật chơi Sokoban và Undo/Redo
│   └── test_mini_photoshop.py          # 20 unit tests cho đồ họa, layer, patch memory và file I/O
│
├── tools/
│   └── build_and_verify_levels.py      # Công cụ sinh và xác minh 10 màn chơi bằng BFS Solver
│
├── launcher.py                         # Hub Launcher Cyberpunk khởi động độc lập cả 2 ứng dụng
├── run_launcher.bat                    # Script click đúp chạy Launcher trên Windows
├── run_sokoban.bat                     # Script click đúp chạy TIME SHIFT
├── run_pixel_studio.bat                # Script click đúp chạy PIXEL STUDIO
├── requirements.txt                    # Thư viện phụ thuộc (pygame, Pillow, PySide6-Essentials)
└── README.md                           # Tài liệu hướng dẫn toàn diện
```

### 3 Nguyên Tắc Thiết Kế Cốt Lõi
1. **Core Độc Lập 100%**: Thư mục `core/` không phụ thuộc vào bất kỳ framework GUI nào (không Pygame, không Qt, không Pillow).
2. **Quản Lý Bộ Nhớ Tối Ưu (Bounding-Box Patch Optimization)**: Trong Pixel Studio, mỗi nét vẽ hay tẩy xóa không lưu toàn bộ bức ảnh canvas 4K; hệ thống chỉ cắt vùng chữ nhật thay đổi (`bounding box crop patch`) lưu vào `ImagePatchCommand`, giảm 90-98% RAM tiêu thụ.
3. **Tiến Trình Độc Lập**: Khởi chạy từ Launcher bằng `subprocess.Popen([sys.executable, "-m", ...])`, hai ứng dụng không chia sẻ biến toàn cục hay làm nghẽn event loop của nhau.

---

## 2. BỘ MÁY UNDO/REDO ENGINE DÙNG CHUNG (`core/`)

Triển khai kiến trúc **Command Pattern** kết hợp cấu trúc dữ liệu **Hai Ngăn Xếp (Dual-Stack)**:

```
[ THAO TÁC MỚI ] ──> execute() ──> [ UNDO STACK ] (Lưu trữ các lệnh đã chạy)
                                         │       ▲
                                  undo() │       │ redo()
                                         ▼       │
                                    [ REDO STACK ] (Lưu trữ các lệnh bị hoàn tác)
```

- **Nguyên tử (Atomic Integrity)**: Thao tác thất bại sẽ trả về `False` và không làm hỏng cả hai ngăn xếp.
- **Giới hạn an toàn**: Hỗ trợ `max_history` (số bước tối đa) và `max_memory_bytes` (tự động giải phóng các lệnh cũ nhất khi đầy RAM).

---

## 3. ỨNG DỤNG 1: TIME SHIFT – SOKOBAN GAME

Trò chơi giải đố 2D phong cách **Neon Cyberpunk** lấy cảm hứng từ Sokoban:
- **10 màn chơi** độc đáo đã được chứng minh lời giải bằng thuật toán tìm đường **BFS (Breadth-First Search)**.
- **Hiệu ứng đồ họa**: Đèn neon phát sáng (Glow), bóng mờ tua ngược (Ghost Rewind Trail), sóng thời gian khi Undo/Redo, tia lửa va chạm (Sparks), và hiệu ứng biến dạng nén đẩy thùng (Squash & Stretch).
- **Âm thanh tổng hợp (Procedural Sound Synthesizer)**: Tạo âm thanh trực tiếp bằng thuật toán PCM nguyên bản, không cần nạp tệp audio ngoài.

### Điều khiển TIME SHIFT
| Thao tác | Phím tắt bàn phím | Chuột |
|---|---|---|
| Di chuyển / Đẩy thùng | **W / A / S / D** hoặc **Mũi tên** | — |
| Hoàn tác (Undo) | **Ctrl + Z** | Click nút **UNDO** |
| Phục hồi (Redo) | **Ctrl + Y** hoặc **Ctrl + Shift + Z** | Click nút **REDO** |
| Chơi lại màn (Restart) | **R** | Click nút **RESTART** |
| Tạm dừng (Pause) | **ESC** | Click nút **PAUSE** |

---

## 4. ỨNG DỤNG 2: PIXEL STUDIO – MINI PHOTOSHOP

Ứng dụng chỉnh sửa đồ họa raster máy tính chuyên nghiệp, xây dựng bằng **PySide6** và **Pillow**.

### Đặc điểm thiết kế & Tính năng
- **Giao diện Modern Dark Studio**: Thiết kế hoàn toàn qua `QPalette`, `QFont` và `QPainter` (tuân thủ nghiêm ngặt ràng buộc **không sử dụng CSS/QSS**).
- **10 Công cụ vẽ chuyên sâu**:
  1. `Brush` (Cọ vẽ tròn mịn với bán kính tùy chỉnh)
  2. `Eraser` (Tẩy xóa vùng vẽ về trong suốt)
  3. `Pencil` (Bút chì 1px vẽ pixel art chuẩn xác)
  4. `Fill` (Tô màu vùng khép kín bằng thuật toán lan truyền BFS Flood-Fill với Tolerance)
  5. `Rectangle` (Vẽ hình chữ nhật viền)
  6. `Filled Rectangle` (Vẽ hình chữ nhật đặc)
  7. `Ellipse` (Vẽ hình tròn/elip)
  8. `Move` (Dịch chuyển nội dung layer)
  9. `Eyedropper` (Hút màu pixel từ canvas)
  10. `Hand` (Kéo rê canvas) & `Zoom` (Phóng to/thu nhỏ)
- **Quản lý đa tầng (Multi-layer Engine)**:
  - Thêm, nhân bản, xóa layer.
  - Ẩn/hiện layer (mắt toggler).
  - Điều chỉnh độ mờ đục (Opacity slider 0% – 100%).
  - Đổi thứ tự layer (Move Up / Move Down).
  - Gộp layer xuống dưới (Merge Down).
  - Alpha compositing thời gian thực.
- **Bảng điều khiển lịch sử trực quan (History Panel)**:
  - Hiển thị danh sách toàn bộ các thao tác trong Undo/Redo stack.
  - Cho phép người dùng click trực tiếp vào một bước trong quá khứ để tự động tua ngược hoặc phục hồi tới bước đó.
- **Định dạng dự án chuyên dụng (`.pstudio`)**:
  - Đóng gói định dạng ZIP chứa `project.json` (metadata kích thước, danh sách layers, opacity, visibility) và từng layer được lưu dưới dạng PNG nguyên gốc không nén suy hao.
  - Xuất ảnh chuẩn **PNG (giữ kênh alpha trong suốt)** và **JPEG (nền trắng chất lượng 95%)**.

### Phím tắt PIXEL STUDIO
| Thao tác | Phím tắt bàn phím |
|---|---|
| Tạo file mới | **Ctrl + N** |
| Mở ảnh / Dự án | **Ctrl + O** |
| Lưu dự án (`.pstudio`) | **Ctrl + S** |
| Xuất ảnh PNG | **Ctrl + Shift + E** |
| Xuất ảnh JPEG | **Ctrl + Shift + J** |
| Hoàn tác (Undo) | **Ctrl + Z** |
| Phục hồi (Redo) | **Ctrl + Y** hoặc **Ctrl + Shift + Z** |
| Thêm layer mới | **Ctrl + Shift + N** |
| Xóa layer hiện tại | **Delete** |
| Phóng to Canvas | **Ctrl + Plus** hoặc cuộn chuột lên |
| Thu nhỏ Canvas | **Ctrl + Minus** hoặc cuộn chuột xuống |
| Đặt lại kích thước (100%) | **Ctrl + 0** |
| Chọn công cụ nhanh | **B** (Brush), **E** (Eraser), **P** (Pencil), **G** (Fill), **U** (Rectangle), **V** (Move), **I** (Eyedropper), **H** (Hand), **Z** (Zoom) |

---

## 5. HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY ỨNG DỤNG

### 1. Cài đặt thư viện
Yêu cầu Python 3.9+ trên Windows. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

### 2. Khởi chạy bằng Click đúp (Khuyên dùng trên Windows)
- Chạy Hub Launcher tổng: Click đúp vào `run_launcher.bat`
- Chạy thẳng game TIME SHIFT: Click đúp vào `run_sokoban.bat`
- Chạy thẳng Mini Photoshop: Click đúp vào `run_pixel_studio.bat`

### 3. Khởi chạy bằng dòng lệnh
- Mở Hub Launcher:
  ```bash
  python launcher.py
  ```
- Mở trực tiếp TIME SHIFT:
  ```bash
  python -m apps.sokoban.main
  ```
- Mở trực tiếp PIXEL STUDIO:
  ```bash
  python -m apps.mini_photoshop.main
  ```

---

## 6. KIỂM THỬ TỰ ĐỘNG (UNIT TESTS)

Dự án bao gồm **55 bài kiểm thử tự động toàn diện** kiểm tra 100% tính nguyên vẹn của:
1. `test_history.py` (16 tests): Kiểm tra 2 stack, logic Undo/Redo, dọn dẹp redo khi có thao tác mới, giới hạn bộ nhớ và tính bất biến khi lệnh thất bại.
2. `test_sokoban.py` (19 tests): Kiểm tra di chuyển, va chạm, đẩy thùng, giải đố, phục hồi trạng thái chiến thắng và tính toàn vẹn của Sokoban.
3. `test_mini_photoshop.py` (20 tests): Kiểm tra tạo canvas, mở ảnh, thao tác layer, nét cọ, tẩy, fill BFS, di chuyển layer, bounding-box crop undo/redo, lưu/nạp file `.pstudio`, xuất PNG/JPEG và chứng minh 2 HistoryManager hoàn toàn độc lập.

Chạy toàn bộ test suite:
```bash
python -m unittest discover -s tests -v
```

Kết quả:
```text
Ran 55 tests in 0.115s
OK
```
