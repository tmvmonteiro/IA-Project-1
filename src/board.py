import csv
import random

class Board:
    def __init__(self, matrix, size, moves=None):
        """
        Initializes the board using a pre-existing NumPy matrix.
        """
        self.matrix = int(matrix)
        self.size = size
        self.moves = moves if moves is not None else []
        
    @classmethod
    def from_csv(cls, file_path):
        """
        Creates a Board instance by reading a CSV file.
        """
        with open(file_path, newline="", encoding="utf-8") as file_handle:
            data = [
                [int(value) for value in row]
                for row in csv.reader(file_handle)
                if row
            ]

        size = len(data)
        matrix_int = 0
        for r in range(size):
            for c in range(size):
                if data[r][c] == 1:
                    # Map 2D coordinates to a 1D bit position
                    matrix_int |= (1 << (r * size + c))

        return cls(matrix_int, size)

    @classmethod
    def random_board(cls, size, toggle_count=None, rng=None):
        """
        Creates a solvable random board by starting from a clean board and toggling
        a set of unique cells.
        """
        if size <= 0:
            raise ValueError("Board size must be greater than zero.")

        rng = rng or random.Random()
        max_cells = size * size
        if toggle_count is None:
            toggle_count = max(1, size + size // 2)

        toggle_count = max(0, min(toggle_count, max_cells))

        board = cls(0, size)
        positions = [(r, c) for r in range(size) for c in range(size)]

        for row, col in rng.sample(positions, toggle_count):
            board.toggle(row, col)

        board.moves = []
        return board

    def toggle(self, r, c):
        """
        Toggles the cell (r, c) and its neighbors (Up, Down, Left, Right).
        """
        targets = [(r, c), (r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        mask = 0
        
        for row, col in targets:
            if 0 <= row < self.size and 0 <= col < self.size:
                mask |= (1 << (row * self.size + col))
        
        self.matrix ^= mask
        self.moves.append((r, c))

    def is_solved(self):
        return self.matrix == 0
    
    def child_board_states(self):
        new_states = []
        for r in range(self.size):
            for c in range(self.size):
                new_board = Board(self.matrix, self.size, list(self.moves))
                new_board.toggle(r, c)
                new_states.append(new_board)
        return new_states
    
    def __repr__(self):
        return f"Board Length: {self.size} | Number of moves: {len(self.moves)} | Moves: {sorted(self.moves, key=lambda x: (x[0], x[1]))}\n"