from functools import partial
from src.board import Board
from src.window import Window


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
    # logic_board = Board.from_csv("input/example.csv")
    logic_board = Board.random(5, 5, 10)

    ui_window = Window(on_click_callback=None)

    ui_window.on_click_callback = partial(
        handle_ui_click,
        logic_board=logic_board,
        ui_window=ui_window
    )

    ui_window.draw(logic_board.matrix)
    ui_window.run()

if __name__ == "__main__":
    main()
