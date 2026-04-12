from pathlib import Path
import re

from src.board import Board


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
MODE_OPTIONS = [
    ("Play", "game"),
    ("BFS", "bfs"),
    ("UCS", "ucs"),
    ("Greedy", "greedy"),
    ("A*", "astar"),
    ("Weighted A*", "wastar"),
]
MODE_LABELS = {mode: label for label, mode in MODE_OPTIONS}


def natural_sort_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def build_board_options():
    options = []
    files = sorted((path.name for path in INPUT_DIR.glob("*.txt")), key=natural_sort_key)

    for file_name in files:
        path = INPUT_DIR / file_name
        try:
            size = Board.from_csv(str(path)).size
        except Exception:
            size = None

        label = f"{file_name} ({size}x{size})" if size else file_name
        options.append({
            "label": label,
            "name": file_name,
            "path": str(path),
            "size": size,
        })

    return options


def resolve_input_path(file_name):
    if file_name is None:
        candidates = [INPUT_DIR / "example1.txt", INPUT_DIR / "example.txt"]
    else:
        raw_path = Path(file_name)
        candidates = [raw_path]
        if not raw_path.is_absolute():
            candidates.append(INPUT_DIR / raw_path)
        if raw_path.suffix == "":
            txt_path = raw_path.with_suffix(".txt")
            candidates.append(txt_path)
            if not txt_path.is_absolute():
                candidates.append(INPUT_DIR / txt_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if file_name is None:
        raise FileNotFoundError("No default input file found in input directory.")
    raise FileNotFoundError(f"Could not find input file '{file_name}'.")


def launch_mode_selector(ui_window, print_solution, to_txt):
    board_options = build_board_options()
    if not board_options:
        print(f"Error: No input files found in '{INPUT_DIR}'.")
        return 1

    def show_menu():
        ui_window.show_menu(board_options, MODE_OPTIONS, start_selected_mode)

    def start_selected_mode(config):
        try:
            if config["source"] == "random":
                board_size = int(config["size"])
                toggle_count = int(config["toggles"])
                logic_board = Board.random_board(board_size, toggle_count)
                board_label = f"Random {board_size}x{board_size} board ({toggle_count} toggles)"
                report_name = f"random_{board_size}x{board_size}.txt"
            else:
                input_path = resolve_input_path(config["file_name"])
                logic_board = Board.from_csv(str(input_path))
                board_label = f"{input_path.name} ({logic_board.size}x{logic_board.size})"
                report_name = input_path.name
        except Exception as exc:
            ui_window.show_report("Error", str(exc), on_back_callback=show_menu)
            return

        if config["mode"] == "game":

            def show_game_report(solved_board, elapsed_seconds):
                game_result = type("Result", (), {"state": solved_board})()
                solutions = [("game", game_result, elapsed_seconds, {})]
                print_solution(solutions, solved_board)
                to_txt(solutions, report_name, solved_board)
                ui_window.show_win_screen(
                    solved_board,
                    board_label,
                    elapsed_seconds,
                    on_back_callback=show_menu,
                )

            ui_window.show_game(
                logic_board,
                board_label,
                on_back_callback=show_menu,
                on_solved_callback=show_game_report,
            )
            return

        def show_solver_report(result_node, elapsed_seconds, stats):
            result_stats = dict(stats)
            result_stats["time"] = elapsed_seconds
            result_stats["moves"] = len(result_node.state.moves) if result_node is not None else 0

            solutions = [(config["mode"], result_node, elapsed_seconds, result_stats)]
            print_solution(solutions, logic_board)
            to_txt(solutions, report_name, logic_board)
            ui_window.show_solver_result_screen(
                f"{MODE_LABELS[config['mode']]} Result",
                result_node.state if result_node is not None else logic_board,
                board_label,
                config["mode"],
                result_stats,
                on_back_callback=show_menu,
            )

        ui_window.show_solver(
            logic_board,
            config["mode"],
            board_label,
            on_back_callback=show_menu,
            on_finished_callback=show_solver_report,
            playback_mode=config.get("solver_view", "solution"),
        )

    show_menu()
    ui_window.run()
    return 0
