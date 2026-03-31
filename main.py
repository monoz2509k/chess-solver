from classes import *
from algo.alphabeta import AlphaBeta


# ─────────────────────────────────────────────────────────
#  Màu sắc & font
# ─────────────────────────────────────────────────────────
C_BG        = (15,  15,  20)
C_PANEL     = (25,  25,  35)
C_BORDER    = (60,  60,  80)
C_WHITE     = (235, 230, 215)
C_GOLD      = (212, 175,  55)
C_GOLD_DIM  = (140, 110,  30)
C_RED       = (200,  60,  60)
C_GREEN     = ( 60, 180,  80)
C_BTN_HOVER = (45,  45,  65)
C_TEXT_DIM  = (130, 130, 150)


def draw_rounded_rect(surface, color, rect, radius=12, border=0, border_color=None):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surface, border_color, rect, border, border_radius=radius)


# ─────────────────────────────────────────────────────────
#  Màn hình Menu
# ─────────────────────────────────────────────────────────
def show_menu(window, clock):
    """
    Hiển thị menu chọn chế độ chơi.
    Trả về (human_team, bot_depth):
        human_team = 0  → người chơi trắng
        human_team = 1  → người chơi đen
        human_team = -1 → bot vs bot
    """
    W, H = window.get_size()

    try:
        font_title  = pygame.font.SysFont("Georgia",      42, bold=True)
        font_sub    = pygame.font.SysFont("Georgia",      16)
        font_btn    = pygame.font.SysFont("Verdana",      17, bold=True)
        font_label  = pygame.font.SysFont("Verdana",      13)
        font_small  = pygame.font.SysFont("Verdana",      12)
    except Exception:
        font_title = font_sub = font_btn = font_label = font_small = pygame.font.SysFont("Arial", 16)

    # ── Layout các button chế độ ────────────────────────
    mode_buttons = [
        {"label": "Trắng  vs  Bot",  "icon": "♔", "team": 0,  "desc": "Bạn đánh quân trắng — đi trước"},
        {"label": "Đen  vs  Bot",    "icon": "♚", "team": 1,  "desc": "Bạn đánh quân đen — đi sau"},
        {"label": "Bot  vs  Bot",    "icon": "⚙", "team": -1, "desc": "Xem AI tự đánh với nhau"},
    ]

    depth_options = [
        {"label": "Dễ",    "depth": 2, "desc": "Depth 2 — rất nhanh"},
        {"label": "Bình thường", "depth": 3, "desc": "Depth 3 — cân bằng"},
        {"label": "Khó",   "depth": 4, "desc": "Depth 4 — chậm hơn"},
    ]

    selected_mode  = 0    # index trong mode_buttons
    selected_depth = 1    # index trong depth_options

    btn_w, btn_h = 480, 64
    btn_x = (W - btn_w) // 2

    mode_y_start  = 170
    mode_gap      = 76

    depth_w  = 140
    depth_gap = 16
    depth_total = 3 * depth_w + 2 * depth_gap
    depth_x_start = (W - depth_total) // 2
    depth_y = 450

    start_rect = pygame.Rect((W - 200) // 2, 530, 200, 50)

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        window.fill(C_BG)

        # ── Tiêu đề ──────────────────────────────────────
        title_surf = font_title.render("♟  Chess AI  ♟", True, C_GOLD)
        sub_surf   = font_sub.render("Alpha-Beta Pruning Bot", True, C_TEXT_DIM)
        window.blit(title_surf, title_surf.get_rect(centerx=W//2, top=50))
        window.blit(sub_surf,   sub_surf.get_rect(centerx=W//2,   top=102))

        # Đường kẻ trang trí
        pygame.draw.line(window, C_BORDER, (60, 135), (W - 60, 135), 1)

        # ── Label "Chọn chế độ" ──────────────────────────
        lbl = font_label.render("CHỌN CHẾ ĐỘ CHƠI", True, C_TEXT_DIM)
        window.blit(lbl, lbl.get_rect(centerx=W//2, top=148))

        # ── Buttons chế độ ───────────────────────────────
        for i, m in enumerate(mode_buttons):
            rect = pygame.Rect(btn_x, mode_y_start + i * mode_gap, btn_w, btn_h)
            hovered = rect.collidepoint(mx, my)

            is_sel = (i == selected_mode)
            bg  = C_GOLD_DIM  if is_sel  else (C_BTN_HOVER if hovered else C_PANEL)
            bdr = C_GOLD      if is_sel  else (C_BORDER    if hovered else C_BORDER)
            bw  = 2           if is_sel  else 1

            draw_rounded_rect(window, bg, rect, radius=10, border=bw, border_color=bdr)

            # Icon
            icon_surf = pygame.font.SysFont("Segoe UI Symbol", 26).render(m["icon"], True,
                        C_GOLD if is_sel else C_WHITE)
            window.blit(icon_surf, (rect.x + 20, rect.y + (btn_h - icon_surf.get_height()) // 2))

            # Label chính
            lbl_surf = font_btn.render(m["label"], True, C_GOLD if is_sel else C_WHITE)
            window.blit(lbl_surf, (rect.x + 62, rect.y + 14))

            # Mô tả nhỏ
            desc_surf = font_small.render(m["desc"], True,
                        C_GOLD_DIM if is_sel else C_TEXT_DIM)
            window.blit(desc_surf, (rect.x + 64, rect.y + 36))

        # ── Label "Độ khó" ────────────────────────────────
        pygame.draw.line(window, C_BORDER, (60, 425), (W - 60, 425), 1)
        lbl2 = font_label.render("ĐỘ KHÓ CỦA BOT", True, C_TEXT_DIM)
        window.blit(lbl2, lbl2.get_rect(centerx=W//2, top=432))

        # ── Buttons độ khó ────────────────────────────────
        for i, d in enumerate(depth_options):
            dx = depth_x_start + i * (depth_w + depth_gap)
            rect = pygame.Rect(dx, depth_y, depth_w, 52)
            hovered = rect.collidepoint(mx, my)
            is_sel  = (i == selected_depth)

            bg  = C_GOLD_DIM if is_sel  else (C_BTN_HOVER if hovered else C_PANEL)
            bdr = C_GOLD     if is_sel  else (C_BORDER    if hovered else C_BORDER)
            bw  = 2          if is_sel  else 1

            draw_rounded_rect(window, bg, rect, radius=8, border=bw, border_color=bdr)

            lbl_surf  = font_btn.render(d["label"], True, C_GOLD if is_sel else C_WHITE)
            desc_surf = font_small.render(d["desc"], True,
                        C_GOLD_DIM if is_sel else C_TEXT_DIM)
            window.blit(lbl_surf,  lbl_surf.get_rect(centerx=rect.centerx, top=rect.y + 8))
            window.blit(desc_surf, desc_surf.get_rect(centerx=rect.centerx, top=rect.y + 32))

        # ── Nút Bắt đầu ──────────────────────────────────
        start_hov = start_rect.collidepoint(mx, my)
        start_bg  = C_GREEN if start_hov else (40, 140, 60)
        draw_rounded_rect(window, start_bg, start_rect, radius=10,
                          border=2, border_color=C_GREEN)
        start_lbl = font_btn.render("▶   BẮT ĐẦU", True, C_WHITE)
        window.blit(start_lbl, start_lbl.get_rect(center=start_rect.center))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Click chế độ
                for i, m in enumerate(mode_buttons):
                    r = pygame.Rect(btn_x, mode_y_start + i * mode_gap, btn_w, btn_h)
                    if r.collidepoint(mx, my):
                        selected_mode = i

                # Click độ khó
                for i in range(3):
                    dx = depth_x_start + i * (depth_w + depth_gap)
                    r = pygame.Rect(dx, depth_y, depth_w, 52)
                    if r.collidepoint(mx, my):
                        selected_depth = i

                # Bắt đầu
                if start_rect.collidepoint(mx, my):
                    running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    running = False

        clock.tick(60)

    return mode_buttons[selected_mode]["team"], depth_options[selected_depth]["depth"]


# ─────────────────────────────────────────────────────────
#  Áp dụng nước đi của bot lên board
# ─────────────────────────────────────────────────────────
def make_bot_move(board, bot):
    result = bot.get_best_move()
    bot.print_stats()

    if result is None:
        return

    (fy, fx), (ty, tx) = result
    piece = board.board[fy][fx][1]

    board.last_move = (ty, tx)
    board.reset_en_passant()
    board.check = 0

    if type(piece).__name__ == "King":
        if tx - fx == 2:
            piece.castle(1, board.board)
        elif tx - fx == -2:
            piece.castle(0, board.board)
        piece.short_castle = False
        piece.long_castle  = False

    elif type(piece).__name__ == "Rook":
        for line in board.board:
            for _, row in line:
                if type(row).__name__ == "King" and row.team == piece.team:
                    if piece.side == 0: row.long_castle  = False
                    elif piece.side == 1: row.short_castle = False

    elif type(piece).__name__ == "Pawn":
        if abs(ty - fy) == 2:
            piece.en_passant = True
        if board.board[ty][tx][1] == 0 and fx != tx:
            piece.do_en_passant(tx, ty, board.board)
        # Phong cấp tự động → Hậu
        if (piece.team == 0 and ty == 0) or (piece.team == 1 and ty == 7):
            color = ".\\Pieces\\white" if piece.team == 0 else ".\\Pieces\\black"
            board.board[ty][tx][1] = Queen(piece.team, f"{color}_queen.png")
            board.board[fy][fx][1] = 0
            all_moves = board.get_all_moves(board.turn)
            board.turn = (board.turn + 1) % 2
            board.check_check(all_moves)
            board.check_checkmate_or_stalemate()
            board.check_draw()
            return

    board.board[fy][fx][1] = 0
    board.board[ty][tx][1] = piece

    all_moves = board.get_all_moves(board.turn)
    board.turn = (board.turn + 1) % 2
    board.check_check(all_moves)
    board.check_checkmate_or_stalemate()
    board.check_draw()


# ─────────────────────────────────────────────────────────
#  Game loop chính
# ─────────────────────────────────────────────────────────
def run_game(window, clock, human_team, bot_depth):
    try:
        font_ui    = pygame.font.SysFont("Verdana", 14, bold=True)
        font_small = pygame.font.SysFont("Verdana", 12)
    except Exception:
        font_ui = font_small = pygame.font.SysFont("Arial", 13)

    check_msg     = font_ui.render("Check!!", True, C_RED)
    checkmate_msg = font_ui.render("Checkmate!!", True, C_RED)
    stalemate_msg = font_ui.render("Stalemate!!", True, C_RED)
    draw_msg      = font_ui.render("Draw!!", True, C_GOLD)
    menu_hint     = font_small.render("ENTER = về menu  |  R = chơi lại", True, C_TEXT_DIM)

    board = Board()

    # Tạo bot
    bot_team = 1 - human_team if human_team >= 0 else 1
    bot = AlphaBeta(board, team=bot_team, depth=bot_depth)
    bot_white = AlphaBeta(board, team=0, depth=bot_depth)  # cho chế độ bot vs bot
    bot_black = AlphaBeta(board, team=1, depth=bot_depth)

    W, H = window.get_size()
    selected     = None
    moves        = []
    index_x      = index_y = 0
    aux_index_x  = aux_index_y = 0
    promotion_x  = promotion_y = 0

    def redraw():
        window.fill(C_BG)
        window.blit(board.image, (0, 0))

        y = 0
        for line in board.board:
            x = 0
            for pos, row in line:
                if row != 0:
                    window.blit(row.image, pos)
                if (y, x) in moves:
                    pygame.draw.circle(window, (220, 80, 80),
                                       (pos[0] + 30, pos[1] + 35), 6)
                x += 1
            y += 1

        if board.promotion:
            if board.turn != 0:
                window.blit(board.white_promotion, (20, 20))
            else:
                window.blit(board.black_promotion, (20, 20))

        # Hiển thị trạng thái
        game_over = board.checkmate or board.stalemate or board.draw
        if board.checkmate:
            window.blit(checkmate_msg, (8, 4))
        elif board.stalemate:
            window.blit(stalemate_msg, (8, 4))
        elif board.draw:
            window.blit(draw_msg, (8, 4))
        elif board.check > 0:
            window.blit(check_msg, (8, 4))

        if game_over:
            window.blit(menu_hint, menu_hint.get_rect(centerx=W//2, bottom=H - 6))

        # Hiển thị lượt đi
        if not game_over:
            side = "Trắng" if board.turn == 0 else "Đen"
            who  = "  (Bạn)" if board.turn == human_team else "  (Bot)"
            if human_team == -1:
                who = "  (Bot)"
            turn_surf = font_small.render(f"Lượt: {side}{who}", True, C_TEXT_DIM)
            window.blit(turn_surf, (W - turn_surf.get_width() - 8, 6))

        pygame.display.flip()

    running = True
    while running:
        clock.tick(30)

        game_over = board.checkmate or board.stalemate or board.draw or board.promotion

        # ── Lượt bot ─────────────────────────────────────
        if not game_over:
            if human_team == -1:
                # Bot vs Bot
                cb = bot_white if board.turn == 0 else bot_black
                make_bot_move(board, cb)
                pygame.time.delay(200)
            elif board.turn != human_team:
                make_bot_move(board, bot)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            elif event.type == pygame.KEYDOWN:
                # Phong cấp thủ công
                if board.promotion and human_team >= 0:
                    board.promotion = False
                    color = ".\\Pieces\\white" if board.turn != 0 else ".\\Pieces\\black"
                    team  = 0 if board.turn != 0 else 1
                    if event.key in (pygame.K_1, pygame.K_KP_1):
                        board.board[promotion_y][promotion_x][1] = Queen(team, f"{color}_queen.png")
                    elif event.key in (pygame.K_2, pygame.K_KP_2):
                        board.board[promotion_y][promotion_x][1] = Rook(team, f"{color}_rook.png", -1)
                    elif event.key in (pygame.K_3, pygame.K_KP_3):
                        board.board[promotion_y][promotion_x][1] = Bishop(team, f"{color}_bishop.png")
                    elif event.key in (pygame.K_4, pygame.K_KP_4):
                        board.board[promotion_y][promotion_x][1] = Knight(team, f"{color}_knight.png")
                    else:
                        board.promotion = True
                    if not board.promotion:
                        all_moves = board.get_all_moves((board.turn + 1) % 2)
                        board.check_check(all_moves)
                        board.check_checkmate_or_stalemate()
                        board.check_draw()

                if event.key == pygame.K_RETURN:
                    return "menu"   # về menu
                if event.key == pygame.K_r:
                    return "restart"  # chơi lại cùng cài đặt

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if board.promotion or board.checkmate or board.stalemate or board.draw:
                    continue
                if human_team >= 0 and board.turn != human_team:
                    continue

                x, y = pygame.mouse.get_pos()
                index_x = (x - 20) // 70
                index_y = (y -  8) // 70

                if not (0 <= index_x < 8 and 0 <= index_y < 8):
                    continue

                tile = board.board[index_y][index_x][1]

                if selected is not None and (index_y, index_x) in moves:
                    board.last_move = (index_y, index_x)
                    board.reset_en_passant()
                    board.check = 0

                    if type(selected).__name__ == "King":
                        if index_x - aux_index_x == 2:
                            selected.castle(1, board.board)
                        if index_x - aux_index_x == -2:
                            selected.castle(0, board.board)
                        selected.short_castle = False
                        selected.long_castle  = False

                    elif type(selected).__name__ == "Rook":
                        for line in board.board:
                            for _, row in line:
                                if type(row).__name__ == "King" and row.team == selected.team:
                                    if selected.side == 0: row.long_castle  = False
                                    elif selected.side == 1: row.short_castle = False

                    elif type(selected).__name__ == "Pawn":
                        if abs(index_y - aux_index_y) == 2:
                            selected.en_passant = True
                        if board.board[index_y][index_x][1] == 0 and aux_index_x != index_x:
                            selected.do_en_passant(index_x, index_y, board.board)
                        if (selected.team == 0 and index_y == 0) or (selected.team == 1 and index_y == 7):
                            board.promotion = True
                            promotion_x, promotion_y = index_x, index_y

                    board.board[aux_index_y][aux_index_x][1] = 0
                    board.board[index_y][index_x][1] = selected
                    all_moves = board.get_all_moves(board.turn)
                    board.turn = (board.turn + 1) % 2
                    board.check_check(all_moves)
                    board.check_checkmate_or_stalemate()
                    board.check_draw()

                    moves    = []
                    selected = None

                elif tile != 0 and tile.team == board.turn:
                    moves    = []
                    selected = board.board[index_y][index_x][1]

                    if type(selected).__name__ == "King":
                        aux_moves = board.get_king_legal_moves(index_x, index_y)
                    else:
                        aux_moves = board.get_legal_moves(index_x, index_y, selected)

                    for move in aux_moves:
                        try:
                            if board.board[move[0]][move[1]][1].team != board.turn:
                                moves.append(move)
                        except AttributeError:
                            moves.append(move)

                    aux_index_x, aux_index_y = index_x, index_y

        redraw()

    return "menu"


# ─────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────
def main():
    pygame.init()
    pygame.font.init()

    W, H = 600, 600
    pygame.display.set_caption("Chess — Alpha-Beta AI")
    pygame.display.set_icon(pygame.image.load('.\\Pieces\\icon.png'))
    window = pygame.display.set_mode((W, H))
    clock  = pygame.time.Clock()

    human_team = 0
    bot_depth  = 3

    action = "menu"
    while True:
        if action == "menu":
            human_team, bot_depth = show_menu(window, clock)
            action = "game"
        elif action in ("game", "restart"):
            action = run_game(window, clock, human_team, bot_depth)


if __name__ == "__main__":
    main()
