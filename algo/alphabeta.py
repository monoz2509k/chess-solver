"""
alphabeta.py  —  Alpha-Beta Pruning bot
========================================
Tích hợp trực tiếp với Board / Piece từ classes.py của project.

Cải tiến:
  - Iterative Deepening
  - Transposition Table
  - Luật chống lặp: bot không chọn nước tạo vị trí lặp lần thứ 3
"""

import time
from .algo import Algorithm


PIECE_VALUES = {
    "Pawn":   100,
    "Knight": 320,
    "Bishop": 330,
    "Rook":   500,
    "Queen":  900,
    "King":   20_000,
}

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
    "Pawn":   _PST_PAWN,   "Knight": _PST_KNIGHT,
    "Bishop": _PST_BISHOP, "Rook":   _PST_ROOK,
    "Queen":  _PST_QUEEN,  "King":   _PST_KING_MID,
}

TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2


def _board_key(board_obj) -> tuple:
    key = []
    for line in board_obj.board:
        for _, piece in line:
            if piece == 0: key.append(0)
            else: key.append((type(piece).__name__, piece.team))
    key.append(board_obj.turn)
    return tuple(key)


def _all_legal_moves(board_obj, team: int) -> list:
    """Lấy tất cả nước đi hợp lệ, loại bỏ nước sẽ tạo lặp lần thứ 3."""
    moves = []
    raw   = board_obj.board
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
                if dest != 0 and dest.team == team:
                    continue
                # ── Lọc nước lặp lần thứ 3 ──────────────
                if board_obj.is_repetition_move(fy, fx, ty, tx):
                    continue
                moves.append((fy, fx, ty, tx))

    board_obj.turn = original_turn
    return moves


def _apply_move(board_obj, fy, fx, ty, tx):
    raw      = board_obj.board
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
            idx   = y * 8 + x if team == 0 else (7 - y) * 8 + x
            score += table[idx]
    return score


def evaluate(board_obj) -> int:
    if board_obj.checkmate:
        return -100_000 if board_obj.turn == 0 else 100_000
    if board_obj.stalemate or board_obj.draw:
        return 0
    endgame = _is_endgame(board_obj)
    score   = 0
    for line in board_obj.board:
        for _, piece in line:
            if piece == 0: continue
            val    = PIECE_VALUES.get(type(piece).__name__, 0)
            score += val if piece.team == 0 else -val
    score += _pst_score(board_obj, 0, endgame)
    score -= _pst_score(board_obj, 1, endgame)
    return score


def _move_priority(board_obj, fy, fx, ty, tx, hint=None) -> int:
    raw      = board_obj.board
    captured = raw[ty][tx][1]
    attacker = raw[fy][fx][1]
    score    = 0
    if hint and (fy, fx, ty, tx) == hint:
        score += 20_000
    if captured != 0:
        cap_val = PIECE_VALUES.get(type(captured).__name__, 0)
        att_val = PIECE_VALUES.get(type(attacker).__name__, 0)
        score  += 10 * cap_val - att_val
    return score


def _order_moves(board_obj, moves, hint=None) -> list:
    return sorted(moves, key=lambda m: _move_priority(board_obj, *m, hint=hint), reverse=True)


def _alpha_beta(board_obj, depth, alpha, beta, maximizing, stats, tt, hint=None):
    stats["nodes"] += 1

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
        hint = entry.get("move")

    if depth == 0:
        stats["leaves"] += 1
        return evaluate(board_obj)

    team  = 0 if maximizing else 1
    moves = _all_legal_moves(board_obj, team)

    if not moves:
        stats["leaves"] += 1
        opp_moves = board_obj.get_all_moves((team + 1) % 2)
        king_pos  = None
        for y in range(8):
            for x in range(8):
                p = board_obj.board[y][x][1]
                if p != 0 and p.team == team and type(p).__name__ == "King":
                    king_pos = (y, x)
        if king_pos and king_pos in opp_moves:
            return -100_000 if maximizing else 100_000
        return 0

    moves      = _order_moves(board_obj, moves, hint=hint)
    orig_alpha = alpha
    best_score = -float("inf") if maximizing else float("inf")
    best_move  = None

    if maximizing:
        for (fy, fx, ty, tx) in moves:
            snap = _apply_move(board_obj, fy, fx, ty, tx)
            val  = _alpha_beta(board_obj, depth-1, alpha, beta, False, stats, tt)
            _undo_move(board_obj, snap)
            if val > best_score:
                best_score = val; best_move = (fy, fx, ty, tx)
            alpha = max(alpha, best_score)
            if alpha >= beta:
                stats["pruned"] += 1; break
    else:
        for (fy, fx, ty, tx) in moves:
            snap = _apply_move(board_obj, fy, fx, ty, tx)
            val  = _alpha_beta(board_obj, depth-1, alpha, beta, True, stats, tt)
            _undo_move(board_obj, snap)
            if val < best_score:
                best_score = val; best_move = (fy, fx, ty, tx)
            beta = min(beta, best_score)
            if alpha >= beta:
                stats["pruned"] += 1; break

    flag = TT_UPPER if best_score <= orig_alpha else (TT_LOWER if best_score >= beta else TT_EXACT)
    tt[key] = {"depth": depth, "score": best_score, "flag": flag, "move": best_move}
    return best_score


