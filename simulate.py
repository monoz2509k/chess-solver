import os
import sys
import time
import random
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from tqdm import tqdm
from datetime import datetime
import concurrent.futures

# Import existing Engine
from classes import Board, Queen, Rook, Bishop, Knight
from algo.alphabeta import AlphaBeta
from algo.mcts import MCTS

# ------------- PLACEHOLDER MCTS ------------- 
# If the real MCTS is empty, we dynamically patch it so the simulation doesn't crash.
# This serves as a random-move agent until the MCTS branch is pushed.
class PlaceholderMCTS:
    def __init__(self, board, team=1, depth=3, time_limit=2.0, **kwargs):
        self.board = board
        self.team = team
        self.time_limit = time_limit
        self.stats = {"nodes": 0, "evals": 0}

    def get_best_move(self):
        start_time = time.time()
        moves = []
        for y, row in enumerate(self.board.board):
            for x, cell in enumerate(row):
                piece = cell[1]
                if piece != 0 and getattr(piece, 'team', -1) == self.team:
                    if type(piece).__name__ == "King":
                        p_moves = self.board.get_king_legal_moves(x, y)
                    else:
                        all_enemy = self.board.get_all_moves((self.team + 1) % 2)
                        
                        try: # Catch different signatures
                            p_moves = piece.get_moves(x, y, self.board.board, all_enemy)
                        except TypeError:
                            p_moves = piece.get_moves(x, y, self.board.board)
                    
                    for (ty, tx) in p_moves:
                        moves.append(((y, x), (ty, tx)))
        self.stats["time"] = time.time() - start_time
        if not moves:
            return None
        return random.choice(moves)

    def print_stats(self):
        pass


def execute_move(board, move):
    """
    Executes a move exactly as main.py does, fully enforcing 
    Castling, En Passant, Promotion, and History rules.
    """
    (fy, fx), (ty, tx) = move
    piece = board.board[fy][fx][1]

    board.last_move = (ty, tx)
    board.reset_en_passant()
    board.check = 0

    p_name = type(piece).__name__
    if p_name == "King":
        if tx - fx == 2:  piece.castle(1, board.board)
        elif tx - fx == -2: piece.castle(0, board.board)
        piece.short_castle = False
        piece.long_castle  = False

    elif p_name == "Rook":
        for line in board.board:
            for _, row in line:
                if type(row).__name__ == "King" and row.team == piece.team:
                    if piece.side == 0:   row.long_castle  = False
                    elif piece.side == 1: row.short_castle = False

    elif p_name == "Pawn":
        if abs(ty - fy) == 2:
            piece.en_passant = True
        if board.board[ty][tx][1] == 0 and fx != tx:
            piece.do_en_passant(tx, ty, board.board)
        if (piece.team == 0 and ty == 0) or (piece.team == 1 and ty == 7):
            color = ".\\Pieces\\white" if piece.team == 0 else ".\\Pieces\\black"
            board.board[ty][tx][1] = Queen(piece.team, f"{color}_queen.png")
            board.board[fy][fx][1] = 0
            all_moves = board.get_all_moves(board.turn)
            board.turn = (board.turn + 1) % 2
            board.check_check(all_moves)
            board.check_checkmate_or_stalemate()
            board.check_draw()
            board.record_position()
            return True

    board.board[fy][fx][1] = 0
    board.board[ty][tx][1] = piece
    all_moves = board.get_all_moves(board.turn)
    board.turn = (board.turn + 1) % 2
    board.check_check(all_moves)
    board.check_checkmate_or_stalemate()
    board.check_draw()
    board.record_position()
    return True


