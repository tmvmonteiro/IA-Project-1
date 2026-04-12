import random
import tkinter as tk


class Window:
    @staticmethod
    def _matrix_dimensions(matrix):
        rows = len(matrix)
        cols = len(matrix[0]) if rows else 0
        return rows, cols

    def load_theme(self, theme_name):
        self.theme = theme_name
        self.img_on = tk.PhotoImage(file=f"themes/{theme_name}/On.png")
        self.img_off = tk.PhotoImage(file=f"themes/{theme_name}/Off.png")

    def set_mode(self, value):
        self.mode = value

    def set_board(self, value):
        self.selected_board_label = value
        self.selected_board_name = self.board_name_by_label.get(value)

    def set_theme(self, value):
        self.theme = value
        self.load_theme(value)

    def configure_board_options(self, board_options, on_start_callback=None):
        self.board_options = list(board_options)
        self.on_start_callback = on_start_callback
        self.board_name_by_label = {
            option["label"]: option["name"]
            for option in self.board_options
        }

        if self.board_options:
            default_option = self.board_options[0]
            self.selected_board_label = default_option["label"]
            self.selected_board_name = default_option["name"]
        else:
            self.selected_board_label = ""
            self.selected_board_name = None

    def __init__(self, on_click_callback):
        self.root = tk.Tk()
        self.root.title("Lights Out")
        self.root.resizable(False, False)

        self.on_click_callback = on_click_callback

        self.container = tk.Frame(self.root)
        self.container.pack(padx=10, pady=10)

        self.theme = "Classic"
        self.load_theme(self.theme)
        self.state = "menu"

        self.mode = "manual"
        self.board_options = []
        self.board_name_by_label = {}
        self.selected_board_label = ""
        self.selected_board_name = None
        self.on_start_callback = None
        self.moves = 0
        self.current_matrix = []

    def draw(self, matrix=None):
        for widget in self.container.winfo_children():
            widget.destroy()

        if matrix is not None:
            self.current_matrix = matrix

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "game":
            self.draw_game(self.current_matrix)
        elif self.state == "win":
            self.draw_win()

    def draw_menu(self):
        frame = tk.Frame(self.container)
        frame.pack(expand=True)

        title = tk.Label(
            frame,
            text="Lights Out",
            font=("Arial", 28, "bold"),
        )
        title.pack(pady=(10, 20))

        start_btn = tk.Button(
            frame,
            text="Start Game",
            font=("Arial", 14),
            width=18,
            height=2,
            bg="#4CAF50",
            fg="white",
            relief="flat",
            command=self.start_game,
        )
        start_btn.pack(pady=10)

        settings_frame = tk.Frame(frame)
        settings_frame.pack(pady=10)

        tk.Label(
            settings_frame,
            text="Board:",
            font=("Arial", 12),
        ).grid(row=0, column=0, padx=10, pady=5)

        board_var = tk.StringVar(value=self.selected_board_label)
        board_labels = [option["label"] for option in self.board_options]
        board_dropdown = tk.OptionMenu(
            settings_frame,
            board_var,
            *board_labels,
            command=self.set_board,
        )
        board_dropdown.config(width=20)
        board_dropdown.grid(row=0, column=1, padx=10)

        tk.Label(
            settings_frame,
            text="Theme:",
            font=("Arial", 12),
        ).grid(row=1, column=0, padx=10, pady=5)

        theme_var = tk.StringVar(value=self.theme)
        theme_dropdown = tk.OptionMenu(
            settings_frame,
            theme_var,
            "Classic",
            "Days",
            "Fire-Water",
            command=self.set_theme,
        )
        theme_dropdown.config(width=12)
        theme_dropdown.grid(row=1, column=1, padx=10)

        tk.Label(
            settings_frame,
            text="Mode:",
            font=("Arial", 12),
        ).grid(row=2, column=0, padx=10, pady=5)

        mode_var = tk.StringVar(value=self.mode)
        mode_dropdown = tk.OptionMenu(
            settings_frame,
            mode_var,
            "manual",
            "random",
            command=self.set_mode,
        )
        mode_dropdown.config(width=12)
        mode_dropdown.grid(row=2, column=1, padx=10)

    def start_game(self):
        if self.on_start_callback is not None:
            if not self.on_start_callback(self.selected_board_name):
                return

        if not self.current_matrix:
            return

        self.state = "game"
        self.moves = 0
        self.draw(self.current_matrix)
        self.root.bind("<Escape>", self.handle_escape)

        if self.mode == "random":
            self.root.after(500, self.play_random)

    def change_theme(self):
        if self.theme == "Classic":
            self.theme = "Days"
        elif self.theme == "Days":
            self.theme = "Fire-Water"
        else:
            self.theme = "Classic"

        self.load_theme(self.theme)
        self.draw()

    def change_mode(self):
        if self.mode == "manual":
            self.mode = "random"
        else:
            self.mode = "manual"

        self.draw()

    def draw_game(self, matrix):
        rows, cols = self._matrix_dimensions(matrix)

        moves_label = tk.Label(
            self.container,
            text=f"Moves: {self.moves}",
            font=("Arial", 14),
        )
        moves_label.grid(row=0, column=0, columnspan=cols, pady=5)

        for row in range(rows):
            for col in range(cols):
                img = self.img_on if matrix[row][col] == 1 else self.img_off
                btn = tk.Button(
                    self.container,
                    image=img,
                    width=60,
                    height=60,
                    command=lambda r=row, c=col: self.on_click_callback(r, c),
                    bd=0,
                    highlightthickness=0,
                    relief="flat",
                )
                btn.grid(row=row + 1, column=col)

    def play_random(self):
        if self.state != "game":
            return

        rows, cols = self._matrix_dimensions(self.current_matrix)
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)

        self.on_click_callback(r, c)
        self.root.after(500, self.play_random)

    def draw_win(self):
        title = tk.Label(
            self.container,
            text="You Win!",
            font=("Arial", 20),
        )
        title.pack(pady=10)

        moves_label = tk.Label(
            self.container,
            text=f"Moves: {self.moves}",
            font=("Arial", 14),
        )
        moves_label.pack(pady=5)

        back_btn = tk.Button(
            self.container,
            text="Back to Menu",
            width=15,
            command=self.back_to_menu,
        )
        back_btn.pack(pady=10)

    def back_to_menu(self):
        self.state = "menu"
        self.draw()

    def handle_escape(self, event):
        if self.state == "game":
            self.back_to_menu()

    def run(self):
        self.root.mainloop()
