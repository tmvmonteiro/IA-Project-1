from src.board import Board

class TreeNode:
    def __init__(self, state : Board, parent=None):
        self.state = state # the Board itself
        self.parent = parent
        self.children = []
        self.cost = 0   # the path cost to get to this state
    
    def add_child(self, child_node, operator_cost=1):
        self.children.append(child_node)
        child_node.cost = self.cost + operator_cost   # the path cost is the parent's cost plus this operator cost
        child_node.parent = self