def simulate_game(white_algo_cls, black_algo_cls, max_moves=150, time_limit=2.0):
    board = Board()
    white_bot = white_algo_cls(board, team=0, time_limit=time_limit)
    black_bot = black_algo_cls(board, team=1, time_limit=time_limit)
    
    move_count = 0
    match_telemetry = []

    while move_count < max_moves:
        if board.checkmate:
            return "White" if board.turn == 1 else "Black", move_count, "Checkmate", match_telemetry
        if board.stalemate:
            return "Draw", move_count, "Stalemate", match_telemetry
        if board.draw:
            return "Draw", move_count, "3-Fold Repetition", match_telemetry

        current_bot = white_bot if board.turn == 0 else black_bot
        team_name = "White" if board.turn == 0 else "Black"
        
        t0 = time.time()
        result = current_bot.get_best_move()
        dt = time.time() - t0
        
        if result is None:
            # Bot gave up or no moves -> Treat as checkmate/loss
            return "Black" if board.turn == 0 else "White", move_count, "Resignation", match_telemetry
            
        stats = getattr(current_bot, "stats", {})
        
        # MCTS tracks 'iterations', AlphaBeta tracks 'nodes' and 'depth_reached'
        ab_nodes = stats.get("nodes", 0) if isinstance(stats, dict) else 0
        ab_depth = stats.get("depth_reached", 0) if isinstance(stats, dict) else 0
        mcts_iters = stats.get("iterations", 0) if isinstance(stats, dict) else 0

        # Unify into 'Evaluations' (Nodes for AlphaBeta, Simulations/Rollouts for MCTS)
        evals = ab_nodes if type(current_bot).__name__ == "AlphaBeta" else mcts_iters
        eps = evals / dt if dt > 0.001 else 0  # Evaluations Per Second
        
        # Game Phase Categorization
        ply = move_count + 1
        if ply <= 20: phase = "Opening (0-20 ply)"
        elif ply <= 60: phase = "Middlegame (21-60 ply)"
        else: phase = "Endgame (60+ ply)"

        match_telemetry.append({
            "Move": ply,
            "Team": team_name,
            "Time_Seconds": dt,
            "Evaluations": evals,
            "EPS": eps,
            "Depth": ab_depth,
            "Phase": phase
        })

        execute_move(board, result)
        move_count += 1
        
    return "Draw", move_count, "50-Move Limit Hit", match_telemetry


