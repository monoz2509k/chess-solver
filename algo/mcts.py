"""
mcts.py  —  Monte Carlo Tree Search bot
========================================
Tích hợp trực tiếp với Board / Piece từ classes.py của project.

Thuật toán MCTS gồm 4 bước lặp:
  1. Selection   – duyệt cây bằng UCT (Upper Confidence Bound for Trees)
  2. Expansion   – mở rộng node chưa khám phá
  3. Simulation  – rollout ngẫu nhiên giới hạn độ sâu + đánh giá heuristic
  4. Backpropagation – cập nhật thống kê ngược lên gốc
"""

import math
import time
import random
import copy

from .algo import Algorithm
from .alphabeta import (
    _all_legal_moves, _apply_move, _undo_move, evaluate, _board_key
)


# ═══════════════════════════════════════════════════════════════
#  MCTSNode — mỗi node trong cây tìm kiếm
# ═══════════════════════════════════════════════════════════════

class MCTSNode:
    __slots__ = (
        "parent", "move", "team", "children",
        "wins", "visits", "untried_moves",
    )

    def __init__(self, parent, move, team, legal_moves):
        self.parent = parent
        self.move = move            # (fy, fx, ty, tx) đã dẫn đến node này
        self.team = team            # team sẽ đi tiếp TẠI node này
        self.children = []
        self.wins = 0.0
        self.visits = 0
        self.untried_moves = list(legal_moves)

    # ── UCT ────────────────────────────────────────────────────
    def uct_value(self, c=math.sqrt(2)):
        if self.visits == 0:
            return float("inf")
        exploitation = self.wins / self.visits
        exploration = c * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

    def best_child(self, c=math.sqrt(2)):
        return max(self.children, key=lambda ch: ch.uct_value(c))

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def is_terminal(self):
        return self.is_fully_expanded() and len(self.children) == 0


# ═══════════════════════════════════════════════════════════════
#  Helper — cập nhật castle flags sau khi apply_move
# ═══════════════════════════════════════════════════════════════

def _update_flags_after_move(board_obj, ty, tx):
    """Cập nhật castle flags sau khi một quân đã di chuyển đến (ty, tx)."""
    piece = board_obj.board[ty][tx][1]
    if piece == 0:
        return
    pname = type(piece).__name__
    if pname == "King":
        piece.short_castle = False
        piece.long_castle = False
    elif pname == "Rook" and hasattr(piece, 'side'):
        for line in board_obj.board:
            for _, p in line:
                if p != 0 and type(p).__name__ == "King" and p.team == piece.team:
                    if piece.side == 0:
                        p.long_castle = False
                    elif piece.side == 1:
                        p.short_castle = False


# ═══════════════════════════════════════════════════════════════
#  Rollout — simulation ngẫu nhiên giới hạn + heuristic eval
# ═══════════════════════════════════════════════════════════════

_ROLLOUT_DEPTH = 20          # số nước random tối đa mỗi rollout
_WIN_SCORE     = 100_000     # ngưỡng coi như thắng/thua tuyệt đối


def _rollout(board_obj, current_team, max_depth=_ROLLOUT_DEPTH):
    """
    Chơi ngẫu nhiên tối đa max_depth nước rồi đánh giá bằng heuristic.
    Trả về điểm từ góc nhìn quân TRẮNG (team 0).
    """
    depth = 0
    team = current_team

    while depth < max_depth:
        moves = _all_legal_moves(board_obj, team)
        if not moves:
            # Hết nước → kiểm tra checkmate hay stalemate
            opp_moves = board_obj.get_all_moves((team + 1) % 2)
            king_pos = None
            for y in range(8):
                for x in range(8):
                    p = board_obj.board[y][x][1]
                    if p != 0 and p.team == team and type(p).__name__ == "King":
                        king_pos = (y, x)
            if king_pos and king_pos in opp_moves:
                # Checkmate — team hiện tại thua
                return -_WIN_SCORE if team == 0 else _WIN_SCORE
            return 0  # stalemate / draw

        move = random.choice(moves)
        fy, fx, ty, tx = move
        _apply_move(board_obj, fy, fx, ty, tx)
        _update_flags_after_move(board_obj, ty, tx)
        team = (team + 1) % 2
        depth += 1

    # Hết độ sâu → dùng heuristic evaluate
    score = evaluate(board_obj)

    # Undo tất cả — KHÔNG cần vì caller sẽ undo bằng deepcopy
    return score


# ═══════════════════════════════════════════════════════════════
#  Snapshot — lưu / khôi phục trạng thái bàn cờ cho MCTS
# ═══════════════════════════════════════════════════════════════

def _save_board_state(board_obj):
    """Lưu toàn bộ trạng thái bàn cờ để khôi phục sau."""
    state = []
    for y in range(8):
        row = []
        for x in range(8):
            pos = board_obj.board[y][x][0]
            piece = board_obj.board[y][x][1]
            row.append((pos, piece))
        state.append(row)
    return {
        "board": state,
        "turn": board_obj.turn,
        "check": board_obj.check,
        "checkmate": board_obj.checkmate,
        "stalemate": board_obj.stalemate,
        "draw": board_obj.draw,
    }


def _restore_board_state(board_obj, saved):
    """Khôi phục trạng thái bàn cờ."""
    for y in range(8):
        for x in range(8):
            board_obj.board[y][x][0] = saved["board"][y][x][0]
            board_obj.board[y][x][1] = saved["board"][y][x][1]
    board_obj.turn = saved["turn"]
    board_obj.check = saved["check"]
    board_obj.checkmate = saved["checkmate"]
    board_obj.stalemate = saved["stalemate"]
    board_obj.draw = saved["draw"]


