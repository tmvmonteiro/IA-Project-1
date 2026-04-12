import random
import time

from src.board import Board
from src.tree import TreeNode


DEFAULT_STEP_FACTOR = 12
DEFAULT_MIN_STEPS = 10000


def solve_board(board, rng=None, max_steps=None):
    """Simulate a random player that presses random cells until it solves or gives up."""
    board_copy = Board(board.matrix, board.size, list(board.moves))
    rng = rng or random.Random()
    max_steps = max_steps or max(DEFAULT_MIN_STEPS, DEFAULT_STEP_FACTOR * board.size * board.size)
    visited_states = {board_copy.matrix}

    if board_copy.is_solved():
        return TreeNode(board_copy), {
            "visited_states": 1,
            "attempted_moves": 0,
            "max_steps": max_steps,
            "solved": True,
        }

    for _ in range(max_steps):
        row = rng.randrange(board_copy.size)
        col = rng.randrange(board_copy.size)
        board_copy.toggle(row, col)
        visited_states.add(board_copy.matrix)

        if board_copy.is_solved():
            return TreeNode(board_copy), {
                "visited_states": len(visited_states),
                "attempted_moves": len(board_copy.moves),
                "max_steps": max_steps,
                "solved": True,
            }

    return None, {
        "visited_states": len(visited_states),
        "attempted_moves": len(board_copy.moves),
        "max_steps": max_steps,
        "solved": False,
    }


def solve(board, rng=None, max_steps=None):
    start_time = time.time()
    result, metrics = solve_board(Board(board.matrix, board.size, list(board.moves)), rng=rng, max_steps=max_steps)
    elapsed = time.time() - start_time
    return [("random_player", result, elapsed, metrics)]