def create_dashboard_for_limit(df_results, df_telemetry, time_label, output_dir, stamp):
    # Filter for the specific time limit
    df_res = df_results[df_results["TimeLimit"] == f"{time_label}s"] if "TimeLimit" in df_results.columns else df_results
    df_tel = df_telemetry[df_telemetry["TimeLimit"] == f"{time_label}s"] if "TimeLimit" in df_telemetry.columns else df_telemetry

    if df_res.empty: return

    # Create a unified professional dashboard display
    fig = plt.figure(figsize=(26, 26))
    title = f"Alpha-Beta vs MCTS Simulation Dashboard\\nTime Control Analysis: {time_label}s Capped"
    fig.suptitle(title, fontsize=32, fontweight='bold', y=0.98)

    palette_map = {"Draw": "#9b9b9b", "MCTS": "#d1a336", "AlphaBeta": "#3a3a3c", "White": "#f2f2f2", "Black": "#262626"}
    phase_order = ["Opening (0-20 ply)", "Middlegame (21-60 ply)", "Endgame (60+ ply)"]

    # 1. Overall Win Rate 
    ax1 = plt.subplot2grid((5, 2), (0, 0))
    wins = df_res["Winner"].value_counts()
    colors = [palette_map.get(w, "#555") for w in wins.index]
    ax1.pie(wins, labels=wins.index, autopct='%1.1f%%', colors=colors, startangle=90, textprops={'fontsize': 15, 'weight': 'bold'}, wedgeprops=dict(edgecolor='gray'))
    ax1.set_title("Overall Win Rate", fontsize=18, fontweight='bold')

    # 2. Algorithm Performance By Side
    ax2 = plt.subplot2grid((5, 2), (0, 1))
    side_results = []
    for _, row in df_res.iterrows():
        if row["Winner"] == "Draw": continue
        w_side = "White" if row["Winner"] == row["White"] else "Black"
        side_results.append({"Winning Algo": row["Winner"], "Won As": w_side})
    if side_results:
        df_sides = pd.DataFrame(side_results)
        import seaborn as sns
        sns.countplot(data=df_sides, x="Winning Algo", hue="Won As", palette={"White": "#f2f2f2", "Black": "#262626"}, edgecolor=".2", ax=ax2)
    ax2.set_title("Wins by Playing Color", fontsize=18, fontweight='bold')
    ax2.set_xlabel("Algorithm", fontsize=14)
    ax2.set_ylabel("Win Count", fontsize=14)
    if side_results: ax2.legend(title="Won Playing As")

    # 3. Match Terminations by Reason 
    ax3 = plt.subplot2grid((5, 2), (1, 0))
    sns.countplot(data=df_res, y="Reason", hue="Winner", palette=palette_map, edgecolor=".2", ax=ax3)
    ax3.set_title("Match Terminations by Reason", fontsize=18, fontweight='bold')
    ax3.set_xlabel("Match Count", fontsize=14)
    ax3.set_ylabel("Termination Rule", fontsize=14)

    # 4. Game Length Distribution
    ax4 = plt.subplot2grid((5, 2), (1, 1))
    sns.histplot(data=df_res, x="Moves", hue="Winner", multiple="stack", palette=palette_map, edgecolor=".2", bins=10, ax=ax4)
    ax4.set_title("Game Length Distribution (Plies)", fontsize=18, fontweight='bold')
    ax4.set_xlabel("Total Plies Played", fontsize=14)
    ax4.set_ylabel("Match Count", fontsize=14)

    # 5. Computation Time over Game Progression
    ax5 = plt.subplot2grid((5, 2), (2, 0), colspan=2)
    if not df_tel.empty:
        sns.lineplot(data=df_tel, x="Move", y="Time_Seconds", hue="Algo", palette=palette_map, errorbar=None, ax=ax5, linewidth=2.5)
        ax5.set_title("Average Computation Time per Move", fontsize=18, fontweight='bold')
        ax5.set_xlabel("Ply / Move Number", fontsize=14)
        ax5.set_ylabel("Average Time (Seconds)", fontsize=14)

    # 6. Evaluations Per Second (EPS)
    ax6 = plt.subplot2grid((5, 2), (3, 0))
    if not df_tel.empty and df_tel["EPS"].max() > 0:
        sns.boxplot(data=df_tel[df_tel["EPS"] > 0], x="Phase", y="EPS", hue="Algo", palette=palette_map, ax=ax6, order=phase_order)
        ax6.set_title("Search Speed per Game Phase (EPS)", fontsize=18, fontweight='bold')
        ax6.set_yscale("log")
        ax6.set_ylabel("Speed (Log Scale)", fontsize=14)
        ax6.set_xlabel("Game Phase", fontsize=14)
    else: ax6.set_title("Missing EPS Metric", fontsize=18, fontweight='bold')

    # 7. Evaluations over progression
    ax7 = plt.subplot2grid((5, 2), (3, 1))
    if not df_tel.empty:
        sns.lineplot(data=df_tel, x="Move", y="Evaluations", hue="Algo", palette=palette_map, errorbar=None, ax=ax7, linewidth=2.5)
        ax7.set_title("Total Evaluations per Move", fontsize=18, fontweight='bold')
        ax7.set_ylabel("Total Count (Log)", fontsize=14)
        ax7.set_yscale("log")
        ax7.set_xlabel("Ply / Move Number", fontsize=14)

    # 8. Elaborated Box: Latency per Phase
    ax8 = plt.subplot2grid((5, 2), (4, 0), colspan=2)
    if not df_tel.empty:
        sns.boxplot(data=df_tel, x="Phase", y="Time_Seconds", hue="Algo", palette=palette_map, ax=ax8, order=phase_order)
        ax8.set_title("Compute Time Variation by Phase", fontsize=18, fontweight='bold')
        ax8.set_yscale("log")
        ax8.set_ylabel("Time (Seconds)", fontsize=14)
        ax8.set_xlabel("Game Phase", fontsize=14)

    total_moves = df_res["Moves"].sum()
    avg_moves = df_res["Moves"].mean()
    import numpy as np
    mcts_avg_t = df_tel[df_tel['Algo'] == 'MCTS']['Time_Seconds'].mean() if not df_tel.empty else 0
    ab_avg_t = df_tel[df_tel['Algo'] == 'AlphaBeta']['Time_Seconds'].mean() if not df_tel.empty else 0

    footer_text = f"SIMULATION SUMMARY ({time_label}s Capped)  |  Total Matches: {len(df_res)}  |  Total Plies Evaluated: {total_moves}  |  Avg Match Length: {avg_moves:.1f} plies\nAlphaBeta Avg Time/Move: {ab_avg_t:.3f}s  |  MCTS Avg Time/Move: {mcts_avg_t:.3f}s  |  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    fig.text(0.5, 0.02, footer_text, ha='center', fontsize=18, fontweight='bold', color='black', bbox=dict(facecolor='#f0f0f0', edgecolor='gray', boxstyle='round,pad=1.0'))

    plt.subplots_adjust(top=0.94, hspace=0.45, wspace=0.25, bottom=0.08)
    plt.savefig(f"{output_dir}/dashboard_{stamp}_{time_label}s.png", dpi=300, bbox_inches='tight')
    plt.close()

