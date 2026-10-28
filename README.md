# PYTHON UNDO/REDO LAB

## Ứng dụng 1: TIME SHIFT – Escape the Timeline

**TIME SHIFT** là một trò chơi giải đố 2D lấy cảm hứng từ Sokoban cổ điển, được phát triển trên nền tảng **Python** và **Pygame**. Trò chơi đưa người chơi vào vai một nhà du hành thời gian giải quyết các dị thường dòng thời gian bằng cách dịch chuyển các Khối Hộp Thời Gian (Chrono-Crates) vào các Cổng Mục Tiêu (Temporal Target Pads).

Dự án là ứng dụng tiêu biểu đầu tiên chứng minh kiến trúc **Undo/Redo Engine đa dụng (Dual-Stack Command Pattern)** độc lập, có thể tái sử dụng trực tiếp cho các ứng dụng khác (như ứng dụng đồ họa raster **Pixel Studio** trong tương lai).

---

## 1. KIẾN TRÚC DỰ ÁN

```text
PYTHON_UNDO_REDO/
│
├── core/                       # Bộ máy Undo/Redo Engine dùng chung
│   ├── __init__.py
│   ├── command.py              # Command abstract base class (Command Pattern)
│   ├── history_manager.py      # Dual-stack HistoryManager độc lập
│   └── exceptions.py           # Phân cấp ngoại lệ an toàn
│
├── apps/
│   ├── __init__.py
│   │
│   └── sokoban/                # Ứng dụng trò chơi TIME SHIFT
│       ├── __init__.py
│       ├── main.py             # Vòng lặp Pygame, State Machine, tương tác người dùng
│       ├── game.py             # Logic luật chơi, quản lý màn chơi, tích hợp HistoryManager
│       ├── player.py           # Thực thể nhân vật người chơi và hướng di chuyển
│       ├── level.py            # Dữ liệu màn chơi, parser JSON và BFS Solver
│       ├── commands.py         # MoveCommand với khả năng hoàn tác/phục hồi nguyên tử
│       ├── renderer.py         # Renderer 3D Cyberpunk, nội suy di chuyển, bóng đổ & hiệu ứng
│       ├── sound.py            # Bộ tổng hợp âm thanh đa dạng (Procedural Synthesizer)
│       ├── particles.py        # Động cơ hạt hiệu năng cao (Dust, Sparks, Portals, Waves)
│       ├── theme.py            # Hằng số giao diện, bảng màu Neon Cyberpunk & hàm Easing
│       ├── widgets.py          # Button tương tác (scale, glow, ripple), ToggleSwitch, Slider
│       ├── ui.py               # TimelineBar thế hệ mới & non-blocking ScreenTransition
│       ├── save_manager.py     # Quản lý lưu tiến độ JSON an toàn (Atomic File Replace)
│       └── levels/             # 10 màn chơi JSON đã xác minh bằng thuật toán BFS
│           ├── level_01.json
│           └── ...
│
├── data/
│   ├── saves/                  # Lưu trữ tiến độ người chơi (progress.json)
│   └── settings/               # Lưu trữ cấu hình trò chơi (settings.json)
│
├── tests/                      # Bộ kiểm thử tự động unittest
│   ├── test_history.py         # 16 unit tests cho Undo/Redo Engine
│   └── test_sokoban.py         # 19 unit tests theo đúng yêu cầu kiểm thử
│
├── tools/
│   └── build_and_verify_levels.py # Công cụ tạo và kiểm tra lời giải màn chơi bằng BFS
│
├── launcher.py                 # Launcher khởi động chung cho các ứng dụng
├── requirements.txt            # Danh sách thư viện phụ thuộc
├── .gitignore                  # Cấu hình bỏ qua tệp tạm
└── README.md                   # Hướng dẫn chi tiết dự án
```

### Nguyên tắc thiết kế
1. **Hoàn toàn độc lập**: Thư mục `core/` độc lập 100%, không import bất kỳ thư viện UI nào (không Pygame, PySide6, Pillow).
2. **Không dùng biến toàn cục**: Mọi trạng thái game, player và history được đóng gói an toàn trong các class đối tượng.
3. **Mỗi ứng dụng có `HistoryManager` riêng**: Khi chuyển màn chơi hoặc tải phiên làm việc mới, một `HistoryManager` độc lập được khởi tạo.
4. **An toàn nguyên tử (Atomic Execution)**: Nếu thao tác di chuyển/đẩy thùng vi phạm luật chơi (va chạm tường, đẩy 2 thùng), command trả về `False` và không ghi nhận vào Undo Stack, không làm xóa Redo Stack.

