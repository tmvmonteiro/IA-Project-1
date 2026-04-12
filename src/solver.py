from src.board import Board
from src.tree import TreeNode
from src.solver_engine import search as _engine_search
from src.solver_engine import iter_search as _engine_iter_search
import time


def compar(x):
    return x[1]


def solve(logic_board, game_mode):
    solution = []
    if (game_mode == "bfs"):
        start_time = time.time()
        result, visited_states = breadth_first_search(logic_board, Board.is_solved, Board.child_board_states, True)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("bfs", result, duration, {"visited_states": visited_states}))
    elif (game_mode == "ucs"):
        start_time = time.time()
        result, visited_states = uniform_cost_search(logic_board, Board.is_solved, Board.child_board_states, True)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("ucs", result, duration, {"visited_states": visited_states}))
    elif (game_mode == "greedy"):
        start_time = time.time()
        result, visited_states = greedy_search(logic_board, Board.is_solved, Board.child_board_states, greedy, True)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("greedy", result, duration, {"visited_states": visited_states}))
    elif (game_mode == "astar"):
        start_time = time.time()
        result, visited_states = astar_search(logic_board, Board.is_solved, Board.child_board_states, greedy, 1, True)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("astar", result, duration, {"visited_states": visited_states}))
    elif (game_mode == "wastar"):
        start_time = time.time()
        result, visited_states = astar_search(logic_board, Board.is_solved, Board.child_board_states, greedy, 2, True)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("wastar", result, duration, {"visited_states": visited_states}))
    else:
        print("Need to insert correct game mode")
    return solution


def breadth_first_search(initial_state, goal_state_func, operators_func, return_stats=False):
    result, visited_states = _engine_search(initial_state, "bfs")
    if return_stats:
        return result, visited_states
    return result


def uniform_cost_search(initial_state, goal_state_func, operators_func, return_stats=False):
    result, visited_states = _engine_search(initial_state, "ucs")
    if return_stats:
        return result, visited_states
    return result


def greedy_search(initial_state, goal_state_func, operators_func, heuristic_func, return_stats=False):
    result, visited_states = _engine_search(initial_state, "greedy")
    if return_stats:
        return result, visited_states
    return result


def greedy(node, weigth=1):
    return weigth * bin(node.state.matrix).count('1')


def astar_search(initial_state, goal_state_func, operators_func, heuristic_func, weigth=1, return_stats=False):
    mode = "wastar" if weigth == 2 else "astar"
    result, visited_states = _engine_search(initial_state, mode)
    if return_stats:
        return result, visited_states
    return result


def iter_search(initial_state, game_mode):
    return _engine_iter_search(initial_state, game_mode)