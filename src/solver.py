from src.board import Board
from src.tree import TreeNode
import time

def solve(logic_board, game_mode):
    if (game_mode == "bfs"):
        start_time = time.time()
        result = breadth_first_search(logic_board, Board.is_solved, Board.child_board_states)
        end_time = time.time()
        print(f"Board solved in {end_time - start_time} seconds.\n")
        print(result.state.moves)
    else:
        print("Need to insert correct game mode")

from collections import deque

def breadth_first_search(initial_state, goal_state_func, operators_func):
    root = TreeNode(initial_state)
    queue = deque([root])

    visited = set()
    visited.add(initial_state.matrix)

    while queue:
        node = queue.popleft()
        if goal_state_func(node.state):
            return node

        for state, _ in operators_func(node.state):
            if state.matrix not in visited:
                visited.add(state.matrix)
                child = TreeNode(state, parent=node)
                node.add_child(child)
                queue.append(child)

    return None