---

## 2. BỘ MÁY UNDO/REDO ENGINE (`core/`)

Engine triển khai cấu trúc dữ liệu hai Stack:
- **`undo_stack`**: Ngăn xếp chứa các lệnh đã thực thi thành công.
- **`redo_stack`**: Ngăn xếp chứa các lệnh vừa bị hoàn tác.

### Các phương thức cốt lõi của `HistoryManager`
- `execute(command: Command) -> bool`: Thực thi lệnh mới. Nếu thành công, đưa vào `undo_stack` và xóa toàn bộ `redo_stack`. Nếu thất bại, bảo toàn nguyên vẹn 2 stack.
- `undo() -> bool`: Lấy lệnh gần nhất từ `undo_stack`, gọi `command.undo()`, và chuyển sang `redo_stack`.
- `redo() -> bool`: Lấy lệnh gần nhất từ `redo_stack`, gọi lại `command.execute()`, và chuyển về `undo_stack`.
- `can_undo() -> bool` & `can_redo() -> bool`: Kiểm tra trạng thái sẵn sàng hoàn tác/phục hồi.
- `clear() -> None`: Xóa sạch lịch sử khi reset màn chơi.
- `max_history` & `max_memory_bytes`: Hỗ trợ giới hạn số lượng bước hoặc dung lượng RAM, sẵn sàng mở rộng cho ứng dụng đồ họa Mini Photoshop (Pixel Studio).

---

## 3. TRÒ CHƠI TIME SHIFT

### Bảng màu đồ họa & Phong cách (Neon Cyberpunk & Modern Pixel Art)
- **Background** `#080D1C` `(8, 13, 28)`: Màu nền vũ trụ thời gian.
- **Surface / Panel** `#121B30` `(18, 27, 48)`: Bề mặt kim loại công nghệ cao.
- **Cyan Neon** `#00E5FF` `(0, 229, 255)`: Dòng chảy thời gian, giao diện HUD, hiệu ứng tua ngược (Rewind).
- **Tím Neon** `#A855F7` `(168, 85, 247)`: Điểm nhấn công nghệ viễn tưởng, năng lượng dị thường, Redo.
- **Vàng Cam** `#F59E0B` `(245, 158, 11)`: Khối Chrono-Crate chứa tinh thể thời gian.
- **Xanh Lá** `#10B981` `(16, 185, 129)`: Cổng mục tiêu không gian (Target Pad) và trạng thái hoàn thành.
- **Text Main** `#E2E8F0` `(226, 232, 240)`: Kiểu chữ hiện đại, tương phản sắc nét.

### Tính năng Animation & Trải nghiệm thị giác nâng cao
1. **Nội suy chuyển động mượt (Smooth Interpolation)**: Nhân vật và thùng di chuyển mượt mà qua các ô với hàm easing `ease_out_quad` (120ms).
2. **Animation đẩy thùng (Squash & Stretch)**: Thùng có hiệu ứng biến dạng nén nhẹ khi bắt đầu đẩy và phục hồi khi chạm đích, kèm hiệu ứng tia lửa va chạm (contact sparks).
3. **Hiệu ứng đặc biệt khi Undo / Redo**:
   - **Undo**: Sóng thời gian Cyan quét toàn màn hình, bóng mờ (ghost trail) tua ngược của nhân vật và thùng, âm thanh hạ tần số sci-fi.
   - **Redo**: Sóng thời gian Tím neon, bóng mờ tiến bước, âm thanh tăng tần số sci-fi.
