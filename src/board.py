import numpy as np

class Board:
    def __init__(self, matrix):
        """
        Initializes the board using a pre-existing NumPy matrix.
        """
        self.matrix = np.array(matrix)
        self.size = self.matrix.shape[0]
        self.moves = 0
        
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
        
        self.moves += 1

    def is_solved(self):
        return np.all(self.matrix == 0)
    
    def __repr__(self):
        return f"Board Size: {self.size}x{self.size} | Moves: {self.moves}\n{self.matrix}"