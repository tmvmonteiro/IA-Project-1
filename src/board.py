import numpy as np

class Board:
    def __init__(self, matrix):
        """
        Initializes the board using a pre-existing NumPy matrix.
        """
        self.matrix = np.array(matrix)
        if self.matrix.ndim != 2:
            raise ValueError("The input matrix must be two-dimensional.")

        self.rows = self.matrix.shape[0]
        self.cols = self.matrix.shape[1]
        self.moves = 0

    @classmethod
    def from_csv(cls, file_path):
        """
        Creates a Board instance by reading a CSV file.
        """
        data = np.loadtxt(file_path, delimiter=',', dtype=int)
        return cls(data)
    
    @classmethod
    def random(cls, rows, cols, moves):
        """
        Generates a solvable random board by starting from an empty board
        and applying random valid moves.
        """
        if rows <= 0 or cols <= 0:
            raise ValueError("Board dimensions must be positive.")
        if moves < 0:
            raise ValueError("The number of moves must be non-negative.")

        moves = min(moves, rows * cols)

        matrix = np.zeros((rows, cols), dtype=int)
        board = cls(matrix)

        chosen_indices = np.random.choice(rows * cols, size=moves, replace=False)

        for index in chosen_indices:
            r, c = divmod(int(index), cols)
            board.toggle(r, c)

        board.moves = 0
        return board

    def toggle(self, r, c):
        """
        Toggles the cell (r, c) and its neighbors (Up, Down, Left, Right).
        """
        targets = [(r, c), (r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        
        for row, col in targets:
            if 0 <= row < self.rows and 0 <= col < self.cols:
                self.matrix[row, col] = 1 - self.matrix[row, col]
        
        self.moves += 1

    def is_solved(self):
        return np.all(self.matrix == 0)

    def copy(self):
        """
        Returns a new board with the same matrix and move counter.
        """
        new_board = Board(self.matrix.copy())
        new_board.moves = self.moves
        return new_board

    def to_state(self):
        """
        Encodes the board as a single integer bitmask.
        Each cell becomes one bit, which is faster for BFS than storing arrays.
        """
        state = 0

        for row in range(self.rows):
            for col in range(self.cols):
                if self.matrix[row, col] == 1:
                    bit_index = row * self.cols + col
                    state |= 1 << bit_index

        return state

    @classmethod
    def from_state(cls, rows, cols, state, moves=0):
        """
        Builds a board from an integer bitmask.
        """
        matrix = np.zeros((rows, cols), dtype=int)

        for row in range(rows):
            for col in range(cols):
                bit_index = row * cols + col
                matrix[row, col] = (state >> bit_index) & 1

        board = cls(matrix)
        board.moves = moves
        return board

    def apply_move(self, move):
        """
        Returns a new board after applying one move.
        """
        row, col = move
        new_board = self.copy()
        new_board.toggle(row, col)
        return new_board

    def format_matrix(self):
        """
        Returns the matrix in a readable multi-line string.
        """
        return "\n".join(" ".join(str(value) for value in row) for row in self.matrix)
    
    def __repr__(self):
        return f"Board Size: {self.rows}x{self.cols} | Moves: {self.moves}\n{self.matrix}"
