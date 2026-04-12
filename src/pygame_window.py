import random

import pygame

from src import gf2_solver, solver
from src.board import Board


class Window:
    WIDTH = 1280
    HEIGHT = 860
    SOLVER_STEP_MS = 500
    GAME_AUTO_STEP_MS = 500
    MODE_LABEL_OVERRIDES = {
        "gf2": "GF(2)",
        "random_player": "Random Player",
    }

    def __init__(self, on_click_callback=None):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Lights Out")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "menu"
        self.on_click_callback = on_click_callback
        self.click_targets = []

        self.palette = {
            "bg_top": (13, 18, 34),
            "bg_bottom": (22, 35, 59),
            "panel": (25, 33, 53),
            "panel_alt": (31, 42, 67),
            "panel_border": (76, 92, 123),
            "text": (242, 245, 251),
            "muted": (171, 181, 203),
            "accent": (92, 141, 255),
            "accent_2": (90, 214, 190),
            "warning": (255, 192, 108),
            "danger": (255, 124, 124),
            "success": (123, 227, 154),
            "on": (18, 18, 18),
            "off": (245, 245, 245),
            "cell_border": (132, 145, 174),
            "shadow": (6, 9, 18),
        }

        self.font_title = pygame.font.SysFont("segoeui", 42, bold=True)
        self.font_heading = pygame.font.SysFont("segoeui", 24, bold=True)
        self.font_body = pygame.font.SysFont("segoeui", 18)
        self.font_small = pygame.font.SysFont("segoeui", 15)
        self.font_mono = pygame.font.SysFont("consolas", 16)

        self.menu_board_options = []
        self.menu_mode_options = []
        self.menu_callback = None
        self.menu_selected_index = 0
        self.menu_selected_file_name = None
        self.menu_selected_mode = "game"
        self.menu_solver_view = "solution"
        self.menu_source = "file"
        self.menu_random_size = 5
        self.menu_random_toggles = 6
        self.menu_initialized = False

        self.game_board = None
        self.game_board_snapshot = None
        self.game_board_label = ""
        self.game_started_at = 0
        self.game_on_back = None
        self.game_on_solved = None
        self.game_hint_move = None
        self.game_last_move = None
        self.game_auto_play_random = False
        self.game_last_auto_step_at = 0

        self.solver_initial_board = None
        self.solver_current_board = None
        self.solver_board_label = ""
        self.solver_mode = ""
        self.solver_generator = None
        self.solver_playback_mode = "solution"
        self.solver_solution_moves = []
        self.solver_solution_index = 0
        self.solver_result_node = None
        self.solver_compute_time = 0.0
        self.solver_animation_started_at = 0
        self.solver_started_at = 0
        self.solver_last_step_at = 0
        self.solver_last_event = None
        self.solver_last_move = None
        self.solver_frontier = 0
        self.solver_visited = 0
        self.solver_total_visited = 0
        self.solver_depth = 0
        self.solver_on_back = None
        self.solver_on_finished = None

        self.report_title = ""
        self.report_content = ""
        self.report_on_back = None
        self.report_scroll = 0

        self.win_board = None
        self.win_elapsed = 0.0
        self.win_label = ""
        self.win_move_count = 0
        self.win_on_back = None

        self.solver_result_title = ""
        self.solver_result_board = None
        self.solver_result_label = ""
        self.solver_result_mode = ""
        self.solver_result_stats = {}
        self.solver_result_on_back = None

    def _select_menu_board_by_index(self, index):
        if not self.menu_board_options:
            self.menu_selected_index = 0
            self.menu_selected_file_name = None
            return

        self.menu_selected_index = index % len(self.menu_board_options)
        self.menu_selected_file_name = self.menu_board_options[self.menu_selected_index]["name"]

    def _sync_menu_state(self, reset=False):
        if self.menu_board_options:
            if reset or self.menu_selected_file_name is None:
                self._select_menu_board_by_index(0)
            else:
                matching_index = next(
                    (
                        index
                        for index, option in enumerate(self.menu_board_options)
                        if option["name"] == self.menu_selected_file_name
                    ),
                    None,
                )
                if matching_index is None:
                    self._select_menu_board_by_index(min(self.menu_selected_index, len(self.menu_board_options) - 1))
                else:
                    self._select_menu_board_by_index(matching_index)
        else:
            self.menu_selected_index = 0
            self.menu_selected_file_name = None

        available_modes = {mode for _, mode in self.menu_mode_options}
        if reset or self.menu_selected_mode not in available_modes:
            self.menu_selected_mode = self.menu_mode_options[0][1] if self.menu_mode_options else "game"

        if reset or self.menu_source not in {"file", "random"}:
            self.menu_source = "file"

        if reset or self.menu_solver_view not in {"solution", "search"}:
            self.menu_solver_view = "solution"

        default_size = max(3, (self.menu_board_options[0]["size"] or 5)) if self.menu_board_options else 5
        if reset:
            self.menu_random_size = default_size
            self.menu_random_toggles = max(1, self.menu_random_size)
        else:
            self.menu_random_size = max(3, self.menu_random_size)
            self.menu_random_toggles = max(
                1,
                min(self.menu_random_size * self.menu_random_size, self.menu_random_toggles),
            )

    def show_menu(self, board_options, mode_options, on_mode_select):
        self.state = "menu"
        self.menu_board_options = board_options
        self.menu_mode_options = mode_options
        self.menu_callback = on_mode_select
        self._sync_menu_state(reset=not self.menu_initialized)
        self.menu_initialized = True

    def show_game(self, board, board_label, on_back_callback=None, on_solved_callback=None, auto_play_random=False):
        self.state = "game"
        self.game_board = Board(board.matrix, board.size, list(board.moves))
        self.game_board_snapshot = Board(board.matrix, board.size, list(board.moves))
        self.game_board_label = board_label
        self.game_started_at = pygame.time.get_ticks()
        self.game_on_back = on_back_callback
        self.game_on_solved = on_solved_callback
        self.game_hint_move = None
        self.game_last_move = None
        self.game_auto_play_random = auto_play_random
        self.game_last_auto_step_at = self.game_started_at
        self.click_targets = []

    def show_solver(
        self,
        board,
        mode,
        board_label,
        on_back_callback=None,
        on_finished_callback=None,
        playback_mode="solution",
    ):
        self.state = "solver"
        self.solver_initial_board = Board(board.matrix, board.size, list(board.moves))
        self.solver_current_board = Board(board.matrix, board.size, list(board.moves))
        self.solver_board_label = board_label
        self.solver_mode = mode
        self.solver_playback_mode = "solution" if mode == "gf2" else playback_mode
        self.solver_generator = None
        self.solver_solution_moves = []
        self.solver_solution_index = 0
        self.solver_result_node = None
        self.solver_compute_time = 0.0
        self.solver_animation_started_at = 0
        self.solver_started_at = pygame.time.get_ticks()
        self.solver_last_step_at = self.solver_started_at
        self.solver_last_event = None
        self.solver_last_move = None
        self.solver_frontier = 0
        self.solver_visited = 0
        self.solver_total_visited = 0
        self.solver_depth = 0
        self.solver_on_back = on_back_callback
        self.solver_on_finished = on_finished_callback
        self.click_targets = []

        if self.solver_playback_mode == "search":
            self.solver_generator = solver.iter_search(Board(board.matrix, board.size, list(board.moves)), mode)
            return

        board_copy = Board(board.matrix, board.size, list(board.moves))
        if mode == "gf2":
            solved = gf2_solver.solve(board_copy)
        else:
            solved = solver.solve(board_copy, mode)
        if solved:
            _, result_node, elapsed, metrics = solved[0]
            self.solver_result_node = result_node
            self.solver_compute_time = elapsed
            self.solver_total_visited = metrics.get("visited_states", 0)

            if result_node is None:
                if self.solver_on_finished is not None:
                    self.solver_on_finished(None, elapsed, {"visited_states": self.solver_total_visited})
                return

            self.solver_solution_moves = list(result_node.state.moves)
            self.solver_frontier = 0
            self.solver_visited = 0
            self.solver_depth = 0
            self.solver_last_step_at = pygame.time.get_ticks()
            self.solver_animation_started_at = self.solver_last_step_at

    def show_report(self, title, content, on_back_callback=None):
        self.state = "report"
        self.report_title = title
        self.report_content = content
        self.report_on_back = on_back_callback
        self.report_scroll = 0
        self.click_targets = []

    def show_win_screen(self, board, board_label, elapsed_seconds, on_back_callback=None):
        self.state = "win"
        self.win_board = Board(board.matrix, board.size, list(board.moves))
        self.win_elapsed = elapsed_seconds
        self.win_label = board_label
        self.win_move_count = len(board.moves)
        self.win_on_back = on_back_callback
        self.click_targets = []

    def show_solver_result_screen(self, title, board, board_label, mode, stats, on_back_callback=None):
        self.state = "solver_result"
        self.solver_result_title = title
        self.solver_result_board = Board(board.matrix, board.size, list(board.moves))
        self.solver_result_label = board_label
        self.solver_result_mode = mode
        self.solver_result_stats = dict(stats)
        self.solver_result_on_back = on_back_callback
        self.click_targets = []

    def _clear_click_targets(self):
        self.click_targets = []

    def _register_click(self, rect, callback):
        self.click_targets.append((rect, callback))

    def _draw_background(self):
        for y in range(0, self.HEIGHT, 4):
            blend = y / max(1, self.HEIGHT)
            color = tuple(
                int(self.palette["bg_top"][index] * (1 - blend) + self.palette["bg_bottom"][index] * blend)
                for index in range(3)
            )
            pygame.draw.rect(self.screen, color, (0, y, self.WIDTH, 4))

        glow = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow, (92, 141, 255, 46), (self.WIDTH - 140, 130), 170)
        pygame.draw.circle(glow, (90, 214, 190, 36), (150, self.HEIGHT - 110), 160)
        pygame.draw.circle(glow, (255, 215, 96, 20), (self.WIDTH // 2, 110), 110)
        self.screen.blit(glow, (0, 0))

    def _card(self, rect, fill=None):
        fill = fill or self.palette["panel"]
        shadow_rect = rect.move(0, 7)
        pygame.draw.rect(self.screen, self.palette["shadow"], shadow_rect, border_radius=24)
        pygame.draw.rect(self.screen, fill, rect, border_radius=24)
        pygame.draw.rect(self.screen, self.palette["panel_border"], rect, 1, border_radius=24)

    def _text(self, text, font, color, x, y, center=False):
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surface, rect)
        return rect

    def _fit_text(self, text, font, max_width):
        if font.size(text)[0] <= max_width:
            return text

        ellipsis = "..."
        if font.size(ellipsis)[0] > max_width:
            return ""

        trimmed = text
        while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
            trimmed = trimmed[:-1]

        return (trimmed + ellipsis) if trimmed else ellipsis

    def _text_box(self, text, font, color, rect, *, align="left"):
        if rect.width <= 0 or rect.height <= 0:
            return None

        fitted = self._fit_text(text, font, rect.width)
        surface = font.render(fitted, True, color)
        target = surface.get_rect()

        if align == "center":
            target.center = rect.center
        elif align == "right":
            target.midright = rect.midright
        else:
            target.midleft = rect.midleft

        clip = self.screen.get_clip()
        self.screen.set_clip(rect)
        self.screen.blit(surface, target)
        self.screen.set_clip(clip)
        return target

    def _draw_wrapped_text(self, text, font, color, rect, line_spacing=4, align="left"):
        if rect.width <= 0 or rect.height <= 0:
            return 0

        lines = self._wrap_text(text, font, rect.width)
        line_height = font.get_linesize() + line_spacing
        y = rect.y
        drawn_lines = 0
        for line in lines:
            if y + line_height > rect.bottom:
                break
            self._text_box(line, font, color, pygame.Rect(rect.x, y, rect.width, line_height), align=align)
            y += line_height
            drawn_lines += 1

        if drawn_lines == 0:
            return 0

        return y - rect.y

    def _draw_text_list(self, lines, font, color, rect, *, line_spacing=4, item_spacing=6, align="left"):
        y = rect.y
        for line in lines:
            available_height = rect.bottom - y
            if available_height <= 0:
                break

            used_height = self._draw_wrapped_text(
                line,
                font,
                color,
                pygame.Rect(rect.x, y, rect.width, available_height),
                line_spacing=line_spacing,
                align=align,
            )
            if used_height <= 0:
                break
            y += used_height + item_spacing

        return y - rect.y

    def _button(self, rect, text, callback, *, selected=False, accent=False, disabled=False):
        if disabled:
            fill = (43, 51, 70)
            border = (74, 82, 100)
            text_color = (140, 146, 158)
        elif selected:
            fill = self.palette["accent"]
            border = self.palette["accent"]
            text_color = (255, 255, 255)
        elif accent:
            fill = self.palette["panel_alt"]
            border = self.palette["accent_2"]
            text_color = self.palette["text"]
        else:
            fill = self.palette["panel_alt"]
            border = self.palette["panel_border"]
            text_color = self.palette["text"]

        pygame.draw.rect(self.screen, fill, rect, border_radius=16)
        pygame.draw.rect(self.screen, border, rect, 1, border_radius=16)
        label_rect = rect.inflate(-12, -8)
        if label_rect.width <= 0 or label_rect.height <= 0:
            label_rect = rect
        self._text_box(text, self.font_body, text_color, label_rect, align="center")

        if callback is not None and not disabled:
            self._register_click(rect, callback)

    def _small_button(self, rect, text, callback, *, selected=False):
        self._button(rect, text, callback, selected=selected)

    def _wrap_text(self, text, font, width):
        lines = []
        for raw_line in text.splitlines():
            if raw_line == "":
                lines.append("")
                continue

            words = raw_line.split(" ")
            current = ""
            for word in words:
                candidate = word if not current else current + " " + word
                if font.size(candidate)[0] <= width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)

        return lines

    def _draw_scroll_text(self, text, rect, scroll):
        clip = self.screen.get_clip()
        self.screen.set_clip(rect)
        lines = self._wrap_text(text, self.font_mono, rect.width - 28)
        line_height = self.font_mono.get_linesize() + 4
        total_height = max(0, len(lines) * line_height)
        max_scroll = max(0, total_height - rect.height + 18)
        scroll = max(0, min(scroll, max_scroll))

        y = rect.y + 12 - scroll
        for line in lines:
            rendered = self.font_mono.render(line, True, self.palette["text"])
            self.screen.blit(rendered, (rect.x + 14, y))
            y += line_height

        self.screen.set_clip(clip)
        return max_scroll

    def _mode_label(self, mode):
        return self.MODE_LABEL_OVERRIDES.get(mode, mode.upper())

    def _board_metrics(self, board, area):
        padding = 18
        available_w = area.width - padding * 2
        available_h = area.height - padding * 2
        gap = max(1, min(6, available_w // max(1, board.size * 8)))
        cell_size = min(
            (available_w - gap * (board.size - 1)) // board.size,
            (available_h - gap * (board.size - 1)) // board.size,
        )
        cell_size = max(2, cell_size)
        board_w = cell_size * board.size + gap * (board.size - 1)
        board_h = cell_size * board.size + gap * (board.size - 1)
        start_x = area.x + (area.width - board_w) // 2
        start_y = area.y + (area.height - board_h) // 2
        return cell_size, gap, start_x, start_y

    def _draw_board(self, board, area, interactive=False, on_cell_click=None, highlight=None, hint=None):
        self._card(area, fill=self.palette["panel"])
        cell_size, gap, start_x, start_y = self._board_metrics(board, area)
        mouse_pos = pygame.mouse.get_pos()
        last_move = highlight
        hint_move = hint
        clip = self.screen.get_clip()
        inset = area.inflate(-12, -12)
        self.screen.set_clip(inset)

        for row in range(board.size):
            for col in range(board.size):
                value = (board.matrix >> (row * board.size + col)) & 1
                cell_rect = pygame.Rect(
                    start_x + col * (cell_size + gap),
                    start_y + row * (cell_size + gap),
                    cell_size,
                    cell_size,
                )

                fill = self.palette["on"] if value else self.palette["off"]
                border = self.palette["cell_border"]
                if cell_rect.collidepoint(mouse_pos) and interactive:
                    border = self.palette["accent"]

                radius = max(1, min(10, cell_size // 3))
                pygame.draw.rect(self.screen, fill, cell_rect, border_radius=radius)
                pygame.draw.rect(self.screen, border, cell_rect, 2, border_radius=radius)

                if last_move is not None and (row, col) == last_move:
                    pygame.draw.rect(self.screen, self.palette["accent_2"], cell_rect.inflate(8, 8), 3, border_radius=radius + 2)

                if hint_move is not None and (row, col) == hint_move:
                    pygame.draw.rect(self.screen, self.palette["warning"], cell_rect.inflate(14, 14), 3, border_radius=radius + 4)

                if interactive and on_cell_click is not None:
                    self._register_click(cell_rect, lambda r=row, c=col: on_cell_click(r, c))

            self.screen.set_clip(clip)

    def _menu_config(self):
        if self.menu_source == "random":
            return {
                "source": "random",
                "size": self.menu_random_size,
                "toggles": self.menu_random_toggles,
                "mode": self.menu_selected_mode,
                "solver_view": self.menu_solver_view,
            }

        selected = self.menu_board_options[self.menu_selected_index]
        return {
            "source": "file",
            "file_name": selected["name"],
            "mode": self.menu_selected_mode,
            "solver_view": self.menu_solver_view,
        }

    def _launch_menu_selection(self):
        if self.menu_callback is not None:
            self.menu_callback(self._menu_config())

    def _adjust_menu_size(self, delta):
        self.menu_random_size = max(3,self.menu_random_size + delta)
        self.menu_random_toggles = max(1, min(self.menu_random_size * self.menu_random_size, self.menu_random_toggles))

    def _adjust_menu_toggles(self, delta):
        self.menu_random_toggles = max(
            1,
            min(self.menu_random_size * self.menu_random_size, self.menu_random_toggles + delta),
        )

    def _advance_solver_step(self):
        if self.solver_playback_mode == "solution":
            if self.solver_result_node is None:
                return

            if self.solver_solution_index >= len(self.solver_solution_moves):
                if self.solver_on_finished is not None:
                    self.solver_on_finished(
                        self.solver_result_node,
                        self.solver_compute_time,
                        {"visited_states": self.solver_total_visited},
                    )
                self.solver_result_node = None
                return

            move = self.solver_solution_moves[self.solver_solution_index]
            self.solver_current_board.toggle(move[0], move[1])
            self.solver_last_move = move
            self.solver_solution_index += 1
            self.solver_depth = self.solver_solution_index
            self.solver_visited = self.solver_solution_index
            self.solver_frontier = max(0, len(self.solver_solution_moves) - self.solver_solution_index)
            return

        if self.solver_generator is None:
            return

        try:
            event = next(self.solver_generator)
        except StopIteration as stop:
            result_node = stop.value
            elapsed = (pygame.time.get_ticks() - self.solver_started_at) / 1000.0
            self.solver_generator = None
            if self.solver_on_finished is not None:
                self.solver_on_finished(result_node, elapsed, {"visited_states": self.solver_visited})
            return

        self.solver_last_event = event
        node = event["node"]
        self.solver_current_board = node.state
        self.solver_last_move = event["last_move"]
        self.solver_frontier = event["frontier"]
        self.solver_visited = event["visited"]
        self.solver_depth = event["depth"]

        if event["kind"] == "solution":
            try:
                next(self.solver_generator)
            except StopIteration as stop:
                result_node = stop.value
                elapsed = (pygame.time.get_ticks() - self.solver_started_at) / 1000.0
                self.solver_generator = None
                if self.solver_on_finished is not None:
                    self.solver_on_finished(result_node, elapsed, {"visited_states": self.solver_visited})

    def _advance_random_game_step(self):
        if self.game_board is None or self.game_board.is_solved():
            return

        row = random.randrange(self.game_board.size)
        col = random.randrange(self.game_board.size)
        self._click_game_cell(row, col)

    def _handle_click(self, pos):
        for rect, callback in reversed(self.click_targets):
            if rect.collidepoint(pos):
                callback()
                return True
        return False

    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._launch_menu_selection()
                return True
            if event.key == pygame.K_ESCAPE:
                self.running = False
                return True
        return False

    def _handle_game_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and self.game_on_back is not None:
                self.game_on_back()
                return True
            if event.key == pygame.K_r:
                self._reset_game_board()
                return True
        return False

    def _handle_solver_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.solver_on_back is not None:
            self.solver_on_back()
            return True
        return False

    def _handle_report_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and self.report_on_back is not None:
                self.report_on_back()
                return True
            if event.key == pygame.K_UP:
                self.report_scroll = max(0, self.report_scroll - 40)
                return True
            if event.key == pygame.K_DOWN:
                self.report_scroll += 40
                return True
        if event.type == pygame.MOUSEWHEEL:
            self.report_scroll = max(0, self.report_scroll - event.y * 36)
            return True
        return False

    def _draw_top_header(self, title, subtitle=None):
        self._text(title, self.font_title, self.palette["text"], 44, 28)
        if subtitle:
            subtitle_rect = pygame.Rect(46, 76, self.WIDTH - 92, 28)
            self._text_box(subtitle, self.font_body, self.palette["muted"], subtitle_rect)

    def _draw_menu(self):
        self._draw_background()
        self._clear_click_targets()
        self._draw_top_header("Lights Out", "Choose a board, set the size, and launch the mode you want.")

        left = pygame.Rect(36, 122, 520, 680)
        right = pygame.Rect(572, 122, 672, 680)
        self._card(left)
        self._card(right)

        self._text("Board Source", self.font_heading, self.palette["text"], left.x + 24, left.y + 20)
        self._text("Algorithm", self.font_heading, self.palette["text"], right.x + 24, right.y + 20)

        file_button = pygame.Rect(left.x + 24, left.y + 58, 130, 34)
        random_button = pygame.Rect(left.x + 164, left.y + 58, 132, 34)
        self._button(file_button, "Input File", lambda: setattr(self, "menu_source", "file"), selected=self.menu_source == "file")
        self._button(random_button, "Random Board", lambda: setattr(self, "menu_source", "random"), selected=self.menu_source == "random")

        if self.menu_source == "file":
            selected = self.menu_board_options[self.menu_selected_index]
            self._text("Selected board", self.font_small, self.palette["muted"], left.x + 24, left.y + 112)
            self._draw_wrapped_text(
                selected["label"],
                self.font_body,
                self.palette["text"],
                pygame.Rect(left.x + 24, left.y + 136, left.width - 48, 44),
                line_spacing=2,
            )

            prev_rect = pygame.Rect(left.x + 24, left.y + 180, 42, 38)
            next_rect = pygame.Rect(left.x + 454, left.y + 180, 42, 38)
            self._button(prev_rect, "<", lambda: self._select_menu_board_by_index(self.menu_selected_index - 1))
            self._button(next_rect, ">", lambda: self._select_menu_board_by_index(self.menu_selected_index + 1))

            preview_rect = pygame.Rect(left.x + 84, left.y + 170, 350, 260)
            try:
                preview_board = Board.from_txt(selected["path"])
                self._draw_board(preview_board, preview_rect, interactive=False)
            except Exception as exc:
                self._card(preview_rect, fill=self.palette["panel_alt"])
                self._text_box(
                    "Preview unavailable",
                    self.font_heading,
                    self.palette["danger"],
                    pygame.Rect(preview_rect.x + 16, preview_rect.y + 18, preview_rect.width - 32, 28),
                    align="center",
                )
                self._draw_wrapped_text(
                    str(exc),
                    self.font_small,
                    self.palette["muted"],
                    pygame.Rect(preview_rect.x + 18, preview_rect.y + 58, preview_rect.width - 36, preview_rect.height - 76),
                    line_spacing=2,
                )

            self._draw_text_list(
                [
                    "Use the arrows to move between input boards.",
                    "The board label includes its size.",
                ],
                self.font_small,
                self.palette["muted"],
                pygame.Rect(left.x + 24, left.y + 448, left.width - 48, 52),
                line_spacing=2,
                item_spacing=4,
            )
        else:
            self._text("Board size", self.font_small, self.palette["muted"], left.x + 24, left.y + 112)
            size_value = pygame.Rect(left.x + 24, left.y + 134, 170, 56)
            self._card(size_value, fill=self.palette["panel_alt"])
            self._text(f"{self.menu_random_size} x {self.menu_random_size}", self.font_heading, self.palette["text"], size_value.centerx, size_value.centery - 8, center=True)
            minus_size = pygame.Rect(left.x + 204, left.y + 143, 38, 38)
            plus_size = pygame.Rect(left.x + 246, left.y + 143, 38, 38)
            self._button(minus_size, "-", lambda: self._adjust_menu_size(-1))
            self._button(plus_size, "+", lambda: self._adjust_menu_size(1))

            self._text("Random toggles", self.font_small, self.palette["muted"], left.x + 24, left.y + 210)
            toggles_value = pygame.Rect(left.x + 24, left.y + 232, 170, 56)
            self._card(toggles_value, fill=self.palette["panel_alt"])
            self._text(str(self.menu_random_toggles), self.font_heading, self.palette["text"], toggles_value.centerx, toggles_value.centery - 8, center=True)
            minus_toggles = pygame.Rect(left.x + 204, left.y + 241, 38, 38)
            plus_toggles = pygame.Rect(left.x + 246, left.y + 241, 38, 38)
            self._button(minus_toggles, "-", lambda: self._adjust_menu_toggles(-1))
            self._button(plus_toggles, "+", lambda: self._adjust_menu_toggles(1))

            preview_rect = pygame.Rect(left.x + 24, left.y + 306, 440, 250)
            preview_seed = self.menu_random_size * 1000 + self.menu_random_toggles
            preview_board = Board.random_board(self.menu_random_size, self.menu_random_toggles, rng=random.Random(preview_seed))
            self._draw_board(preview_board, preview_rect, interactive=False)

            self._draw_text_list(
                [
                    "This board is generated from a clean board, so it is always solvable.",
                    "Use the toggle count to tune the puzzle intensity.",
                ],
                self.font_small,
                self.palette["muted"],
                pygame.Rect(left.x + 24, left.y + 580, left.width - 48, 58),
                line_spacing=2,
                item_spacing=4,
            )

        mode_area = pygame.Rect(right.x + 24, right.y + 58, right.width - 48, 470)
        cols = 2
        gap_x = 14
        gap_y = 14
        button_w = (mode_area.width - gap_x) // cols
        button_h = 70

        for index, (label, mode) in enumerate(self.menu_mode_options):
            row = index // cols
            col = index % cols
            button_rect = pygame.Rect(
                mode_area.x + col * (button_w + gap_x),
                mode_area.y + row * (button_h + gap_y),
                button_w,
                button_h,
            )
            self._button(
                button_rect,
                label,
                lambda selected_mode=mode: setattr(self, "menu_selected_mode", selected_mode),
                selected=self.menu_selected_mode == mode,
            )

        note_rect = pygame.Rect(right.x + 24, right.y + 392, right.width - 48, 124)
        self._card(note_rect, fill=self.palette["panel_alt"])
        self._text("Solver playback", self.font_heading, self.palette["text"], note_rect.x + 18, note_rect.y + 12)
        solution_mode_rect = pygame.Rect(note_rect.x + 18, note_rect.y + 42, 190, 34)
        search_mode_rect = pygame.Rect(note_rect.x + 216, note_rect.y + 42, 190, 34)
        self._button(
            solution_mode_rect,
            "Final Path",
            lambda: setattr(self, "menu_solver_view", "solution"),
            selected=self.menu_solver_view == "solution",
        )
        self._button(
            search_mode_rect,
            "Every Expanded Node",
            lambda: setattr(self, "menu_solver_view", "search"),
            selected=self.menu_solver_view == "search",
        )
        self._draw_wrapped_text(
            "Final Path: solve first, then animate only the winning moves. Every Expanded Node: show full search process at 500 ms.",
            self.font_small,
            self.palette["muted"],
            pygame.Rect(note_rect.x + 18, note_rect.y + 82, note_rect.width - 36, 40),
            line_spacing=1,
        )

        launch_rect = pygame.Rect(right.x + 24, right.bottom - 82, right.width - 48, 52)
        self._button(launch_rect, "Launch", self._launch_menu_selection, accent=True)

        footer = "Use Enter to launch and Esc to close."
        self._text(footer, self.font_small, self.palette["muted"], 44, self.HEIGHT - 30)

    def _draw_game(self):
        self._draw_background()
        self._clear_click_targets()
        title = "Random Player" if self.game_auto_play_random else "Play Mode"
        self._draw_top_header(title, self.game_board_label)

        board_area = pygame.Rect(36, 120, 786, 686)
        side_area = pygame.Rect(846, 120, 398, 686)
        self._draw_board(
            self.game_board,
            board_area,
            interactive=not self.game_auto_play_random,
            on_cell_click=None if self.game_auto_play_random else self._click_game_cell,
            highlight=self.game_last_move,
            hint=None if self.game_auto_play_random else self.game_hint_move,
        )
        self._card(side_area)

        self._text("Status", self.font_heading, self.palette["text"], side_area.x + 24, side_area.y + 20)
        elapsed = (pygame.time.get_ticks() - self.game_started_at) / 1000.0
        if self.game_auto_play_random:
            status_lines = [
                "Mode: Random autoplay",
                f"Moves: {len(self.game_board.moves)}",
                f"Board: {self.game_board.size} x {self.game_board.size}",
                f"Elapsed: {elapsed:.1f}s",
                f"Solved: {'yes' if self.game_board.is_solved() else 'no'}",
            ]
        else:
            status_lines = [
                f"Moves: {len(self.game_board.moves)}",
                f"Board: {self.game_board.size} x {self.game_board.size}",
                f"Elapsed: {elapsed:.1f}s",
                f"Solved: {'yes' if self.game_board.is_solved() else 'no'}",
                f"Hint: {self.game_hint_move if self.game_hint_move is not None else '-'}",
            ]

        status_box = pygame.Rect(side_area.x + 20, side_area.y + 58, side_area.width - 40, 164)
        self._card(status_box, fill=self.palette["panel_alt"])
        self._draw_text_list(
            status_lines,
            self.font_body,
            self.palette["text"],
            pygame.Rect(status_box.x + 18, status_box.y + 18, status_box.width - 36, status_box.height - 36),
            line_spacing=2,
            item_spacing=6,
        )

        action_box = pygame.Rect(side_area.x + 20, side_area.y + 244, side_area.width - 40, 230)
        self._card(action_box, fill=self.palette["panel_alt"])
        self._text("Controls", self.font_heading, self.palette["text"], action_box.x + 18, action_box.y + 16)
        if self.game_auto_play_random:
            control_lines = [
                "The random player presses one tile every 500 ms.",
                "Press R to restart the same board.",
                "Press Esc to go back to the menu.",
                "Watch the highlighted tile to follow each move.",
            ]
        else:
            control_lines = [
                "Click any tile to toggle it and its neighbors.",
                "Press R to reset the board.",
                "Press Esc to go back to the menu.",
                "Press Hint to highlight the next A* move.",
            ]

        self._draw_text_list(
            control_lines,
            self.font_small,
            self.palette["muted"],
            pygame.Rect(action_box.x + 18, action_box.y + 54, action_box.width - 36, 106),
            line_spacing=2,
            item_spacing=6,
        )

        hint_rect = pygame.Rect(action_box.x + 18, action_box.y + 170, action_box.width - 36, 44)
        if self.game_auto_play_random:
            self._button(hint_rect, "Random Player Active", None, disabled=True)
        else:
            self._button(hint_rect, "Hint", self._compute_hint, accent=True)

        back_rect = pygame.Rect(side_area.x + 20, side_area.bottom - 74, 150, 50)
        reset_rect = pygame.Rect(side_area.right - 170, side_area.bottom - 74, 150, 50)
        self._button(back_rect, "Back", self.game_on_back)
        self._button(reset_rect, "Reset", self._reset_game_board)

    def _click_game_cell(self, row, col):
        if self.game_board is None:
            return

        self.game_board.toggle(row, col)
        self.game_hint_move = None
        self.game_last_move = (row, col)
        self.game_started_at = self.game_started_at if self.game_started_at else pygame.time.get_ticks()

        if self.game_board.is_solved() and self.game_on_solved is not None:
            elapsed = (pygame.time.get_ticks() - self.game_started_at) / 1000.0
            self.game_on_solved(self.game_board, elapsed)

    def _draw_win(self):
        self._draw_background()
        self._clear_click_targets()
        self._draw_top_header("Victory", "Board solved successfully")

        main_rect = pygame.Rect(120, 140, 1040, 640)
        self._card(main_rect)

        left = pygame.Rect(main_rect.x + 24, main_rect.y + 24, 620, main_rect.height - 48)
        right = pygame.Rect(main_rect.x + 662, main_rect.y + 24, 354, main_rect.height - 48)

        if self.win_board is not None:
            self._draw_board(self.win_board, left, interactive=False)

        self._card(right, fill=self.palette["panel_alt"])
        self._text("Winning Summary", self.font_heading, self.palette["text"], right.x + 16, right.y + 16)
        self._text_box(
            self.win_label,
            self.font_small,
            self.palette["muted"],
            pygame.Rect(right.x + 16, right.y + 52, right.width - 32, 24),
        )

        stats = [
            f"Solved in: {self.win_elapsed:.3f}s",
            f"Moves: {self.win_move_count}",
            f"Board: {self.win_board.size} x {self.win_board.size}" if self.win_board else "Board: -",
        ]
        self._draw_text_list(
            stats,
            self.font_body,
            self.palette["text"],
            pygame.Rect(right.x + 16, right.y + 98, right.width - 32, 108),
            line_spacing=2,
            item_spacing=8,
        )

        message_rect = pygame.Rect(right.x + 16, right.y + 230, right.width - 32, 120)
        self._draw_wrapped_text(
            "Great job. You cleared all lights. Return to the menu to try another map or launch a search algorithm.",
            self.font_body,
            self.palette["muted"],
            message_rect,
            line_spacing=5,
        )

        back_rect = pygame.Rect(right.x + 16, right.bottom - 66, 150, 46)
        close_rect = pygame.Rect(right.right - 166, right.bottom - 66, 150, 46)
        self._button(back_rect, "Back", self.win_on_back)
        self._button(close_rect, "Close", self._close_window, accent=True)

    def _reset_game_board(self):
        if self.game_board_snapshot is None:
            return
        self.game_board = Board(
            self.game_board_snapshot.matrix,
            self.game_board_snapshot.size,
            list(self.game_board_snapshot.moves),
        )
        self.game_hint_move = None
        self.game_started_at = pygame.time.get_ticks()
        self.game_last_move = None
        self.game_last_auto_step_at = self.game_started_at

    def _compute_hint(self):
        if self.game_board is None or self.game_board.is_solved():
            self.game_hint_move = None
            return

        current_moves = len(self.game_board.moves)
        board_copy = Board(self.game_board.matrix, self.game_board.size, list(self.game_board.moves))
        solved = solver.solve(board_copy, "astar")

        if not solved:
            self.game_hint_move = None
            return

        _, result_node, _, _ = solved[0]
        if result_node is None:
            self.game_hint_move = None
            return

        solution_moves = result_node.state.moves
        if len(solution_moves) <= current_moves:
            self.game_hint_move = None
            return

        self.game_hint_move = solution_moves[current_moves]

    def _draw_solver(self):
        self._draw_background()
        self._clear_click_targets()
        playback_label = "Final Path" if self.solver_playback_mode == "solution" else "Every Expanded Node"
        self._draw_top_header("Solver View", f"{self._mode_label(self.solver_mode)} - {self.solver_board_label} - {playback_label}")

        board_area = pygame.Rect(36, 120, 786, 686)
        side_area = pygame.Rect(846, 120, 398, 686)
        self._draw_board(self.solver_current_board, board_area, interactive=False, highlight=self.solver_last_move)
        self._card(side_area)

        self._text("Search progress", self.font_heading, self.palette["text"], side_area.x + 24, side_area.y + 20)
        elapsed = (pygame.time.get_ticks() - self.solver_started_at) / 1000.0
        shown_elapsed = self.solver_compute_time if self.solver_playback_mode == "solution" else elapsed
        shown_visited = self.solver_total_visited if self.solver_playback_mode == "solution" else self.solver_visited

        status_box = pygame.Rect(side_area.x + 20, side_area.y + 58, side_area.width - 40, 210)
        self._card(status_box, fill=self.palette["panel_alt"])
        details = [
            f"Solve time: {shown_elapsed:.3f}s",
            f"Depth: {self.solver_depth}",
            f"Frontier: {self.solver_frontier}",
            f"Visited: {shown_visited}",
            f"Last move: {self.solver_last_move if self.solver_last_move is not None else '-'}",
        ]
        self._draw_text_list(
            details,
            self.font_body,
            self.palette["text"],
            pygame.Rect(status_box.x + 18, status_box.y + 18, status_box.width - 36, status_box.height - 36),
            line_spacing=2,
            item_spacing=6,
        )

        info_box = pygame.Rect(side_area.x + 20, side_area.y + 286, side_area.width - 40, 124)
        self._card(info_box, fill=self.palette["panel_alt"])
        if self.solver_playback_mode == "solution":
            info_lines = [
                "Algorithm runs first, then only the final move sequence is shown.",
                "Playback step interval: 500 ms per move.",
                "Report opens after the final solution move.",
            ]
        else:
            info_lines = [
                "This screen advances one search expansion every 500 ms.",
                "The last expanded node stays highlighted on the board.",
                "When the solution is found, the final report opens automatically.",
            ]
        self._draw_text_list(
            info_lines,
            self.font_small,
            self.palette["muted"],
            pygame.Rect(info_box.x + 18, info_box.y + 18, info_box.width - 36, info_box.height - 32),
            line_spacing=2,
            item_spacing=4,
        )

        back_rect = pygame.Rect(side_area.x + 20, side_area.bottom - 74, 150, 50)
        stop_rect = pygame.Rect(side_area.right - 170, side_area.bottom - 74, 150, 50)
        self._button(back_rect, "Back", self.solver_on_back)
        self._button(stop_rect, "Pause", None, disabled=True)

    def _draw_solver_result(self):
        self._draw_background()
        self._clear_click_targets()
        self._draw_top_header(self.solver_result_title, self.solver_result_label)

        board_area = pygame.Rect(36, 120, 786, 686)
        side_area = pygame.Rect(846, 120, 398, 686)

        if self.solver_result_board is not None:
            self._draw_board(self.solver_result_board, board_area, interactive=False)

        self._card(side_area)
        self._text("Solver Summary", self.font_heading, self.palette["text"], side_area.x + 24, side_area.y + 20)

        time_taken = self.solver_result_stats.get("time", 0.0)
        visited_states = self.solver_result_stats.get("visited_states", 0)
        move_count = self.solver_result_stats.get("moves", 0)
        solved = self.solver_result_stats.get("solved", True)

        status_box = pygame.Rect(side_area.x + 20, side_area.y + 58, side_area.width - 40, 210)
        self._card(status_box, fill=self.palette["panel_alt"])
        lines = [
            f"Algorithm: {self._mode_label(self.solver_result_mode)}",
            f"Execution: {time_taken:.3f}s",
            f"Visited states: {visited_states}",
            f"Outcome: {'Solved' if solved else 'No solution'}",
            f"{'Moves in solution' if solved else 'Moves attempted'}: {move_count}",
        ]
        self._draw_text_list(
            lines,
            self.font_body,
            self.palette["text"],
            pygame.Rect(status_box.x + 18, status_box.y + 18, status_box.width - 36, status_box.height - 36),
            line_spacing=2,
            item_spacing=8,
        )

        msg_rect = pygame.Rect(side_area.x + 20, side_area.y + 286, side_area.width - 40, 124)
        self._card(msg_rect, fill=self.palette["panel_alt"])
        self._draw_wrapped_text(
            (
                "Search completed. Use Back to try another board or algorithm."
                if solved
                else "No solution was found within the algorithm limit. Use Back to try another board or algorithm."
            ),
            self.font_body,
            self.palette["muted"],
            pygame.Rect(msg_rect.x + 16, msg_rect.y + 18, msg_rect.width - 32, msg_rect.height - 20),
            line_spacing=4,
        )

        back_rect = pygame.Rect(side_area.x + 20, side_area.bottom - 74, 150, 50)
        close_rect = pygame.Rect(side_area.right - 170, side_area.bottom - 74, 150, 50)
        self._button(back_rect, "Back", self.solver_result_on_back)
        self._button(close_rect, "Close", self._close_window, accent=True)

    def _draw_report(self):
        self._draw_background()
        self._clear_click_targets()
        self._draw_top_header(self.report_title, "Scroll the report with the mouse wheel or the arrow keys.")

        report_area = pygame.Rect(36, 120, 1208, 640)
        self._card(report_area)

        title_box = pygame.Rect(report_area.x + 22, report_area.y + 18, report_area.width - 44, 60)
        self._card(title_box, fill=self.palette["panel_alt"])
        self._draw_wrapped_text(
            self.report_title,
            self.font_heading,
            self.palette["text"],
            pygame.Rect(title_box.x + 18, title_box.y + 14, title_box.width - 36, title_box.height - 20),
            line_spacing=2,
        )

        text_box = pygame.Rect(report_area.x + 22, report_area.y + 94, report_area.width - 44, 500)
        self._card(text_box, fill=self.palette["panel_alt"])
        max_scroll = self._draw_scroll_text(self.report_content, text_box, self.report_scroll)
        self.report_scroll = max(0, min(self.report_scroll, max_scroll))

        back_rect = pygame.Rect(report_area.x + 22, report_area.bottom - 72, 150, 50)
        close_rect = pygame.Rect(report_area.right - 172, report_area.bottom - 72, 150, 50)
        self._button(back_rect, "Back", self.report_on_back)
        self._button(close_rect, "Close", self._close_window, accent=True)

    def _close_window(self):
        self.running = False

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._handle_click(event.pos):
                        continue

                if self.state == "menu":
                    if self._handle_menu_event(event):
                        continue
                elif self.state == "game":
                    if self._handle_game_event(event):
                        continue
                elif self.state == "solver":
                    if self._handle_solver_event(event):
                        continue
                elif self.state == "report":
                    if self._handle_report_event(event):
                        continue
                elif self.state == "win":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.win_on_back is not None:
                        self.win_on_back()
                        continue
                elif self.state == "solver_result":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.solver_result_on_back is not None:
                        self.solver_result_on_back()
                        continue

                if event.type == pygame.MOUSEWHEEL and self.state == "report":
                    self._handle_report_event(event)

            should_advance_solver = (
                self.state == "solver"
                and (
                    self.solver_generator is not None
                    or (
                        self.solver_playback_mode == "solution"
                        and self.solver_result_node is not None
                    )
                )
            )

            if should_advance_solver:
                now = pygame.time.get_ticks()
                if now - self.solver_last_step_at >= self.SOLVER_STEP_MS:
                    self.solver_last_step_at = now
                    self._advance_solver_step()

            should_advance_random_game = (
                self.state == "game"
                and self.game_auto_play_random
                and self.game_board is not None
                and not self.game_board.is_solved()
            )

            if should_advance_random_game:
                now = pygame.time.get_ticks()
                if now - self.game_last_auto_step_at >= self.GAME_AUTO_STEP_MS:
                    self.game_last_auto_step_at = now
                    self._advance_random_game_step()

            if self.state == "menu":
                self._draw_menu()
            elif self.state == "game":
                self._draw_game()
            elif self.state == "solver":
                self._draw_solver()
            elif self.state == "report":
                self._draw_report()
            elif self.state == "win":
                self._draw_win()
            elif self.state == "solver_result":
                self._draw_solver_result()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
