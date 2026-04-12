from functools import partial
from src.board import Board
from src.window import Window
from src import solver
import time
import sys
import csv

def get_grid_from_mask(logic_board):
    """Helper to convert integer bitmask back to a 2D list for the UI."""
    size = logic_board.size
    return [[(logic_board.matrix >> (r * size + c)) & 1 
             for c in range(size)] 
            for r in range(size)]

def handle_ui_click(r, c, logic_board, ui_window):
    logic_board.toggle(r, c)
    
    grid = get_grid_from_mask(logic_board)
    ui_window.draw(grid)
    
    if logic_board.is_solved():
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

    for algorithm, result, time_taken in solutions:
        if result is not None:
            print(f"Algorithm:           {algorithm.upper()}")
            print(f"Time:                {time_taken:.7f} seconds")
            print(f"Board Size:          {result.state.size}x{result.state.size}")
            print(f"Number of Movements: {len(result.state.moves)}")
            print(f"Sequence:            {result.state.moves}")
            print("-" * 30 + "\n")

def to_txt(solutions, file, initial_logic_board):
    file_path = str('output/results_' + file)

    size = initial_logic_board.size
    matrix_str = ""
    for r in range(size):
        row = [(initial_logic_board.matrix >> (r * size + c)) & 1 for c in range(size)]
        matrix_str += " ".join(map(str, row)) + "\n"
    
    with open(file_path, mode='w', encoding='utf-8') as f:
        f.write("=== REPORT ===\n\n")
        f.write(f"INITIAL MATRIX ({size}x{size}):\n")
        f.write(matrix_str)
        f.write("-" * 30 + "\n")

        for algorithm, result, time_taken in solutions:
            if result is not None:
                f.write(f"Algorithm:           {algorithm.upper()}\n")
                f.write(f"Time:                {time_taken:.7f} seconds\n")
                f.write(f"Board Size:          {result.state.size}x{result.state.size}\n")
                f.write(f"Number of Movements: {len(result.state.moves)}\n")
                f.write(f"Sequence:            {result.state.moves}\n")
                f.write("-" * 30 + "\n")

def main():
    if len(sys.argv) > 1:
        game_mode = sys.argv[1]
        file = None
        logic_board = None
        if len(sys.argv) > 2:
            try:
                file = sys.argv[2]
                logic_board = Board.from_csv(str('input/' + file))
            except:
                print(f"Error: Failed to load board from '{file}'.\nDetails: {Exception}")
                sys.exit(1)
        else:
            try:
                file = 'example.csv'
                logic_board = Board.from_csv(str('input/' + file))
            except:
                print(f"Error: Failed to load board from '{file}'.\nDetails: {Exception}")
                sys.exit(1)
        solutions = None
        if (game_mode == "game"):
            ui_window = Window(on_click_callback=None)
            
            ui_window.on_click_callback = partial(
                handle_ui_click, 
                logic_board=logic_board, 
                ui_window=ui_window
            )

            ui_window.draw(logic_board.matrix)

            start_time = time.time()
            ui_window.run()  
            end_time = time.time()
            print(f"Board solved in {end_time - start_time} seconds.\n")
        else:
            solutions = solver.solve(logic_board, game_mode)

        print_solution(solutions, logic_board)
        to_txt(solutions, file, logic_board)   

    else:
        print(f"TO IMPLEMENT\n")

if __name__ == "__main__":
    main()