def _deep_copy_board_pieces(board_obj):
    """
    Deep-copy tất cả quân cờ trên bàn để rollout không ảnh hưởng
    trạng thái gốc (đặc biệt là en_passant, castle flags).
    """
    import copy as _copy
    piece_map = {}   # id(old_piece) -> new_piece
    for y in range(8):
        for x in range(8):
            piece = board_obj.board[y][x][1]
            if piece != 0:
                if id(piece) not in piece_map:
                    piece_map[id(piece)] = _copy.copy(piece)
                board_obj.board[y][x][1] = piece_map[id(piece)]


# ═══════════════════════════════════════════════════════════════
#  MCTS class chính
# ═══════════════════════════════════════════════════════════════

class MCTS(Algorithm):
    """
    Monte Carlo Tree Search bot.

    Args:
        board:       Board object từ classes.py
        team:        0 = trắng, 1 = đen
        iterations:  Số vòng lặp MCTS (dùng khi time_limit=None)
        time_limit:  Giới hạn thời gian tính bằng giây.
                     Nếu đặt, bot sẽ lặp cho đến khi hết giờ.
    """

    def __init__(self, board, team: int = 1,
                 iterations: int = 2000, time_limit: float = None):
        super().__init__(board)
        self.team = team
        self.iterations = iterations
        self.time_limit = time_limit
        self.stats: dict = {}

    # ── Entry point ────────────────────────────────────────────
    def get_best_move(self):
        t0 = time.time()

        root_moves = _all_legal_moves(self.board, self.team)
        if not root_moves:
            self.stats = {"iterations": 0, "time_s": 0.0}
            return None

        root = MCTSNode(
            parent=None,
            move=None,
            team=self.team,
            legal_moves=root_moves,
        )

        iteration = 0
        max_iter = self.iterations if self.time_limit is None else 10_000_000

        while iteration < max_iter:
            # Kiểm tra thời gian
            if self.time_limit and (time.time() - t0) >= self.time_limit:
                break

            # Lưu trạng thái gốc
            saved = _save_board_state(self.board)

            # ── 1. SELECTION ──────────────────────────────────
            node = root
            current_team = self.team

            while node.is_fully_expanded() and node.children:
                node = node.best_child()
                fy, fx, ty, tx = node.move
                _apply_move(self.board, fy, fx, ty, tx)
                _update_flags_after_move(self.board, ty, tx)
                current_team = (current_team + 1) % 2

            # ── 2. EXPANSION ─────────────────────────────────
            if node.untried_moves:
                move = random.choice(node.untried_moves)
                node.untried_moves.remove(move)
                fy, fx, ty, tx = move
                _apply_move(self.board, fy, fx, ty, tx)
                _update_flags_after_move(self.board, ty, tx)
                next_team = (current_team + 1) % 2

                # Tính legal moves cho node con
                child_moves = _all_legal_moves(self.board, next_team)
                child_node = MCTSNode(
                    parent=node,
                    move=move,
                    team=next_team,
                    legal_moves=child_moves,
                )
                node.children.append(child_node)
                node = child_node
                current_team = next_team

            # ── 3. SIMULATION (Rollout) ──────────────────────
            # Deep-copy pieces để rollout không hỏng state
            _deep_copy_board_pieces(self.board)
            score = _rollout(self.board, current_team)

            # ── 4. BACKPROPAGATION ───────────────────────────
            while node is not None:
                node.visits += 1
                # Score từ góc nhìn trắng (team 0)
                # Nếu bot là đen (team 1): thắng khi score < 0
                # Nếu bot là trắng (team 0): thắng khi score > 0
                if self.team == 0:
                    # Node thuộc team 0 (trắng) — score dương = tốt
                    if score > 0:
                        node.wins += 1
                    elif score == 0:
                        node.wins += 0.5
                else:
                    # Node thuộc team 1 (đen) — score âm = tốt
                    if score < 0:
                        node.wins += 1
                    elif score == 0:
                        node.wins += 0.5
                node = node.parent

            # Khôi phục trạng thái gốc
            _restore_board_state(self.board, saved)
            iteration += 1

        # ── Chọn nước tốt nhất ────────────────────────────────
        elapsed = round(time.time() - t0, 3)
        if not root.children:
            self.stats = {"iterations": iteration, "time_s": elapsed}
            return None

        # Chọn child có nhiều visit nhất (robust child)
        best = max(root.children, key=lambda c: c.visits)

        self.stats = {
            "iterations": iteration,
            "time_s": elapsed,
            "best_visits": best.visits,
            "best_winrate": round(best.wins / best.visits * 100, 1)
                           if best.visits > 0 else 0,
            "total_children": len(root.children),
        }

        fy, fx, ty, tx = best.move
        return (fy, fx), (ty, tx)

    # ── Stats ──────────────────────────────────────────────────
    def get_stats(self) -> dict:
        return self.stats

    def print_stats(self):
        s = self.stats
        side = "BLACK" if self.team == 1 else "WHITE"
        budget = (f"time≤{self.time_limit}s" if self.time_limit
                  else f"iter={self.iterations}")
        print(
            f"[MCTS/{side}] {budget} | "
            f"iterations={s.get('iterations', 0):,} | "
            f"best_visits={s.get('best_visits', 0):,} | "
            f"winrate={s.get('best_winrate', 0)}% | "
            f"children={s.get('total_children', 0)} | "
            f"time={s.get('time_s', 0)}s"
        )