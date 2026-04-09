from src.board import Board
from src.tree import TreeNode
import time

def compar(x):
    return x[1]

def solve(logic_board, game_mode):
    if (game_mode == "bfs"):
        start_time = time.time()
        result = breadth_first_search(logic_board, Board.is_solved, Board.child_board_states)
        end_time = time.time()
        print(f"Board solved in {end_time - start_time} seconds.\n")
        print(result.state.moves)
    elif (game_mode == "ucs"):
        start_time = time.time()
        result = breadth_first_search(logic_board, Board.is_solved, Board.child_board_states)
        end_time = time.time()
        print(f"Board solved in {end_time - start_time} seconds.\n")
        print(result.state.moves)
    elif (game_mode == "greedy"):
        start_time = time.time()
        result = greedy_search(logic_board, Board.is_solved, Board.child_board_states, greedy)
        end_time = time.time()
        print(f"Board solved in {end_time - start_time} seconds.\n")
        print(sorted(result.state.moves, key=lambda x: (x[0], x[1])))
    elif (game_mode == "astar"):
        start_time = time.time()
        result = astar_search(logic_board, Board.is_solved, Board.child_board_states, greedy)
        end_time = time.time()
        print(f"Board solved in {end_time - start_time} seconds.\n")
        print(sorted(result.state.moves, key=lambda x: (x[0], x[1])))
    else:
        print("Need to insert correct game mode")

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