def generate_reports(results, telemetry, output_dir="results"):
    os.makedirs(output_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    import pandas as pd
    df_results = pd.DataFrame(results)
    df_results.to_csv(f"{output_dir}/summary_{stamp}.csv", index=False)
    
    df_telemetry = pd.DataFrame(telemetry)
    df_telemetry.to_csv(f"{output_dir}/telemetry_{stamp}.csv", index=False)

    # 1.0s Limit Dashboard
    create_dashboard_for_limit(df_results, df_telemetry, "1.0", output_dir, stamp)
    # 2.5s Limit Dashboard
    create_dashboard_for_limit(df_results, df_telemetry, "2.5", output_dir, stamp)

def run_single_game(game_args):
    game_idx, time_limit, MCTS_Class = game_args
    
    # Alternate colors to remove first-mover advantage bias
    if game_idx % 2 == 0:
        w_bot, b_bot = AlphaBeta, MCTS_Class
        w_name, b_name = "AlphaBeta", "MCTS"
    else:
        w_bot, b_bot = MCTS_Class, AlphaBeta
        w_name, b_name = "MCTS", "AlphaBeta"

    winner, moves, reason, match_telemetry = simulate_game(
        w_bot, b_bot, max_moves=100, time_limit=time_limit
    )

    algo_winner = "Draw"
    if winner == "White": algo_winner = w_name
    elif winner == "Black": algo_winner = b_name

    result_dict = {
        "Game": game_idx + 1,
        "White": w_name,
        "Black": b_name,
        "Winner": algo_winner,
        "TimeLimit": f"{time_limit}s",
        "Moves": moves,
        "Reason": reason
    }
    
    for t in match_telemetry:
        t["Game"] = game_idx + 1
        t["TimeLimit"] = f"{time_limit}s"
        t["Algo"] = w_name if t["Team"] == "White" else b_name
        
    return result_dict, match_telemetry

if __name__ == "__main__":
    print("=== Alpha-Beta vs MCTS Simulator ===")
    
    # 1. Patch MCTS if it is empty!
    mcts_empty = False
    try:
        from algo.mcts import MCTS
        board = Board()
        # If MCTS does nothing natively, instantiate returns None on get_best_move usually
        instance = MCTS(board)
        if instance.get_best_move() is None:
            mcts_empty = True
    except Exception:
        mcts_empty = True
        
    MCTS_Class = PlaceholderMCTS if mcts_empty else MCTS
    print(f"[!] Using {'Placeholder (Random)' if mcts_empty else 'Actual'} MCTS code.")
    
    games_to_play = 20  # Run 20 tests
    time_limit = 1.0   # seconds
    
    all_results = []
    all_telemetry = []

    print(f"Simulating {games_to_play} matches between AlphaBeta and MCTS using multiprocessing (10@1.0s, 10@2.5s)...")
    
    tasks = []
    for i in range(10):
        tasks.append((i, 1.0, MCTS_Class))
    for i in range(10, 20):
        tasks.append((i, 2.5, MCTS_Class))
    
    # Using ProcessPoolExecutor to bypass Python's GIL for heavily CPU-bound execution
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # submit doesn't guarantee order of execution, but order defaults to finishing order
        futures = [executor.submit(run_single_game, task) for task in tasks]
        for future in tqdm(concurrent.futures.as_completed(futures), total=games_to_play):
            res, tele = future.result()
            all_results.append(res)
            all_telemetry.extend(tele)
            
    print("Simulation Complete. Generating PNG charts...")
    generate_reports(all_results, all_telemetry)
    print("Done! Charts saved in the 'results' folder.")
