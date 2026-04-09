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

def print_solution(solutions):
    for algorithm, result, time in solutions:
        if result is not None:
            print(f"Algorithm: {algorithm} | Time: {time:.7f} | {result.state}")

def to_csv(solutions, file_path="output/results_example.csv"):
    headers = ["Algorithm", "Time (s)", "Board Size", "Number of Moves"]
    
    with open(file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        
        for algorithm, result, time_taken in solutions:
            if result is not None:
                row = [
                    algorithm, 
                    f"{time_taken:.7f}", 
                    result.state.size, 
                    len(result.state.moves)
                ]
                writer.writerow(row)

def main():
    if len(sys.argv) > 1:
        game_mode = sys.argv[1]
        logic_board = Board.from_csv("input/example.csv")
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

        print_solution(solutions)
        to_csv(solutions)   

    else:
        print(f"TO IMPLEMENT\n")

if __name__ == "__main__":
    main()