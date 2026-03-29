from functools import partial
from src.board import Board
from src.window import Window
from src import solver
import time
import sys

def handle_ui_click(r, c, logic_board, ui_window):
    """
    Standalone controller function.
    Coordinates updates between the logic and the UI.
    """
    
    logic_board.toggle(r, c)
    
    ui_window.draw(logic_board.matrix)
    
    if logic_board.is_solved():
        ui_window.root.destroy()

def main():
    if len(sys.argv) > 1:
        game_mode = sys.argv[1]
        logic_board = Board.from_csv("input/example.csv")
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
            solver.solve(logic_board, game_mode)
    else:
        print(f"TO IMPLEMENT\n")

if __name__ == "__main__":
    main()