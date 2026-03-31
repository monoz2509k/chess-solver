"""
alphabeta.py  —  Alpha-Beta Pruning bot
========================================
Tích hợp trực tiếp với Board / Piece từ classes.py của project.

Cải tiến so với phiên bản cũ:
  - Iterative Deepening: duyệt depth=1,2,...,N thay vì thẳng depth=N
  - Transposition Table: cache kết quả các vị trí đã tính để tránh tính lại

Cách dùng trong main.py:
    from Algo.alphabeta import AlphaBeta
    bot = AlphaBeta(board, team=1, depth=3)
    move = bot.get_best_move()
    if move:
        (fy, fx), (ty, tx) = move
"""

import time
from .algo import Algorithm


# ─────────────────────────────────────────────────────────
#  Bảng giá trị quân cờ (centipawns)
# ─────────────────────────────────────────────────────────
PIECE_VALUES = {
    "Pawn":   100,
    "Knight": 320,
    "Bishop": 330,
    "Rook":   500,
    "Queen":  900,
    "King":   20_000,
}

# Piece-Square Tables — góc nhìn quân TRẮNG (team 0, đi từ hàng 6 lên)
_PST_PAWN = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
_PST_KNIGHT = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]
_PST_BISHOP = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]
_PST_ROOK = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]
_PST_QUEEN = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]
_PST_KING_MID = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]
_PST_KING_END = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]
_PST_MAP = {
    "Pawn":   _PST_PAWN,
    "Knight": _PST_KNIGHT,
    "Bishop": _PST_BISHOP,
    "Rook":   _PST_ROOK,
    "Queen":  _PST_QUEEN,
    "King":   _PST_KING_MID,
}

# ─────────────────────────────────────────────────────────
#  Transposition Table — flag constants
# ─────────────────────────────────────────────────────────
TT_EXACT = 0   # điểm chính xác
TT_LOWER = 1   # alpha cut (lower bound)
TT_UPPER = 2   # beta cut  (upper bound)


# ─────────────────────────────────────────────────────────
#  Helper: hash bàn cờ thành key cho Transposition Table
# ─────────────────────────────────────────────────────────
def _board_key(board_obj) -> tuple:
    """
    Tạo key duy nhất đại diện cho trạng thái bàn cờ hiện tại.
    Dùng tuple của (piece_type, team) trên từng ô + lượt đi.
    """
    key = []
    for line in board_obj.board:
        for _, piece in line:
            if piece == 0:
                key.append(0)
            else:
                key.append((type(piece).__name__, piece.team))
    key.append(board_obj.turn)
    return tuple(key)


# ─────────────────────────────────────────────────────────
#  Helper: lấy tất cả nước đi hợp lệ của một team
# ─────────────────────────────────────────────────────────
def _all_legal_moves(board_obj, team: int) -> list:
    moves = []
    raw = board_obj.board
    original_turn = board_obj.turn
    board_obj.turn = team

    for fy in range(8):
        for fx in range(8):
            piece = raw[fy][fx][1]
            if piece == 0 or piece.team != team:
                continue
            if type(piece).__name__ == "King":
                legal = board_obj.get_king_legal_moves(fx, fy)
            else:
                legal = board_obj.get_legal_moves(fx, fy, piece)
            for (ty, tx) in legal:
                dest = raw[ty][tx][1]
                if dest == 0 or dest.team != team:
                    moves.append((fy, fx, ty, tx))

    board_obj.turn = original_turn
    return moves


# ─────────────────────────────────────────────────────────
#  Helper: apply / undo nước đi (không deepcopy)
# ─────────────────────────────────────────────────────────
def _apply_move(board_obj, fy, fx, ty, tx):
    raw = board_obj.board
    piece    = raw[fy][fx][1]
    captured = raw[ty][tx][1]
    raw[ty][tx][1] = piece
    raw[fy][fx][1] = 0
    return {"fy": fy, "fx": fx, "ty": ty, "tx": tx,
            "piece": piece, "captured": captured}


def _undo_move(board_obj, snap):
    raw = board_obj.board
    raw[snap["fy"]][snap["fx"]][1] = snap["piece"]
    raw[snap["ty"]][snap["tx"]][1] = snap["captured"]


# ─────────────────────────────────────────────────────────
#  Hàm đánh giá tĩnh
# ─────────────────────────────────────────────────────────
def _is_endgame(board_obj) -> bool:
    queens = minors = 0
    for line in board_obj.board:
        for _, p in line:
            if p == 0: continue
            n = type(p).__name__
            if n == "Queen": queens += 1
            elif n in ("Rook", "Bishop", "Knight"): minors += 1
    return queens == 0 or (queens <= 2 and minors <= 4)


