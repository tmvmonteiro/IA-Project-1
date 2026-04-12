import random
import re

class Board:
    def __init__(self, matrix, size, moves=None):
        """
        Initializes the board using a pre-existing bitmask.
        """
        self.matrix = int(matrix)
        self.size = size
        self.moves = moves if moves is not None else []
        
    @classmethod
    def from_txt(cls, file_path):
        """
        Creates a Board instance by reading a plain-text board file.
        """
        with open(file_path, encoding="utf-8") as file_handle:
            rows = [line.strip() for line in file_handle if line.strip()]

        data = []
        for row in rows:
            values = [int(value) for value in re.split(r"[\s,]+", row) if value]
            data.append(values)

        size = len(data)
        if size == 0:
            raise ValueError(f"Board file '{file_path}' is empty.")

        if any(len(row) != size for row in data):
            raise ValueError(f"Board file '{file_path}' must contain a square matrix.")

        if any(value not in (0, 1) for row in data for value in row):
            raise ValueError(f"Board file '{file_path}' must contain only 0 and 1 values.")

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
        Creates a solvable random board by starting from a clean board and applying
        a set of unique random presses.
        """
        if size <= 0:
            raise ValueError("Board size must be greater than zero.")

        rng = rng or random.Random()
        max_cells = size * size
        if toggle_count is None:
            toggle_count = max(1, size + size // 2)

        toggle_count = max(0, min(toggle_count, max_cells))

        positions = [(r, c) for r in range(size) for c in range(size)]
        chosen_positions = rng.sample(positions, toggle_count)
        matrix = 0

        # Sample without replacement so the same press position is never applied twice.
        for row, col in chosen_positions:
            targets = ((row, col), (row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
            for target_row, target_col in targets:
                if 0 <= target_row < size and 0 <= target_col < size:
                    matrix ^= 1 << (target_row * size + target_col)

        return cls(matrix, size, [])

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