4. **Hệ thống nút bấm đa trạng thái (Universal Button Component)**: Hỗ trợ Idle, Hover (nâng thẻ, đổi màu, phát sáng), Pressed (thu nhỏ nhẹ), Click Ripple lan tỏa và âm thanh phản hồi.
5. **Hệ thống hạt (Particle System)**: Bụi phát sáng trôi nổi, vụ nổ kích hoạt mục tiêu (goal burst), pháo hoa mừng chiến thắng (victory fireworks).
6. **Âm thanh tổng hợp độc lập (Procedural Sound Synthesizer)**: Toàn bộ âm thanh bước chân, đẩy thùng, kích hoạt mục tiêu, tua ngược, hoàn tất màn chơi được tổng hợp bằng thuật toán PCM nguyên bản, không cần tải bất kỳ file MP3/WAV bên ngoài.
7. **Cài đặt & Trợ năng (Settings & Accessibility)**: Tùy chỉnh âm lượng (Slider 0-100%), bật/tắt hạt (Particles), bật/tắt rung màn hình (Screen Shake), bật/tắt hào quang (Glow Effects), và chế độ Giảm chuyển động (Reduced Motion - di chuyển tức thời).

### Bảng điều khiển

| Thao tác | Phím tắt bàn phím | Chuột |
|---|---|---|
| Di chuyển / Đẩy thùng | **W / A / S / D** hoặc **Mũi tên** | — |
| Hoàn tác (Undo) | **Ctrl + Z** | Click nút **UNDO** |
| Phục hồi (Redo) | **Ctrl + Y** hoặc **Ctrl + Shift + Z** | Click nút **REDO** |
| Chơi lại màn (Restart) | **R** | Click nút **RESTART** |
| Tạm dừng (Pause) | **ESC** | Click nút **PAUSE** |

---

## 4. HỆ THỐNG MÀN CHƠI (LEVELS)

Dự án gồm **10 màn chơi JSON** đã được kiểm tra tính hợp lệ và xác minh có ít nhất 1 lời giải hoàn chỉnh thông qua thuật toán tìm kiếm theo chiều rộng (**BFS Solver**):

- **Level 1–3 (Dễ)**: *First Shift*, *Dual Timeline*, *Corridor* — Giúp làm quen với cơ chế đẩy thùng và đảo ngược thời gian.
- **Level 4–7 (Trung bình)**: *Quantum Knot*, *Paradox Alley*, *Chrono Vault*, *Continuum Chamber* — Không gian chật hẹp, đòi hỏi lập kế hoạch thứ tự đẩy.
- **Level 8–10 (Khó)**: *Time Warp*, *Event Horizon*, *Singularity* — Nhiều thùng, câu đố hóc búa, cần tận dụng Undo/Redo để thử nghiệm dòng thời gian tối ưu.

---

## 5. HƯỚNG DẪN CÀI ĐẶT VÀ KHỞI CHẠY

### Yêu cầu môi trường
- Python 3.9 trở lên (đã kiểm thử tương thích hoàn hảo trên Windows 11).
- Pygame 2.5 trở lên.

### Cài đặt thư viện
```bash
python -m pip install -r requirements.txt
```

### Khởi chạy Launcher tổng
```bash
python launcher.py
```
*(Launcher cho phép mở ứng dụng **TIME SHIFT** trong tiến trình độc lập, đồng thời hiển thị vị trí sẵn sàng tích hợp của **PIXEL STUDIO**)*.

### Hoặc khởi chạy trực tiếp trò chơi TIME SHIFT
```bash
python -m apps.sokoban.main
```

---

## 6. KIỂM THỬ TỰ ĐỘNG (UNIT TESTS)

Dự án đi kèm bộ kiểm thử toàn diện gồm **35 unit tests** tự động, bao gồm đầy đủ **19 kịch bản bắt buộc**:

1. Di chuyển hợp lệ.
2. Va chạm tường.
3. Đẩy thùng hợp lệ.
4. Đẩy thùng bị chặn.
5. Undo một lần.
6. Undo nhiều lần.
7. Redo một lần.
8. Redo nhiều lần.
9. Undo rồi thực hiện hành động mới (xóa sạch Redo Stack).
10. Undo sau khi đẩy thùng.
11. Redo sau khi đẩy thùng.
12. Undo khi không có lịch sử.
13. Redo khi không có lịch sử.
14. Restart phải xóa lịch sử.
15. Chuyển Level phải tạo lịch sử độc lập.
16. Undo/Redo tại trạng thái chiến thắng.
17. Kiểm tra level hợp lệ.
18. Kiểm tra lưu và tải JSON.
19. Command thất bại không làm sai lịch sử.

Chạy kiểm thử bằng lệnh tiêu chuẩn:
```bash
python -m unittest discover -s tests -v
```

Kết quả:
```text
Ran 35 tests in 0.065s
OK
```