class AlphaBeta(Algorithm):
    def __init__(self, board, team: int = 1, depth: int = 3, time_limit: float = None):
        """
        Args:
            board:       Board object từ classes.py
            team:        0 = trắng, 1 = đen
            depth:       Độ sâu tối đa (dùng khi time_limit=None)
            time_limit:  Giới hạn thời gian tính bằng giây (ví dụ: 3.0).
                         Nếu đặt, bot sẽ duyệt sâu dần và dừng khi hết giờ,
                         trả về kết quả tốt nhất tìm được cho đến lúc đó.
                         Nếu None, dùng depth cố định như cũ.
        """
        super().__init__(board)
        self.team       = team
        self.depth      = depth
        self.time_limit = time_limit
        self.stats: dict = {}
        self._tt:   dict = {}

    def get_best_move(self):
        self.stats = {"nodes": 0, "leaves": 0, "pruned": 0, "tt_hits": 0, "time_s": 0.0}
        t0 = time.time()

        maximizing_root = (self.team == 0)
        best_move  = None
        best_score = -float("inf") if maximizing_root else float("inf")

        moves = _all_legal_moves(self.board, self.team)
        if not moves:
            return None

        # Xác định depth tối đa: nếu có time_limit thì duyệt tới depth rất lớn,
        # vòng lặp sẽ tự dừng khi hết giờ
        max_depth = self.depth if self.time_limit is None else 99

        hint = None
        for current_depth in range(1, max_depth + 1):

            # ── Kiểm tra thời gian trước mỗi iteration ──
            if self.time_limit and (time.time() - t0) >= self.time_limit:
                break

            iter_best_score = -float("inf") if maximizing_root else float("inf")
            iter_best_move  = None
            ordered = _order_moves(self.board, moves, hint=hint)

            for (fy, fx, ty, tx) in ordered:
                # Kiểm tra giữa chừng — nếu hết giờ thì bỏ iteration này,
                # giữ nguyên best_move của iteration trước (luôn hoàn chỉnh)
                if self.time_limit and (time.time() - t0) >= self.time_limit:
                    iter_best_move = None   # đánh dấu iteration chưa xong
                    break

                snap  = _apply_move(self.board, fy, fx, ty, tx)
                score = _alpha_beta(self.board, current_depth - 1,
                                    -float("inf"), float("inf"),
                                    not maximizing_root, self.stats, self._tt)
                _undo_move(self.board, snap)

                if maximizing_root and score > iter_best_score:
                    iter_best_score = score
                    iter_best_move  = (fy, fx, ty, tx)
                elif not maximizing_root and score < iter_best_score:
                    iter_best_score = score
                    iter_best_move  = (fy, fx, ty, tx)

            # Chỉ cập nhật best nếu iteration hoàn thành đầy đủ
            if iter_best_move:
                best_move  = iter_best_move
                best_score = iter_best_score
                hint       = iter_best_move
                self.stats["depth_reached"] = current_depth

        self.stats["time_s"]     = round(time.time() - t0, 3)
        self.stats["best_score"] = best_score
        self.stats["tt_size"]    = len(self._tt)

        if best_move is None:
            return None
        fy, fx, ty, tx = best_move
        return (fy, fx), (ty, tx)

    def clear_tt(self):
        self._tt.clear()

    def get_stats(self) -> dict:
        return self.stats

    def print_stats(self):
        s    = self.stats
        side = "BLACK" if self.team == 1 else "WHITE"
        depth_info = (f"depth={s.get('depth_reached','?')}/{self.depth}"
                      if self.time_limit else f"depth={self.depth}")
        print(
            f"[AlphaBeta/{side}] {depth_info} | "
            f"nodes={s.get('nodes',0):,} | pruned={s.get('pruned',0):,} | "
            f"tt_hits={s.get('tt_hits',0):,} | tt_size={s.get('tt_size',0):,} | "
            f"time={s.get('time_s',0)}s | score={s.get('best_score','?')}"
        )
        