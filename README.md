# Chess Solver — Alpha-Beta Pruning Bot

Phần này implement thuật toán **Alpha-Beta Pruning** để xây dựng bot chơi cờ vua, là một trong hai thuật toán AI của project (cùng với MCTS).

---

## Mục lục

- [Tổng quan thuật toán](#tổng-quan-thuật-toán)
- [Kiến trúc code](#kiến-trúc-code)
- [Các kỹ thuật tối ưu](#các-kỹ-thuật-tối-ưu)
- [Hàm đánh giá](#hàm-đánh-giá)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Cách chạy](#cách-chạy)
- [Thống kê hiệu năng](#thống-kê-hiệu-năng)

---

## Tổng quan thuật toán

### Minimax

Minimax là nền tảng của Alpha-Beta. Thuật toán giả định cả hai bên đều chơi tối ưu:

- **MAX** (bot) luôn chọn nước đi có điểm cao nhất
- **MIN** (đối thủ) luôn chọn nước đi có điểm thấp nhất

Cây tìm kiếm được duyệt đến độ sâu `d`, mỗi nút lá được chấm điểm bằng hàm đánh giá tĩnh.

```
        MAX          [chọn max]
       /   \
     MIN   MIN       [chọn min]
    / \   / \
   3   5 2   9       [lá — evaluate()]

→ MIN trái = 3, MIN phải = 2
→ MAX chọn 3
```

### Alpha-Beta Pruning

Alpha-Beta giữ nguyên kết quả của Minimax nhưng **cắt bỏ các nhánh không thể ảnh hưởng đến kết quả**, giúp giảm số node cần duyệt đáng kể.

Hai tham số quan trọng:

| Tham số | Ý nghĩa | Khởi tạo |
|---------|---------|----------|
| `α` (alpha) | Điểm tốt nhất MAX đã tìm được | −∞ |
| `β` (beta)  | Điểm tốt nhất MIN đã tìm được | +∞ |

**Điều kiện cắt:** Khi `α ≥ β`, các nhánh còn lại không thể thay đổi kết quả → bỏ qua.

```
Alpha cut (cắt tại node MIN):
  Nếu node MIN tìm được giá trị ≤ α của cha (MAX)
  → MAX đã có lựa chọn tốt hơn → cắt

Beta cut (cắt tại node MAX):
  Nếu node MAX tìm được giá trị ≥ β của cha (MIN)
  → MIN sẽ không bao giờ chọn nhánh này → cắt
```

**Pseudo-code:**

```python
def alpha_beta(node, depth, α, β, maximizing):
    if depth == 0 or game_over:
        return evaluate(node)

    if maximizing:
        best = -∞
        for child in node.children:
            val  = alpha_beta(child, depth-1, α, β, False)
            best = max(best, val)
            α    = max(α, best)
            if α >= β:
                break          # Beta cut-off
        return best
    else:
        best = +∞
        for child in node.children:
            val  = alpha_beta(child, depth-1, α, β, True)
            best = min(best, val)
            β    = min(β, best)
            if α >= β:
                break          # Alpha cut-off
        return best
```

---

## Kiến trúc code

```
Algo/
├── algo.py          # Base class Algorithm
├── alphabeta.py     # Alpha-Beta bot
└── mcts.py          # MCTS bot 
```

### Sơ đồ luồng xử lý

```
get_best_move()
    │
    ├─ Iterative Deepening: depth = 1, 2, ..., N (hoặc đến hết time_limit)
    │       │
    │       ├─ _order_moves()       ← sắp xếp nước đi (MVV-LVA + hint)
    │       │
    │       └─ _alpha_beta()        ← đệ quy chính
    │               │
    │               ├─ Tra Transposition Table  → cache hit → trả về ngay
    │               ├─ depth == 0              → evaluate() → trả về điểm
    │               ├─ MAX node: duyệt, cập nhật α, beta cut nếu α≥β
    │               ├─ MIN node: duyệt, cập nhật β, alpha cut nếu α≥β
    │               └─ Lưu kết quả vào Transposition Table
    │
    └─ Trả về ((from_y, from_x), (to_y, to_x))
```

---

## Các kỹ thuật tối ưu

### 1. Move Ordering — MVV-LVA

Sắp xếp nước đi trước khi duyệt giúp alpha-beta cắt nhiều hơn. Ưu tiên theo thứ tự:

1. **Nước tốt nhất từ iteration trước** (hint) — điểm thưởng 20,000
2. **Bắt quân giá trị cao bằng quân giá trị thấp** — MVV-LVA (Most Valuable Victim – Least Valuable Attacker)
3. Nước đi thông thường

```python
score = 10 * PIECE_VALUES[captured] - PIECE_VALUES[attacker]
# Ví dụ: Tốt bắt Hậu = 10*900 - 100 = 8900  (ưu tiên cao)
#         Hậu bắt Tốt = 10*100 - 900 = 100   (ưu tiên thấp)
```

### 2. Iterative Deepening

Thay vì nhảy thẳng vào `depth = N`, thuật toán duyệt lần lượt `depth = 1, 2, ..., N`:

```
Iteration 1: depth=1 → tìm được move_A
Iteration 2: depth=2 → duyệt move_A trước (hint) → cắt nhiều hơn → tìm được move_B
Iteration 3: depth=3 → duyệt move_B trước → ...
```

**Lợi ích:** Kết quả depth trước cải thiện move ordering cho depth sau → alpha-beta cắt nhiều hơn → tổng thời gian thực ra *ít hơn* so với nhảy thẳng vào depth=N.

Khi bật `time_limit`, vòng lặp dừng khi hết giờ và trả về kết quả của iteration hoàn chỉnh gần nhất — đảm bảo luôn có nước đi hợp lệ.

### 3. Transposition Table

Dictionary lưu kết quả các vị trí đã tính, tránh tính lại khi cùng một vị trí xuất hiện qua nhiều đường đi khác nhau (rất phổ biến trong cờ vua).

```python
# Cấu trúc mỗi entry:
{
    "depth": int,       # depth đã tính
    "score": int,       # điểm kết quả
    "flag":  TT_EXACT   # EXACT / LOWER / UPPER (alpha-beta window)
           | TT_LOWER
           | TT_UPPER,
    "move":  tuple      # nước đi tốt nhất từ vị trí này
}
```

TT tồn tại **xuyên suốt cả ván cờ** (không reset sau mỗi nước), nên các nước đi sau tái sử dụng được cache của nước trước.

### 4. Luật chống lặp (3-fold repetition)

Mỗi vị trí bàn cờ được hash thành key và đếm số lần xuất hiện. Khi một vị trí xuất hiện lần thứ 3 → hòa.

- Bot tự động loại bỏ các nước dẫn đến lặp lần 3 khỏi danh sách tìm kiếm
- Người chơi cũng không thể chọn các nước đó (chấm gợi ý không hiện)

---

## Hàm đánh giá

Hàm `evaluate()` trả về điểm số đại diện cho lợi thế của bàn cờ:
- **Dương** = có lợi cho quân Trắng (team 0)
- **Âm** = có lợi cho quân Đen (team 1)
- Đơn vị: **centipawns** (100 = 1 con tốt)

### Thành phần điểm

#### Material (giá trị vật chất)

| Quân | Điểm |
|------|------|
| Tốt (Pawn) | 100 |
| Mã (Knight) | 320 |
| Tượng (Bishop) | 330 |
| Xe (Rook) | 500 |
| Hậu (Queen) | 900 |
| Vua (King) | 20,000 |

#### Piece-Square Tables (PST)

Mỗi quân có một bảng 8×8 thưởng/phạt điểm theo vị trí trên bàn cờ. Ví dụ với Tốt:

```
Hàng 7 (phong cấp): +50  ← thưởng cao khi tiến sâu
Hàng 5-6 (trung tâm): +10 đến +30
Hàng 2 (vị trí ban đầu): 0
```

Vua có 2 bảng khác nhau cho **mid-game** (ẩn nấp góc) và **endgame** (tiến ra trung tâm).

#### Nhận biết tàn cuộc

```python
def _is_endgame(board):
    # Tàn cuộc khi: không còn hậu, hoặc còn ≤2 hậu và ≤4 quân mạnh
    return queens == 0 or (queens <= 2 and minors <= 4)
```

---

## Cấu trúc thư mục

```
chess-solver/
├── Pieces/                  # Hình ảnh quân cờ và bàn cờ
├── Algo/
│   ├── __init__.py
│   ├── algo.py              # Base class
│   ├── alphabeta.py         # Alpha-Beta bot
│   └── mcts.py              # MCTS bot
├── classes.py               # Board, Piece, và các quân cờ
└── main.py                  # Game loop + menu pygame
```

---

## Cách chạy

### Yêu cầu

```bash
pip install pygame
```

### Chạy game

```bash
python main.py
```

### Menu chọn chế độ

Khi khởi động sẽ hiện màn hình menu:

```
┌─────────────────────────────────┐
│       ♟  Chess AI  ♟            │
│    Alpha-Beta Pruning Bot       │
│                                 │
│  ♔  Trắng vs Bot                │  ← bạn đánh trắng
│  ♚  Đen vs Bot                  │  ← bạn đánh đen
│  ⚙  Bot vs Bot                  │  ← xem AI tự đánh
│                                 │
│  [ Dễ ]  [ Bình thường ]  [ Khó ]│
│                                 │
│         [ ▶ BẮT ĐẦU ]          │
└─────────────────────────────────┘
```

| Độ khó | Cơ chế | Thời gian/nước |
|--------|--------|---------------|
| Dễ | depth = 2 (cố định) | ~0.1–0.5s |
| Bình thường | depth = 3 (cố định) | ~0.5–3s |
| Khó | Iterative Deepening + time limit 5s | ~5s |

### Phím tắt trong game

| Phím | Chức năng |
|------|-----------|
| `ENTER` | Về menu chính |
| `R` | Chơi lại cùng cài đặt |

---

## Thống kê hiệu năng

Log được in ra terminal sau mỗi nước đi của bot:

```
[AlphaBeta/BLACK] depth=4/99 | nodes=34,300 | pruned=3,894 | tt_hits=1,520 | tt_size=74,051 | time=5.636s | score=690
```

| Field | Ý nghĩa |
|-------|---------|
| `depth=4/99` | Duyệt được đến depth 4 trong time limit (99 = không giới hạn) |
| `nodes` | Tổng số node đã duyệt |
| `pruned` | Số lần cắt nhánh thành công |
| `tt_hits` | Số lần tra Transposition Table thành công (tránh tính lại) |
| `tt_size` | Tổng số entry đang lưu trong TT |
| `time` | Thời gian tính nước (giây) |
| `score` | Điểm đánh giá bàn cờ hiện tại (centipawns) |

### Ví dụ từ một ván thực tế (Bot vs Bot — Khó)

| Giai đoạn | Depth đạt được | Nodes | TT hits | Thời gian |
|-----------|---------------|-------|---------|-----------|
| Khai cuộc | 3–4 | ~30,000–50,000 | ~1,000–2,000 | ~5–8s |
| Trung cuộc | 3–4 | ~10,000–25,000 | ~500–1,500 | ~5s |
| Tàn cuộc | 9–13 | ~35,000–65,000 | ~10,000–30,000 | ~5–7s |

Tàn cuộc duyệt được depth cao hơn vì ít quân → ít nhánh → trong 5s tìm được sâu hơn. TT hits tăng mạnh về cuối ván vì cache tích lũy từ đầu ván.

---

## So sánh với MCTS

| Tiêu chí | Alpha-Beta | MCTS |
|----------|-----------|------|
| Phương pháp | Tìm kiếm cây tất định | Simulation ngẫu nhiên |
| Độ chính xác | Chính xác trong tầm nhìn | Ước lượng xác suất |
| Tầm nhìn | Giới hạn bởi depth | Không giới hạn depth |
| Mạnh ở | Tactical (tính toán cụ thể) | Strategic (chiến lược dài hạn) |
| Tốc độ | Nhanh ở depth thấp | Cần nhiều simulation |
| Điểm mạnh | Không bỏ sót nước trong tầm nhìn | Phát hiện được hy sinh quân dài hạn |