def _pst_score(board_obj, team: int, endgame: bool) -> int:
    score = 0
    for y in range(8):
        for x in range(8):
            piece = board_obj.board[y][x][1]
            if piece == 0 or piece.team != team: continue
            name = type(piece).__name__
            if name not in _PST_MAP: continue
            table = _PST_KING_END if (name == "King" and endgame) else _PST_MAP[name]
            idx = y * 8 + x if team == 0 else (7 - y) * 8 + x
            score += table[idx]
    return score


def evaluate(board_obj) -> int:
    if board_obj.checkmate:
        return -100_000 if board_obj.turn == 0 else 100_000
    if board_obj.stalemate or board_obj.draw:
        return 0
    endgame = _is_endgame(board_obj)
    score = 0
    for line in board_obj.board:
        for _, piece in line:
            if piece == 0: continue
            val = PIECE_VALUES.get(type(piece).__name__, 0)
            score += val if piece.team == 0 else -val
    score += _pst_score(board_obj, 0, endgame)
    score -= _pst_score(board_obj, 1, endgame)
    return score


# ─────────────────────────────────────────────────────────
#  Move ordering — MVV-LVA + hint từ iteration trước / TT
# ─────────────────────────────────────────────────────────
def _move_priority(board_obj, fy, fx, ty, tx, hint=None) -> int:
    raw = board_obj.board
    captured = raw[ty][tx][1]
    attacker = raw[fy][fx][1]
    score = 0
    # Ưu tiên cao nhất: nước tốt nhất từ iteration trước
    if hint and (fy, fx, ty, tx) == hint:
        score += 20_000
    if captured != 0:
        cap_val = PIECE_VALUES.get(type(captured).__name__, 0)
        att_val = PIECE_VALUES.get(type(attacker).__name__, 0)
        score += 10 * cap_val - att_val   # MVV-LVA
    return score


def _order_moves(board_obj, moves, hint=None) -> list:
    return sorted(moves,
                  key=lambda m: _move_priority(board_obj, *m, hint=hint),
                  reverse=True)


# ─────────────────────────────────────────────────────────
#  Alpha-Beta với Transposition Table
# ─────────────────────────────────────────────────────────
def _alpha_beta(board_obj, depth, alpha, beta, maximizing, stats, tt, hint=None):
    """
    Alpha-Beta Pruning có Transposition Table.

    tt: dict dùng chung trong suốt một lần get_best_move().
        key   = _board_key(board_obj)
        value = {"depth": int, "score": int, "flag": TT_*, "move": tuple|None}
    """
    stats["nodes"] += 1

    # ── Tra Transposition Table ──────────────────────────
    key = _board_key(board_obj)
    if key in tt and tt[key]["depth"] >= depth:
        entry = tt[key]
        stats["tt_hits"] += 1
        if entry["flag"] == TT_EXACT:
            return entry["score"]
        elif entry["flag"] == TT_LOWER:
            alpha = max(alpha, entry["score"])
        elif entry["flag"] == TT_UPPER:
            beta  = min(beta,  entry["score"])
        if alpha >= beta:
            stats["pruned"] += 1
            return entry["score"]
        hint = entry.get("move")   # dùng move từ TT để sắp xếp tốt hơn

    # ── Điều kiện dừng ──────────────────────────────────
    if depth == 0:
        stats["leaves"] += 1
        return evaluate(board_obj)

    team = 0 if maximizing else 1
    moves = _all_legal_moves(board_obj, team)

    if not moves:
        stats["leaves"] += 1
        opp_moves = board_obj.get_all_moves((team + 1) % 2)
        king_pos = None
        for y in range(8):
            for x in range(8):
                p = board_obj.board[y][x][1]
                if p != 0 and p.team == team and type(p).__name__ == "King":
                    king_pos = (y, x)
        if king_pos and king_pos in opp_moves:
            return -100_000 if maximizing else 100_000
        return 0

    moves = _order_moves(board_obj, moves, hint=hint)

    # ── Tìm kiếm ────────────────────────────────────────
    orig_alpha = alpha
    best_score = -float("inf") if maximizing else float("inf")
    best_move  = None

    if maximizing:
        for (fy, fx, ty, tx) in moves:
            snap = _apply_move(board_obj, fy, fx, ty, tx)
            val  = _alpha_beta(board_obj, depth - 1, alpha, beta, False, stats, tt)
            _undo_move(board_obj, snap)
            if val > best_score:
                best_score = val
                best_move  = (fy, fx, ty, tx)
            alpha = max(alpha, best_score)
            if alpha >= beta:
                stats["pruned"] += 1
                break
    else:
        for (fy, fx, ty, tx) in moves:
            snap = _apply_move(board_obj, fy, fx, ty, tx)
            val  = _alpha_beta(board_obj, depth - 1, alpha, beta, True, stats, tt)
            _undo_move(board_obj, snap)
            if val < best_score:
                best_score = val
                best_move  = (fy, fx, ty, tx)
            beta = min(beta, best_score)
            if alpha >= beta:
                stats["pruned"] += 1
                break

    # ── Lưu vào Transposition Table ─────────────────────
    if best_score <= orig_alpha:
        flag = TT_UPPER
    elif best_score >= beta:
        flag = TT_LOWER
    else:
        flag = TT_EXACT

    tt[key] = {"depth": depth, "score": best_score, "flag": flag, "move": best_move}

    return best_score


