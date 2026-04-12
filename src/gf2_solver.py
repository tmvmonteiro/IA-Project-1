"""Algebraic Lights Out solver using Gaussian elimination over GF(2).

The key idea is:
1. Each possible press is a binary variable (press it = 1, do not press it = 0).
2. Each cell gives one equation:
   the presses that affect this cell must sum to its current value.
3. Because Lights Out is binary, all arithmetic is done in GF(2):
   - addition is XOR
   - subtraction is also XOR
   - 1 + 1 = 0

This turns the puzzle into a linear system A x = b over GF(2).
"""

import time

from src.board import Board
from src.tree import TreeNode


# If the system has a few free variables, we exhaustively test the null-space
# combinations and keep the solution with the fewest button presses.
OPTIMIZATION_FREE_VARIABLE_LIMIT = 15


def _toggle_mask(size, row, col):
    """Return the bitmask for the cells affected by pressing (row, col)."""
    mask = 0
    for next_row, next_col in (
        (row, col),
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    ):
        if 0 <= next_row < size and 0 <= next_col < size:
            mask |= 1 << (next_row * size + next_col)
    return mask


def _build_augmented_matrix(board):
    """Build the augmented matrix [A | b] for the current board.

    We store each row as a single integer:
    - the lowest n bits are the coefficients of one equation
    - the bit at position n is the right-hand side value for that equation

    Here n = board.size * board.size, one variable per possible press.
    """
    rows = []
    variable_count = board.size * board.size

    for row in range(board.size):
        for col in range(board.size):
            # Column j is 1 if pressing move j affects this cell.
            coefficients = _toggle_mask(board.size, row, col)

            # The cell itself is the target value for the equation:
            # if it is currently 1, the affecting presses must XOR to 1.
            rhs = (board.matrix >> (row * board.size + col)) & 1

            # Append the RHS bit after all coefficient bits.
            rows.append(coefficients | (rhs << variable_count))

    return rows


def _optimize_solution(particular_solution, basis_vectors):
    """Try to reduce the number of presses using null-space basis vectors.

    If the system has free variables, there are multiple valid solutions.
    Any solution can be written as:

        particular_solution XOR combination_of_basis_vectors

    Each basis vector flips one free variable and the pivot variables that
    depend on it. We search these combinations when the null space is small
    enough and keep the solution with the smallest Hamming weight.
    """
    if not basis_vectors or len(basis_vectors) > OPTIMIZATION_FREE_VARIABLE_LIMIT:
        return particular_solution, False

    best_solution = particular_solution
    best_weight = particular_solution.bit_count()

    for combination in range(1, 1 << len(basis_vectors)):
        candidate = particular_solution
        for index, vector in enumerate(basis_vectors):
            if (combination >> index) & 1:
                candidate ^= vector

        candidate_weight = candidate.bit_count()
        if candidate_weight < best_weight:
            best_solution = candidate
            best_weight = candidate_weight

        if best_weight == 0:
            break

    return best_solution, True


def solve_board(board):
    """Solve one board by reducing its linear system over GF(2).

    The elimination below is Gauss-Jordan elimination:
    - find a pivot column
    - swap a row into the pivot position
    - XOR that row into every other row that has a 1 in the pivot column

    Because we eliminate both above and below the pivot, the resulting matrix is
    close to reduced row echelon form, which makes extracting a solution simple.
    """
    variable_count = board.size * board.size
    coefficient_mask = (1 << variable_count) - 1
    rows = _build_augmented_matrix(board)
    pivot_columns = []
    pivot_row = 0

    for column in range(variable_count):
        pivot_index = None
        for candidate in range(pivot_row, len(rows)):
            if (rows[candidate] >> column) & 1:
                pivot_index = candidate
                break

        if pivot_index is None:
            # No pivot in this column means this variable is free.
            continue

        rows[pivot_row], rows[pivot_index] = rows[pivot_index], rows[pivot_row]
        pivot_value = rows[pivot_row]

        # Over GF(2), row elimination is just XOR.
        for row_index in range(len(rows)):
            if row_index != pivot_row and ((rows[row_index] >> column) & 1):
                rows[row_index] ^= pivot_value

        pivot_columns.append(column)
        pivot_row += 1

        if pivot_row == len(rows):
            break

    # A row like 0 0 0 ... 0 | 1 means the system is inconsistent.
    for row in rows[pivot_row:]:
        if (row & coefficient_mask) == 0 and ((row >> variable_count) & 1):
            return None, {
                "visited_states": 0,
                "rank": len(pivot_columns),
                "free_variables": variable_count - len(pivot_columns),
                "optimized": False,
            }

    # With Gauss-Jordan elimination complete, each pivot row directly gives the
    # value of its pivot variable when all free variables are set to 0.
    particular_solution = 0
    for row_index, column in enumerate(pivot_columns):
        if (rows[row_index] >> variable_count) & 1:
            particular_solution |= 1 << column

    pivot_set = set(pivot_columns)
    free_columns = [column for column in range(variable_count) if column not in pivot_set]
    basis_vectors = []

    # Build one null-space basis vector per free variable.
    # That vector encodes how the pivot variables must change when that free
    # variable is set to 1.
    for free_column in free_columns:
        basis_vector = 1 << free_column
        for row_index, pivot_column in enumerate(pivot_columns):
            if (rows[row_index] >> free_column) & 1:
                basis_vector |= 1 << pivot_column
        basis_vectors.append(basis_vector)

    solution_mask, optimized = _optimize_solution(particular_solution, basis_vectors)

    # Convert the solution bitmask into board coordinates.
    presses = [
        (index // board.size, index % board.size)
        for index in range(variable_count)
        if (solution_mask >> index) & 1
    ]

    # Rebuild the solved board by replaying the presses on a copy.
    solved_board = Board(board.matrix, board.size, list(board.moves))
    for row, col in presses:
        solved_board.toggle(row, col)

    if not solved_board.is_solved():
        raise RuntimeError("GF(2) solver produced a non-solved board.")

    # The UI/reporting pipeline expects a TreeNode-like result object, so we
    # wrap the solved board even though this algorithm does not search a tree.
    result = TreeNode(solved_board)
    metrics = {
        # This is not a graph search, so there is no meaningful visited-state count.
        "visited_states": 0,
        "rank": len(pivot_columns),
        "free_variables": len(free_columns),
        "optimized": optimized,
    }
    return result, metrics


def solve(board):
    """Match the result format used by the rest of the project."""
    start_time = time.time()

    # Work on a copy so the caller's board is never mutated by the solver.
    result, metrics = solve_board(Board(board.matrix, board.size, list(board.moves)))

    elapsed = time.time() - start_time
    return [("gf2", result, elapsed, metrics)]
