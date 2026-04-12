from functools import partial
from pathlib import Path
from src.board import Board
from src.pygame_window import Window
from src import solver
from src.app_runner import launch_mode_selector, resolve_input_path
import time
import sys

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

def get_grid_from_mask(logic_board):
    """Helper to convert integer bitmask back to a 2D list for the UI."""
    size = logic_board.size
    return [[(logic_board.matrix >> (r * size + c)) & 1 
             for c in range(size)] 
            for r in range(size)]


def handle_ui_click(r, c, logic_board, ui_window):
    logic_board.toggle(r, c)
    
    grid = get_grid_from_mask(logic_board)
    if hasattr(ui_window, "draw"):
        ui_window.draw(grid)

    if logic_board.is_solved() and hasattr(ui_window, "root"):
        ui_window.root.destroy()


def print_solution(solutions, initial_logic_board):
    size = initial_logic_board.size
    matrix_str = ""
    for r in range(size):
        row = [(initial_logic_board.matrix >> (r * size + c)) & 1 for c in range(size)]
        matrix_str += " ".join(map(str, row)) + "\n"
    
    print(f"=== REPORT ===\n")
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

    with open(file_path, mode="w", encoding="utf-8") as f:
        f.write("=== REPORT ===\n\n")
        f.write(f"INITIAL MATRIX ({size}x{size}):\n")
        f.write(matrix_str)
        f.write("-" * 30 + "\n")

        for entry in solutions:
            if len(entry) == 4:
                algorithm, result, time_taken, metrics = entry
            else:
                algorithm, result, time_taken = entry
                metrics = {}

            f.write(f"Algorithm:           {algorithm.upper()}\n")
            f.write(f"Time:                {time_taken:.7f} seconds\n")
            f.write(f"Visited States:      {metrics.get('visited_states', '-')}\n")
            if result is not None:
                f.write(f"Board Size:          {result.state.size}x{result.state.size}\n")
                f.write(f"Number of Movements: {len(result.state.moves)}\n")
                f.write(f"Sequence:            {result.state.moves}\n")
            else:
                f.write("Result:              No solution found\n")
            f.write("-" * 30 + "\n")


def main():
    if len(sys.argv) > 1:
        game_mode = sys.argv[1]
        file_name = None
        logic_board = None
        if len(sys.argv) > 2:
            try:
                file_name = sys.argv[2]
                input_path = resolve_input_path(file_name)
                logic_board = Board.from_csv(str(input_path))
                file_name = input_path.name
            except Exception as exc:
                print(f"Error: Failed to load board from '{file_name}'.\nDetails: {exc}")
                sys.exit(1)
        else:
            try:
                input_path = resolve_input_path(None)
                file_name = input_path.name
                logic_board = Board.from_csv(str(input_path))
            except Exception as exc:
                print(f"Error: Failed to load default board.\nDetails: {exc}")
                sys.exit(1)

        solutions = None
        if game_mode == "game":
            ui_window = Window(on_click_callback=None)

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
                ui_window=ui_window
            )

            ui_window.draw(get_grid_from_mask(logic_board))

            start_time = time.time()
            ui_window.run()
            end_time = time.time()
            print(f"Board solved in {end_time - start_time} seconds.\n")
        else:
            solutions = solver.solve(logic_board, game_mode)
            print_solution(solutions, logic_board)
            to_txt(solutions, file_name, logic_board)

    else:
        ui_window = Window(on_click_callback=None)
        launch_mode_selector(ui_window, print_solution, to_txt)

if __name__ == "__main__":
    main()
