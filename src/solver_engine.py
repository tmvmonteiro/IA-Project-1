from itertools import count
import heapq

from src.tree import TreeNode


SUPPORTED_MODES = {"bfs", "ucs", "greedy", "astar", "wastar"}


def heuristic(node, weight=1):
    return weight * bin(node.state.matrix).count("1")


def _priority_for(mode, node):
    depth = len(node.state.moves)
    if mode == "bfs":
        return 0
    if mode == "ucs":
        return depth
    if mode == "greedy":
        return heuristic(node)
    if mode == "astar":
        return depth + heuristic(node)
    if mode == "wastar":
        return depth + heuristic(node, 2)
    raise ValueError(f"Unsupported game mode '{mode}'.")


def search(initial_state, mode):
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported game mode '{mode}'.")

    root = TreeNode(initial_state)
    queue = []
    order = count()
    heapq.heappush(queue, (0, next(order), root))
    visited = {initial_state.matrix}

    while queue:
        _, _, node = heapq.heappop(queue)

        if node.state.is_solved():
            return node, len(visited)

        for state in node.state.child_board_states():
            if state.matrix in visited:
                continue

            visited.add(state.matrix)
            child = TreeNode(state, parent=node)
            priority = _priority_for(mode, child)
            node.add_child(child, priority)
            heapq.heappush(queue, (priority, next(order), child))

    return None, len(visited)


def iter_search(initial_state, mode):
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported game mode '{mode}'.")

    root = TreeNode(initial_state)
    queue = []
    order = count()
    heapq.heappush(queue, (0, next(order), root))
    visited = {initial_state.matrix}

    while queue:
        priority, _, node = heapq.heappop(queue)

        yield {
            "kind": "visit",
            "node": node,
            "priority": priority,
            "frontier": len(queue),
            "visited": len(visited),
            "depth": len(node.state.moves),
            "last_move": node.state.moves[-1] if node.state.moves else None,
        }

        if node.state.is_solved():
            yield {
                "kind": "solution",
                "node": node,
                "priority": priority,
                "frontier": len(queue),
                "visited": len(visited),
                "depth": len(node.state.moves),
                "last_move": node.state.moves[-1] if node.state.moves else None,
            }
            return node

        for state in node.state.child_board_states():
            if state.matrix in visited:
                continue

            visited.add(state.matrix)
            child = TreeNode(state, parent=node)
            child_priority = _priority_for(mode, child)
            node.add_child(child, child_priority)
            heapq.heappush(queue, (child_priority, next(order), child))

    return None
