from dataclasses import dataclass
from time import perf_counter

from src.board import Board


@dataclass(slots=True)
class Solver2Result:
    """
    Result of the optimized Lights Out solver.
    """
    solved: bool
    method: str
    solution_moves: list[tuple[int, int]]
    solution_states: list[int]
    press_state: int
    press_count: int
    rank: int
    nullity: int
    enumerated_candidates: int
    elapsed_time: float


class LinearBitsetSolver:
    """
    Fast exact solver for Lights Out.

    The board is solved as a linear system over GF(2):
        A * x = b

    A and all candidate solutions are stored as Python integers, so row
    operations are done with xor instead of Python lists of booleans.
    """

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.cell_count = rows * cols
        self.augmented_bit = self.cell_count
        self.coefficient_mask = (1 << self.cell_count) - 1
        self.moves = [(row, col) for row in range(rows) for col in range(cols)]
        self.effect_masks = self._build_effect_masks()

    def _build_effect_masks(self):
        """
        Builds one bitmask per press position.
        Each mask marks the cells flipped by pressing that position.
        """
        masks = []

        for row, col in self.moves:
            mask = 0
            for next_row, next_col in (
                (row, col),
                (row - 1, col),
                (row + 1, col),
                (row, col - 1),
                (row, col + 1),
            ):
                if 0 <= next_row < self.rows and 0 <= next_col < self.cols:
                    index = next_row * self.cols + next_col
                    mask |= 1 << index

            masks.append(mask)

        return masks

    def _build_augmented_matrix(self, board_state):
        """
        Builds the system A * x = b.

        For Lights Out the coefficient matrix is symmetric, so the equation row
        for a cell has the same pattern as the effect mask of pressing that cell.
        """
        rows = []

        for cell_index, effect_mask in enumerate(self.effect_masks):
            rhs = (board_state >> cell_index) & 1
            rows.append(effect_mask | (rhs << self.augmented_bit))

        return rows

    def _reduced_row_echelon_form(self, augmented_rows):
        """
        Converts the augmented matrix into reduced row echelon form over GF(2).
        """
        rows = augmented_rows[:]
        pivot_columns = []
        pivot_rows_by_column = {}
        pivot_row = 0

        for column in range(self.cell_count):
            pivot = None

            for row_index in range(pivot_row, self.cell_count):
                if (rows[row_index] >> column) & 1:
                    pivot = row_index
                    break

            if pivot is None:
                continue

            rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]

            for row_index in range(self.cell_count):
                if row_index != pivot_row and ((rows[row_index] >> column) & 1):
                    rows[row_index] ^= rows[pivot_row]

            pivot_columns.append(column)
            pivot_rows_by_column[column] = pivot_row
            pivot_row += 1

            if pivot_row == self.cell_count:
                break

        return rows, pivot_columns, pivot_rows_by_column

    def _is_inconsistent(self, rref_rows):
        """
        Checks whether the system has no solution.
        """
        for row in rref_rows:
            coefficients = row & self.coefficient_mask
            rhs = (row >> self.augmented_bit) & 1

            if coefficients == 0 and rhs == 1:
                return True

        return False

    def _build_affine_solution_space(self, rref_rows, pivot_columns, pivot_rows_by_column):
        """
        Returns one particular solution and a basis for the null space.
        """
        particular_solution = 0
        free_columns = []
        pivot_set = set(pivot_columns)

        for column in range(self.cell_count):
            if column not in pivot_set:
                free_columns.append(column)

        for pivot_column in pivot_columns:
            row_index = pivot_rows_by_column[pivot_column]
            rhs = (rref_rows[row_index] >> self.augmented_bit) & 1

            if rhs:
                particular_solution |= 1 << pivot_column

        null_space_basis = []

        for free_column in free_columns:
            basis_vector = 1 << free_column

            for pivot_column in pivot_columns:
                row_index = pivot_rows_by_column[pivot_column]

                if (rref_rows[row_index] >> free_column) & 1:
                    basis_vector |= 1 << pivot_column

            null_space_basis.append(basis_vector)

        return particular_solution, null_space_basis

    def _minimum_weight_solution(self, particular_solution, null_space_basis):
        """
        Finds the exact minimum-press solution inside the affine solution space.

        Gray-code enumeration lets us update the current candidate by flipping
        exactly one basis vector at a time.
        """
        current_solution = particular_solution
        best_solution = particular_solution
        best_weight = particular_solution.bit_count()
        previous_gray = 0
        total_candidates = 1 << len(null_space_basis)

        for step in range(1, total_candidates):
            gray = step ^ (step >> 1)
            changed = gray ^ previous_gray
            basis_index = changed.bit_length() - 1
            current_solution ^= null_space_basis[basis_index]

            current_weight = current_solution.bit_count()
            if current_weight < best_weight:
                best_solution = current_solution
                best_weight = current_weight

            previous_gray = gray

        return best_solution, best_weight, total_candidates

    def _solution_moves_from_press_state(self, press_state):
        """
        Converts the press bitmask into board coordinates.
        """
        moves = []

        for index in range(self.cell_count):
            if (press_state >> index) & 1:
                moves.append(divmod(index, self.cols))

        return moves

    def _solution_states_from_moves(self, board, moves):
        """
        Builds the sequence of board states after applying the solution moves.
        """
        states = [board.to_state()]
        current_board = board.copy()

        for move in moves:
            current_board.toggle(*move)
            states.append(current_board.to_state())

        return states

    def solve(self, board):
        """
        Solves the board exactly and returns the minimum-press solution found.
        """
        if board.rows != self.rows or board.cols != self.cols:
            raise ValueError("Solver dimensions do not match the board dimensions.")

        start_time = perf_counter()
        board_state = board.to_state()

        if board_state == 0:
            elapsed_time = perf_counter() - start_time
            return Solver2Result(
                solved=True,
                method="GF(2) bitset elimination",
                solution_moves=[],
                solution_states=[board_state],
                press_state=0,
                press_count=0,
                rank=0,
                nullity=self.cell_count,
                enumerated_candidates=1,
                elapsed_time=elapsed_time,
            )

        augmented_rows = self._build_augmented_matrix(board_state)
        rref_rows, pivot_columns, pivot_rows_by_column = self._reduced_row_echelon_form(augmented_rows)

        if self._is_inconsistent(rref_rows):
            elapsed_time = perf_counter() - start_time
            return Solver2Result(
                solved=False,
                method="GF(2) bitset elimination",
                solution_moves=[],
                solution_states=[],
                press_state=0,
                press_count=0,
                rank=len(pivot_columns),
                nullity=self.cell_count - len(pivot_columns),
                enumerated_candidates=0,
                elapsed_time=elapsed_time,
            )

        particular_solution, null_space_basis = self._build_affine_solution_space(
            rref_rows,
            pivot_columns,
            pivot_rows_by_column,
        )

        press_state, press_count, enumerated_candidates = self._minimum_weight_solution(
            particular_solution,
            null_space_basis,
        )
        solution_moves = self._solution_moves_from_press_state(press_state)
        solution_states = self._solution_states_from_moves(board, solution_moves)
        elapsed_time = perf_counter() - start_time

        return Solver2Result(
            solved=True,
            method="GF(2) bitset elimination + exact null-space minimization",
            solution_moves=solution_moves,
            solution_states=solution_states,
            press_state=press_state,
            press_count=press_count,
            rank=len(pivot_columns),
            nullity=len(null_space_basis),
            enumerated_candidates=enumerated_candidates,
            elapsed_time=elapsed_time,
        )

    def state_to_board(self, state, moves=0):
        """
        Converts an integer state back into a Board instance.
        """
        return Board.from_state(self.rows, self.cols, state, moves=moves)
