import numpy as np
import copy

class Board:
    def __init__(self, matrix, moves=None):
        """
        Initializes the board using a pre-existing NumPy matrix.
        """
        self.matrix = np.array(matrix)
        self.size = self.matrix.shape[0]
        self.number_moves = 0
        self.moves = moves if moves is not None else []
        
        # Validation: Ensure the matrix is square
        if self.matrix.shape[0] != self.matrix.shape[1]:
            raise ValueError("The input matrix must be square (NxN).")

    @classmethod
    def from_csv(cls, file_path):
        """
        Creates a Board instance by reading a CSV file.
        """
        data = np.loadtxt(file_path, delimiter=',', dtype=int)
        return cls(data)

    def toggle(self, r, c):
        """
        Toggles the cell (r, c) and its neighbors (Up, Down, Left, Right).
        """
        targets = [(r, c), (r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        
        for row, col in targets:
            if 0 <= row < self.size and 0 <= col < self.size:
                self.matrix[row, col] = 1 - self.matrix[row, col]
        
        self.moves.append((r, c))
        self.number_moves += 1

    def is_solved(self):
        return np.all(self.matrix == 0)
    
    def child_board_states(self):
        new_states = []
        for r in range(self.size):
            for c in range(self.size):
                # Create a deep copy to avoid modifying the current board
                new_board = copy.deepcopy(self)
                new_board.toggle(r, c)
                # Store the state and the move coordinates (optional metadata)
                new_states.append((new_board, (r, c)))
        return new_states
    
    def __repr__(self):
        return f"Board Size: {self.size}x{self.size} | Moves: {self.number_moves}\n{self.matrix}"