# ─────────────────────────────────────────────────────────
#  Class chính: AlphaBeta
# ─────────────────────────────────────────────────────────
class AlphaBeta(Algorithm):
    """
    Bot cờ vua dùng Alpha-Beta Pruning + Iterative Deepening + Transposition Table.

    Ví dụ dùng trong main.py:
        bot = AlphaBeta(board, team=1, depth=3)
        move = bot.get_best_move()
        if move:
            (fy, fx), (ty, tx) = move
    """

    def __init__(self, board, team: int = 1, depth: int = 3):
        """
        Args:
            board:  Board object từ classes.py
            team:   0 = bot đánh trắng, 1 = bot đánh đen
            depth:  Độ sâu tối đa (3 = nhanh, 4 = trung bình, 5 = chậm)
        """
        super().__init__(board)
        self.team  = team
        self.depth = depth
        self.stats: dict = {}
        # TT tồn tại xuyên suốt ván → nước sau tái sử dụng cache nước trước
        self._tt: dict = {}

    def get_best_move(self):
        """
        Tìm nước đi tốt nhất dùng Iterative Deepening + Alpha-Beta + TT.

        Iterative Deepening:
          - Chạy depth=1, 2, ..., self.depth
          - Kết quả depth trước làm hint cho depth sau → move ordering tốt hơn
          - Nước đi trả về luôn là kết quả của lần duyệt sâu nhất

        Returns:
            ((from_y, from_x), (to_y, to_x))  hoặc  None
        """
        self.stats = {
            "nodes": 0, "leaves": 0, "pruned": 0,
            "tt_hits": 0, "time_s": 0.0,
        }
        t0 = time.time()

        maximizing_root = (self.team == 0)
        best_move  = None
        best_score = -float("inf") if maximizing_root else float("inf")

        moves = _all_legal_moves(self.board, self.team)
        if not moves:
            return None

        hint = None  # nước tốt nhất từ iteration trước

        # ── Iterative Deepening ──────────────────────────
        for current_depth in range(1, self.depth + 1):
            iter_best_score = -float("inf") if maximizing_root else float("inf")
            iter_best_move  = None

            ordered = _order_moves(self.board, moves, hint=hint)

            for (fy, fx, ty, tx) in ordered:
                snap  = _apply_move(self.board, fy, fx, ty, tx)
                score = _alpha_beta(
                    self.board,
                    current_depth - 1,
                    -float("inf"),
                    float("inf"),
                    not maximizing_root,
                    self.stats,
                    self._tt,
                )
                _undo_move(self.board, snap)

                if maximizing_root and score > iter_best_score:
                    iter_best_score = score
                    iter_best_move  = (fy, fx, ty, tx)
                elif not maximizing_root and score < iter_best_score:
                    iter_best_score = score
                    iter_best_move  = (fy, fx, ty, tx)

            if iter_best_move:
                best_move  = iter_best_move
                best_score = iter_best_score
                hint = iter_best_move   # làm hint cho iteration tiếp theo

        self.stats["time_s"]    = round(time.time() - t0, 3)
        self.stats["best_score"] = best_score
        self.stats["tt_size"]   = len(self._tt)

        if best_move is None:
            return None

        fy, fx, ty, tx = best_move
        return (fy, fx), (ty, tx)

    def clear_tt(self):
        """Xóa Transposition Table — gọi khi bắt đầu ván mới."""
        self._tt.clear()

    def get_stats(self) -> dict:
        """Trả về số liệu — dùng để so sánh với MCTS."""
        return self.stats

    def print_stats(self):
        s = self.stats
        side = "BLACK" if self.team == 1 else "WHITE"
        print(
            f"[AlphaBeta/{side}] depth={self.depth} | "
            f"nodes={s.get('nodes',0):,} | "
            f"pruned={s.get('pruned',0):,} | "
            f"tt_hits={s.get('tt_hits',0):,} | "
            f"tt_size={s.get('tt_size',0):,} | "
            f"time={s.get('time_s',0)}s | "
            f"score={s.get('best_score','?')}"
        )
