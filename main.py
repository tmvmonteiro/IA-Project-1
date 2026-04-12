from functools import partial
from pathlib import Path
import sys
import time

from src import solver
from src.app_runner import build_board_options, launch_mode_selector, resolve_input_path
from src.board import Board


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
TK_UI_ALIASES = {"tk", "tkinter", "legacy"}


def get_grid_from_mask(logic_board):
    """Convert the integer bitmask board into a 2D grid for UI rendering."""
    size = logic_board.size
    return [
        [(logic_board.matrix >> (r * size + c)) & 1 for c in range(size)]
        for r in range(size)
    ]


def create_window(ui_backend, on_click_callback=None):
    if ui_backend == "tk":
        from src.window import Window as TkWindow

        return TkWindow(on_click_callback=on_click_callback)

    from src.pygame_window import Window as PygameWindow

    return PygameWindow(on_click_callback=on_click_callback)


def parse_cli_args(argv):
    args = list(argv[1:])
    ui_backend = "pygame"

    if args and args[0].lower() in TK_UI_ALIASES:
        ui_backend = "tk"
        args = args[1:]

    return ui_backend, args


def handle_ui_click(r, c, logic_board, ui_window):
    logic_board.toggle(r, c)

    if hasattr(ui_window, "moves"):
        ui_window.moves += 1

    if hasattr(ui_window, "draw"):
        ui_window.draw(get_grid_from_mask(logic_board))

    if logic_board.is_solved():
        if hasattr(ui_window, "state") and hasattr(ui_window, "draw_win"):
            ui_window.state = "win"
            ui_window.draw()
        elif hasattr(ui_window, "root"):
            ui_window.root.destroy()


def print_solution(solutions, initial_logic_board):
    size = initial_logic_board.size
    matrix_str = ""
    for r in range(size):
        row = [(initial_logic_board.matrix >> (r * size + c)) & 1 for c in range(size)]
        matrix_str += " ".join(map(str, row)) + "\n"

    print("=== REPORT ===\n")
    print(f"INITIAL MATRIX ({size}x{size}):")
    print(matrix_str)
    print("-" * 30 + "\n")

    for entry in solutions:
        if len(entry) == 4:
            algorithm, result, time_taken, metrics = entry
        else:
            algorithm, result, time_taken = entry
            metrics = {}

        print(f"Algorithm:           {algorithm.upper()}")
        print(f"Time:                {time_taken:.7f} seconds")
        print(f"Visited States:      {metrics.get('visited_states', '-')}")
        if result is not None:
            print(f"Board Size:          {result.state.size}x{result.state.size}")
            print(f"Number of Movements: {len(result.state.moves)}")
            print(f"Sequence:            {result.state.moves}")
        else:
            print("Result:              No solution found")
        print("-" * 30 + "\n")


def to_txt(solutions, file_name, initial_logic_board):
    OUTPUT_DIR.mkdir(exist_ok=True)
    report_stem = Path(file_name).stem if file_name else "results"
    file_path = OUTPUT_DIR / f"results_{report_stem}.txt"

    size = initial_logic_board.size
    matrix_str = ""
    for r in range(size):
        row = [(initial_logic_board.matrix >> (r * size + c)) & 1 for c in range(size)]
        matrix_str += " ".join(map(str, row)) + "\n"

    with open(file_path, mode="w", encoding="utf-8") as file_handle:
        file_handle.write("=== REPORT ===\n\n")
        file_handle.write(f"INITIAL MATRIX ({size}x{size}):\n")
        file_handle.write(matrix_str)
        file_handle.write("-" * 30 + "\n")

        for entry in solutions:
            if len(entry) == 4:
                algorithm, result, time_taken, metrics = entry
            else:
                algorithm, result, time_taken = entry
                metrics = {}

            file_handle.write(f"Algorithm:           {algorithm.upper()}\n")
            file_handle.write(f"Time:                {time_taken:.7f} seconds\n")
            file_handle.write(f"Visited States:      {metrics.get('visited_states', '-')}\n")
            if result is not None:
                file_handle.write(f"Board Size:          {result.state.size}x{result.state.size}\n")
                file_handle.write(f"Number of Movements: {len(result.state.moves)}\n")
                file_handle.write(f"Sequence:            {result.state.moves}\n")
            else:
                file_handle.write("Result:              No solution found\n")
            file_handle.write("-" * 30 + "\n")


def read_board(file_name):
    input_path = resolve_input_path(file_name)
    return Board.from_txt(str(input_path)), input_path.name


def load_board(file_name):
    try:
        return read_board(file_name)
    except Exception as exc:
        if file_name is None:
            print(f"Error: Failed to load default board.\nDetails: {exc}")
        else:
            print(f"Error: Failed to load board from '{file_name}'.\nDetails: {exc}")
        sys.exit(1)


def run_tk_menu():
    board_options = build_board_options()
    if not board_options:
        print("Error: No input files found in 'input'.")
        return

    ui_window = create_window("tk", on_click_callback=None)

    def prepare_tk_game(file_name):
        try:
            logic_board, _ = read_board(file_name)
        except Exception as exc:
            print(f"Error: Failed to load board from '{file_name}'.\nDetails: {exc}")
            return False

        ui_window.on_click_callback = partial(
            handle_ui_click,
            logic_board=logic_board,
            ui_window=ui_window,
        )
        ui_window.current_matrix = get_grid_from_mask(logic_board)
        return True

    ui_window.configure_board_options(board_options, prepare_tk_game)
    ui_window.draw()
    ui_window.run()


def run_game_mode(ui_backend, logic_board, file_name):
    ui_window = create_window(ui_backend, on_click_callback=None)

    if hasattr(ui_window, "show_game"):
        def show_game_report(solved_board, elapsed_seconds):
            game_result = type("Result", (), {"state": solved_board})()
            solutions_local = [("game", game_result, elapsed_seconds, {})]
            print_solution(solutions_local, solved_board)
            to_txt(solutions_local, file_name, solved_board)

        ui_window.show_game(
            logic_board,
            f"{file_name} ({logic_board.size}x{logic_board.size})",
            on_solved_callback=show_game_report,
        )
        ui_window.run()
        return

    ui_window.on_click_callback = partial(
        handle_ui_click,
        logic_board=logic_board,
        ui_window=ui_window,
    )
    ui_window.draw(get_grid_from_mask(logic_board))

    start_time = time.time()
    ui_window.run()
    end_time = time.time()
    if logic_board.is_solved():
        print(f"Board solved in {end_time - start_time} seconds.\n")


def main():
    ui_backend, args = parse_cli_args(sys.argv)

    if args:
        game_mode = args[0]
        file_name = args[1] if len(args) > 1 else None
        logic_board, resolved_name = load_board(file_name)

        if game_mode == "game":
            run_game_mode(ui_backend, logic_board, resolved_name)
            return

        solutions = solver.solve(logic_board, game_mode)
        print_solution(solutions, logic_board)
        to_txt(solutions, resolved_name, logic_board)
        return

    if ui_backend == "tk":
        run_tk_menu()
        return

    ui_window = create_window(ui_backend, on_click_callback=None)
    launch_mode_selector(ui_window, print_solution, to_txt)


if __name__ == "__main__":
    main()
