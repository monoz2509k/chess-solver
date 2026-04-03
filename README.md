# Chess Solver — Alpha-Beta & MCTS Bot

Project implement hai thuật toán AI để xây dựng bot chơi cờ vua: **Alpha-Beta Pruning** và **Monte Carlo Tree Search (MCTS)**.

---

## Mục lục

- [Tổng quan thuật toán](#tổng-quan-thuật-toán)
  - [Alpha-Beta Pruning](#alpha-beta-pruning)
  - [Monte Carlo Tree Search (MCTS)](#monte-carlo-tree-search-mcts)
- [Kiến trúc code](#kiến-trúc-code)
- [Các kỹ thuật tối ưu](#các-kỹ-thuật-tối-ưu)
- [Hàm đánh giá](#hàm-đánh-giá)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Cách chạy](#cách-chạy)
- [Thống kê hiệu năng](#thống-kê-hiệu-năng)
- [So sánh Alpha-Beta vs MCTS](#so-sánh-alpha-beta-vs-mcts)

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

### Monte Carlo Tree Search (MCTS)

MCTS là thuật toán tìm kiếm dựa trên **mô phỏng ngẫu nhiên** (simulation). Thay vì đánh giá trực tiếp các vị trí, MCTS chơi ngẫu nhiên hàng trăm/hàng nghìn ván và dùng thống kê để chọn nước đi tốt nhất.

#### 4 bước của MCTS

```
        get_best_move()
            │
            ├─ Lặp N iterations (hoặc đến hết time_limit)
            │       │
            │       ├─ 1. SELECTION    ← duyệt cây bằng UCT
            │       ├─ 2. EXPANSION    ← mở rộng node chưa khám phá
            │       ├─ 3. SIMULATION   ← rollout ngẫu nhiên + heuristic
            │       └─ 4. BACKPROPAGATION ← cập nhật thống kê ngược lên gốc
            │
            └─ Chọn child có nhiều visits nhất (robust child)
```

**Bước 1 — Selection:** Từ gốc, chọn child theo công thức **UCT (Upper Confidence Bound for Trees)**:

```
UCT(i) = wi/ni + C × √(ln(N) / ni)
```

| Biến | Ý nghĩa |
|------|---------|
| `wi` | Số lần thắng của node i |
| `ni` | Số lần visit node i |
| `N`  | Số lần visit node cha |
| `C`  | Hằng số exploration (√2 ≈ 1.414) |

Công thức cân bằng giữa **exploitation** (chọn nước đã biết tốt) và **exploration** (thử nước chưa khám phá).

**Bước 2 — Expansion:** Khi gặp node có nước chưa thử, tạo child node mới cho 1 nước ngẫu nhiên.

**Bước 3 — Simulation (Rollout):** Từ node mới, chơi ngẫu nhiên tối đa **20 nước** rồi đánh giá bằng hàm heuristic `evaluate()`. Dùng rollout giới hạn + heuristic thay vì chơi đến kết thúc vì ván cờ vua quá dài (100+ nước random sẽ cho kết quả vô nghĩa).

**Bước 4 — Backpropagation:** Cập nhật số liệu thắng/thua ngược lên gốc:
- Thắng → wins += 1
- Hòa → wins += 0.5
- Thua → wins += 0

**Pseudo-code:**

```python
def mcts(root_state, iterations):
    root = MCTSNode(state=root_state)

    for i in range(iterations):
        node = root
        state = copy(root_state)

        # 1. Selection
        while node.fully_expanded and node.has_children:
            node = node.best_child_by_uct()
            state.apply(node.move)

        # 2. Expansion
        if node.has_untried_moves:
            move = random.choice(node.untried_moves)
            state.apply(move)
            node = node.add_child(move, state)

        # 3. Simulation (Rollout)
        for depth in range(20):
            moves = state.legal_moves()
            if not moves: break
            state.apply(random.choice(moves))
        score = evaluate(state)

        # 4. Backpropagation
        while node is not None:
            node.visits += 1
            node.wins += result(score)
            node = node.parent

    # Chọn nước đi có nhiều visits nhất
    return max(root.children, key=lambda c: c.visits).move
```

---

## Kiến trúc code

```
algo/
├── algo.py          # Base class Algorithm
├── alphabeta.py     # Alpha-Beta bot
└── mcts.py          # MCTS bot
```

### Sơ đồ luồng xử lý — Alpha-Beta

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

### Sơ đồ luồng xử lý — MCTS

```
get_best_move()
    │
    ├─ Lặp N iterations
    │       │
    │       ├─ Lưu trạng thái bàn cờ
    │       ├─ Selection:  duyệt cây theo UCT  (wi/ni + C√(ln N/ni))
    │       ├─ Expansion:  thêm child cho nước chưa thử
    │       ├─ Simulation: deep-copy quân cờ → rollout 20 nước → evaluate()
    │       ├─ Backpropagation: cập nhật wins/visits ngược lên gốc
    │       └─ Khôi phục trạng thái bàn cờ
    │
    └─ Chọn child có visits cao nhất → trả về move
```

---

## Các kỹ thuật tối ưu

### Alpha-Beta: Move Ordering — MVV-LVA

Sắp xếp nước đi trước khi duyệt giúp alpha-beta cắt nhiều hơn:

1. **Nước tốt nhất từ iteration trước** (hint) — điểm thưởng 20,000
2. **Bắt quân giá trị cao bằng quân giá trị thấp** — MVV-LVA
3. Nước đi thông thường

```python
score = 10 * PIECE_VALUES[captured] - PIECE_VALUES[attacker]
# Ví dụ: Tốt bắt Hậu = 10*900 - 100 = 8900  (ưu tiên cao)
#         Hậu bắt Tốt = 10*100 - 900 = 100   (ưu tiên thấp)
```

### Alpha-Beta: Iterative Deepening

Thay vì nhảy thẳng vào `depth = N`, thuật toán duyệt lần lượt `depth = 1, 2, ..., N`:

```
Iteration 1: depth=1 → tìm được move_A
Iteration 2: depth=2 → duyệt move_A trước (hint) → cắt nhiều hơn → tìm được move_B
Iteration 3: depth=3 → duyệt move_B trước → ...
```

Khi bật `time_limit`, vòng lặp dừng khi hết giờ và trả về kết quả của iteration hoàn chỉnh gần nhất.

### Alpha-Beta: Transposition Table

Dictionary lưu kết quả các vị trí đã tính, tránh tính lại khi cùng một vị trí xuất hiện qua nhiều đường đi khác nhau.

```python
{
    "depth": int,       # depth đã tính
    "score": int,       # điểm kết quả
    "flag":  TT_EXACT | TT_LOWER | TT_UPPER,
    "move":  tuple      # nước đi tốt nhất từ vị trí này
}
```

TT tồn tại xuyên suốt cả ván cờ, nên các nước đi sau tái sử dụng được cache của nước trước.

### MCTS: UCT Exploration

Hằng số exploration `C = √2` cân bằng giữa khai thác (exploitation) và khám phá (exploration). Node chưa thử nhiều sẽ có thành phần exploration cao → được ưu tiên thăm.

### MCTS: Limited-Depth Rollout + Heuristic

Thay vì chơi random đến khi ván cờ kết thúc (có thể hàng trăm nước), rollout giới hạn ở **20 nước random** rồi đánh giá bằng hàm heuristic `evaluate()`. Đây là kỹ thuật phổ biến cho MCTS trong cờ vua, vì random rollout đến tận cùng sẽ cho kết quả rất nhiễu (noisy).

### Luật chống lặp (3-fold repetition)

Mỗi vị trí bàn cờ được hash thành key và đếm số lần xuất hiện. Khi một vị trí xuất hiện lần thứ 3 → hòa. Bot và người chơi đều không thể chọn nước dẫn đến lặp lần 3.

---

## Hàm đánh giá

Hàm `evaluate()` trả về điểm số (centipawns — 100 = 1 con tốt):
- **Dương** = có lợi cho quân Trắng (team 0)
- **Âm** = có lợi cho quân Đen (team 1)

Cả Alpha-Beta và MCTS đều dùng chung hàm đánh giá này.

### Material (giá trị vật chất)

| Quân | Điểm |
|------|------|
| Tốt (Pawn) | 100 |
| Mã (Knight) | 320 |
| Tượng (Bishop) | 330 |
| Xe (Rook) | 500 |
| Hậu (Queen) | 900 |
| Vua (King) | 20,000 |

### Piece-Square Tables (PST)

Mỗi quân có một bảng 8×8 thưởng/phạt điểm theo vị trí trên bàn cờ. Ví dụ với Tốt:

```
Hàng 7 (phong cấp): +50  ← thưởng cao khi tiến sâu
Hàng 5-6 (trung tâm): +10 đến +30
Hàng 2 (vị trí ban đầu): 0
```

Vua có 2 bảng khác nhau cho **mid-game** (ẩn nấp góc) và **endgame** (tiến ra trung tâm).

---

## Cấu trúc thư mục

```
chess-solver/
├── Pieces/                  # Hình ảnh quân cờ và bàn cờ
├── Material/                # Tài liệu tham khảo & bài tập
├── algo/
│   ├── __init__.py
│   ├── algo.py              # Base class Algorithm
│   ├── alphabeta.py         # Alpha-Beta bot
│   └── mcts.py              # MCTS bot
├── classes.py               # Board, Piece, và các quân cờ
├── main.py                  # Game loop + menu pygame
└── README.md
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
┌─────────────────────────────────────┐
│         ♟  Chess AI  ♟              │
│       Alpha-Beta & MCTS Bot         │
│                                     │
│  ── CHỌN CHẾ ĐỘ CHƠI ──           │
│  ♔  Trắng vs Bot                    │
│  ♚  Đen vs Bot                      │
│  ⚙  Bot vs Bot                      │
│                                     │
│  ── CHỌN THUẬT TOÁN ──             │
│  [ Alpha-Beta ]    [ MCTS ]         │
│                                     │
│  ── ĐỘ KHÓ CỦA BOT ──            │
│  [ Dễ ]  [ Bình thường ]  [ Khó ]   │
│                                     │
│           [ ▶ BẮT ĐẦU ]            │
└─────────────────────────────────────┘
```

Khi chọn **Bot vs Bot**, xuất hiện thêm lựa chọn đối đầu:

```
  ── CHỌN ĐỐI ĐẦU ──
  [ AB vs AB ]  [ MCTS vs MCTS ]  [ AB vs MCTS ]
```

### Cấu hình độ khó

| Độ khó | Alpha-Beta | MCTS |
|--------|-----------|------|
| Dễ | depth = 2 (~0.1–0.5s) | 100 iterations (~1–2s) |
| Bình thường | depth = 3 (~0.5–3s) | 300 iterations (~3–7s) |
| Khó | time limit 5s (ID) | time limit 5s |

### Phím tắt trong game

| Phím | Chức năng |
|------|-----------| 
| `ENTER` | Về menu chính |
| `R` | Chơi lại cùng cài đặt |

---

## Thống kê hiệu năng

### Alpha-Beta log

```
[AlphaBeta/BLACK] depth=4/99 | nodes=34,300 | pruned=3,894 | tt_hits=1,520 | tt_size=74,051 | time=5.636s | score=690
```

| Field | Ý nghĩa |
|-------|---------| 
| `depth` | Độ sâu đã duyệt |
| `nodes` | Tổng số node đã duyệt |
| `pruned` | Số lần cắt nhánh (alpha/beta cut) |
| `tt_hits` | Số lần tra Transposition Table thành công |
| `time` | Thời gian tính (giây) |
| `score` | Điểm đánh giá vị trí (centipawns) |

### MCTS log

```
[MCTS/BLACK] iter=300 | iterations=300 | best_visits=22 | winrate=67.8% | children=20 | time=5.2s
```

| Field | Ý nghĩa |
|-------|---------|
| `iterations` | Số vòng lặp MCTS đã thực hiện |
| `best_visits` | Số lần visit của nước đi tốt nhất |
| `winrate` | Tỉ lệ thắng ước tính của nước đi (%) |
| `children` | Số nước đi đã khám phá từ vị trí hiện tại |
| `time` | Thời gian tính (giây) |

---

## So sánh Alpha-Beta vs MCTS

### Tóm tắt lý thuyết

| Tiêu chí | Alpha-Beta | MCTS |
|----------|-----------|------|
| Phương pháp | Tìm kiếm cây tất định (deterministic) | Mô phỏng ngẫu nhiên (probabilistic) |
| Đánh giá | Heuristic evaluation ở mọi node | Random rollout + heuristic ở cuối |
| Tầm nhìn | Giới hạn bởi depth | Không giới hạn depth lý thuyết |
| Tốc độ | Nhanh (pruning cắt bỏ nhiều nhánh) | Chậm hơn (cần nhiều simulation) |
| Mạnh ở | Tactical — tính toán chính xác | Strategic — chiến lược dài hạn |
| Nhược điểm | Phụ thuộc vào hàm đánh giá | Random rollouts rất nhiễu (noisy) |
| Phù hợp | Cờ vua, cờ tướng (branching factor vừa) | Cờ vây, Atari (branching factor lớn) |

### Kết quả thực nghiệm: Alpha-Beta (Trắng) vs MCTS (Đen)

Cấu hình: Cả hai dùng **Khó** — time limit 5s/nước

| Nước | AB depth | AB score | AB time | MCTS iter | MCTS winrate | MCTS time |
|------|----------|----------|---------|-----------|-------------|-----------|
| 1 | 4 | 40 | 6.6s | 222 | 64.3% | 5.0s |
| 2 | 4 | 90 | 5.1s | 205 | 62.5% | 5.0s |
| 3 | 3 | 155 | 5.2s | 178 | 72.7% | 5.0s |
| 4 | 3 | 215 | 5.5s | 163 | 81.8% | 5.0s |
| 5 | 3 | 380 | 5.3s | 168 | 77.8% | 5.0s |
| 6 | 3 | 490 | 5.0s | 174 | 54.5% | 5.0s |
| 8 | 3 | 760 | 5.1s | 180 | 25.0% | 5.0s |
| 9 | 3 | 1415 | 5.1s | 215 | 10.0% | 5.0s |
| 10 | 3 | 1655 | 5.1s | 206 | 0.0% | 5.0s |
| 15 | 3 | 2870 | 5.1s | 260 | 0.0% | 5.0s |
| 20 | 4 | 3120 | 5.3s | 466 | 0.0% | 5.0s |
| 25 | 4 | 3730 | 5.2s | 526 | 1.4% | 5.0s |
| 30 | 5 | 4105 | 5.8s | 589 | 4.7% | 5.0s |
| 31 | 5 | 100000 | 5.2s | — | — | — |

**Kết quả:** Alpha-Beta thắng bằng checkmate sau 31 nước.

### Nhận xét

1. **Cùng thời gian, hiệu quả khác biệt lớn:** Với cùng 5s/nước, Alpha-Beta duyệt 20,000–100,000 nodes ở depth 3–5, trong khi MCTS chỉ chạy được **160–600 iterations**. Nguyên nhân: mỗi iteration MCTS gọi `_all_legal_moves()` ~20 lần cho rollout, rất tốn thời gian trong Python.

2. **MCTS winrate sai lệch nghiêm trọng:** Ở nước 4, MCTS báo winrate **81.8%** trong khi AB score đã +215 (hơn 2 tốt). Ở nước 5, winrate vẫn **77.8%** với AB score +380. Random rollouts tạo ảo giác "đang thắng" vì chơi random từ vị trí thua vẫn có thể thắng bằng may mắn.

3. **Winrate giảm dần khi thua nặng:** Từ nước 9 trở đi (AB score > 1400), MCTS winrate rơi về **0.0%** — quá thua để random rollouts cứu vãn. Điều này cho thấy MCTS *có thể* nhận biết vị trí thua nặng, nhưng ở giai đoạn đó đã quá muộn.

4. **Alpha-Beta tăng depth ở tàn cuộc:** Từ depth 3 ở khai cuộc lên depth 4–5 ở tàn cuộc (ít quân → ít nhánh → tìm sâu hơn trong 5s). TT hits cũng tăng mạnh nhờ cache tích lũy. MCTS iterations cũng tăng ở cuối (ít quân → rollout nhanh hơn) nhưng vẫn không đủ để cạnh tranh.

5. **Alpha-Beta chiến thắng toàn diện trong cờ vua:** Điều này phù hợp với lý thuyết — cờ vua có hàm đánh giá tốt (material + PST), Alpha-Beta khai thác triệt để trong khi MCTS phụ thuộc vào random rollouts không hiệu quả.

6. **Khi nào MCTS tốt hơn:** MCTS phát huy sức mạnh trong các game có branching factor rất lớn (cờ vây: ~250 vs cờ vua: ~35) hoặc khi không có hàm đánh giá tốt. AlphaGo/AlphaZero kết hợp MCTS với neural network thay vì random rollouts để khắc phục nhược điểm này.

