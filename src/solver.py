from collections import deque
from dataclasses import dataclass
from time import perf_counter

from src.board import Board
from src.tree import SearchTree


@dataclass(slots=True)
class SolverResult:
    """
    Final result returned by the BFS solver.
    """
    solved: bool
    tree: SearchTree
    solution_moves: list[tuple[int, int]]
    solution_states: list[int]
    explored_nodes: int
    elapsed_time: float


class BFSSolver:
    """
    Breadth-First Search solver for Lights Out.
    Uses integer bitmasks so state expansion stays fast and simple.
    Each cell can be used at most once, because toggling the same cell twice
    would cancel the effect and only waste search time.
    """

    def __init__(self, board_rows, board_cols=None):
        self.rows = board_rows
        self.cols = board_rows if board_cols is None else board_cols
        self.goal_state = 0
        self.moves = [(row, col) for row in range(self.rows) for col in range(self.cols)]
        self.move_count = len(self.moves)
        self.toggle_masks = self._build_toggle_masks()

    def _build_toggle_masks(self):
        """
        Precomputes the bitmask changed by each possible move.
        """
        masks = []

        for row, col in self.moves:
            mask = 0
            positions = [
                (row, col),
                (row - 1, col),
                (row + 1, col),
                (row, col - 1),
                (row, col + 1),
            ]

            for next_row, next_col in positions:
                if 0 <= next_row < self.rows and 0 <= next_col < self.cols:
                    bit_index = next_row * self.cols + next_col
                    mask |= 1 << bit_index

            masks.append(mask)

        return masks

    def _next_state(self, state, move_index):
        """
        Applies a move using xor because toggling is just bit flipping.
        """
        return state ^ self.toggle_masks[move_index]

    def solve(self, board):
        """
        Runs BFS and returns the shortest solution.
        """
        start_state = board.to_state()
        tree = SearchTree(start_state)
        queue = deque([tree.root_id])
        visited = {(start_state, 0)}
        explored_nodes = 0
        start_time = perf_counter()

        if start_state == self.goal_state:
            elapsed_time = perf_counter() - start_time
            return SolverResult(
                solved=True,
                tree=tree,
                solution_moves=[],
                solution_states=[start_state],
                explored_nodes=1,
                elapsed_time=elapsed_time,
            )

        while queue:
            current_id = queue.popleft()
            current_node = tree.get_node(current_id)
            explored_nodes += 1

            # Only moves after current_node.next_move_index are allowed.
            # This guarantees the same cell is never selected twice and
            # prevents duplicate paths that differ only in move order.
            for move_index in range(current_node.next_move_index, self.move_count):
                next_state = self._next_state(current_node.state, move_index)
                next_move_index = move_index + 1
                visited_key = (next_state, next_move_index)

                if visited_key in visited:
                    continue

                child_id = tree.add_node(
                    state=next_state,
                    parent_id=current_id,
                    move=self.moves[move_index],
                    depth=current_node.depth + 1,
                    next_move_index=next_move_index,
                )
                visited.add(visited_key)

                if next_state == self.goal_state:
                    elapsed_time = perf_counter() - start_time
                    path = tree.build_path(child_id)

                    return SolverResult(
                        solved=True,
                        tree=tree,
                        solution_moves=[node.move for node in path[1:]],
                        solution_states=[node.state for node in path],
                        explored_nodes=explored_nodes,
                        elapsed_time=elapsed_time,
                    )

                queue.append(child_id)

        elapsed_time = perf_counter() - start_time
        return SolverResult(
            solved=False,
            tree=tree,
            solution_moves=[],
            solution_states=[],
            explored_nodes=explored_nodes,
            elapsed_time=elapsed_time,
        )

    def state_to_board(self, state, moves=0):
        """
        Helper used by main to display solution steps.
        """
        return Board.from_state(self.rows, self.cols, state, moves=moves)
