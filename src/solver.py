from src.board import Board
from src.tree import TreeNode
import time

def compar(x):
    return x[1]

def solve(logic_board, game_mode):
    solution = []
    if (game_mode == "bfs"):
        start_time = time.time()
        result = breadth_first_search(logic_board, Board.is_solved, Board.child_board_states)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("bfs", result, duration))
    elif (game_mode == "ucs"):
        start_time = time.time()
        result = uniform_cost_search(logic_board, Board.is_solved, Board.child_board_states)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("ucs", result, duration))
    elif (game_mode == "greedy"):
        start_time = time.time()
        result = greedy_search(logic_board, Board.is_solved, Board.child_board_states, greedy)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("greedy", result, duration))
    elif (game_mode == "astar"):
        start_time = time.time()
        result = astar_search(logic_board, Board.is_solved, Board.child_board_states, greedy)
        end_time = time.time()
        duration = end_time - start_time
        solution.append(("astar", result, duration))
    else:
        print("Need to insert correct game mode")
    return solution

def breadth_first_search(initial_state, goal_state_func, operators_func):
    root = TreeNode(initial_state)
    queue = [root]

    visited = set()
    visited.add(initial_state.matrix)

    while queue:
        node = queue.pop(0)
        if goal_state_func(node.state):
            return node

        for state in operators_func(node.state):
            if state.matrix not in visited:
                visited.add(state.matrix)
                child = TreeNode(state, parent=node)
                g_n = len(state.moves)
                node.add_child(child, g_n)
                queue.append(child)

    return None

def uniform_cost_search(initial_state, goal_state_func, operators_func):
    root = TreeNode(initial_state)
    queue = [root]

    visited = set()
    visited.add(initial_state.matrix)

    while queue:
        node = queue.pop(0)
        if goal_state_func(node.state):
            return node

        for state in operators_func(node.state):
            if state.matrix not in visited:
                visited.add(state.matrix)
                child = TreeNode(state, parent=node)
                g_n = len(state.moves)
                node.add_child(child, g_n)
                queue.append(child)

        queue.sort(key=lambda node: node.cost)  

    return None

def greedy_search(initial_state, goal_state_func, operators_func, heuristic_func):
    root = TreeNode(initial_state)
    queue = [root]

    visited = set()
    visited.add(initial_state.matrix)

    while queue:
        node = queue.pop(0)
        if goal_state_func(node.state):
            return node

        for state in operators_func(node.state):
            if state.matrix not in visited:
                visited.add(state.matrix)
                child = TreeNode(state, parent=node)  
                h_n = heuristic_func(child)     
                node.add_child(child, h_n)
                queue.append(child)
        
        queue.sort(key=lambda node: node.cost)      
    
    return None

def greedy(node):
    return bin(node.state.matrix).count('1')

def astar_search(initial_state, goal_state_func, operators_func, heuristic_func):
    root = TreeNode(initial_state)
    queue = [root]

    visited = set()
    visited.add(initial_state.matrix)

    while queue:
        node = queue.pop(0)
        if goal_state_func(node.state):
            return node

        for state in operators_func(node.state):
            if state.matrix not in visited:
                visited.add(state.matrix)
                child = TreeNode(state, parent=node)  
                g_n = len(state.moves)
                h_n = heuristic_func(child)
                node.add_child(child, g_n + h_n)
                queue.append(child)
        
        queue.sort(key=lambda node: node.cost)     
    
    return None