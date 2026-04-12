from dataclasses import dataclass, field


@dataclass(slots=True)
class SearchNode:
    """
    One node in the search tree.
    Stores only the minimum information needed to rebuild the solution path.
    """
    node_id: int
    state: int
    parent_id: int | None
    move: tuple[int, int] | None
    depth: int
    next_move_index: int
    children: list[int] = field(default_factory=list)


class SearchTree:
    """
    Small helper around the BFS tree.
    Keeps nodes indexed by id so we can rebuild the solution after the search.
    """

    def __init__(self, root_state):
        self.nodes = {}
        self.root_id = self.add_node(
            root_state,
            parent_id=None,
            move=None,
            depth=0,
            next_move_index=0,
        )

    def add_node(self, state, parent_id, move, depth, next_move_index):
        node_id = len(self.nodes)
        self.nodes[node_id] = SearchNode(
            node_id=node_id,
            state=state,
            parent_id=parent_id,
            move=move,
            depth=depth,
            next_move_index=next_move_index,
        )

        if parent_id is not None:
            self.nodes[parent_id].children.append(node_id)

        return node_id

    def get_node(self, node_id):
        return self.nodes[node_id]

    def build_path(self, node_id):
        """
        Returns the nodes from the root to the target node.
        """
        path = []
        current_id = node_id

        while current_id is not None:
            node = self.nodes[current_id]
            path.append(node)
            current_id = node.parent_id

        path.reverse()
        return path

    def summary(self):
        """
        Simple search tree statistics.
        """
        max_depth = max((node.depth for node in self.nodes.values()), default=0)
        leaf_count = sum(1 for node in self.nodes.values() if not node.children)
        internal_nodes = sum(1 for node in self.nodes.values() if node.children)
        total_children = sum(len(node.children) for node in self.nodes.values())
        max_branching = max((len(node.children) for node in self.nodes.values()), default=0)
        average_branching = total_children / internal_nodes if internal_nodes else 0

        return {
            "total_nodes": len(self.nodes),
            "max_depth": max_depth,
            "leaf_nodes": leaf_count,
            "max_branching": max_branching,
            "average_branching": average_branching,
        }
