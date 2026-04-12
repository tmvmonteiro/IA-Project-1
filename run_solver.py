from src.board import Board
from src.solver import BFSSolver


def print_solution(result, solver):
    """
    Prints a readable summary of the BFS result.
    """
    print("\nSearch finished.")
    print(f"Solved: {result.solved}")
    print(f"Explored nodes: {result.explored_nodes}")
    print(f"Time: {result.elapsed_time:.6f} seconds")

    tree_summary = result.tree.summary()
    print("\nSearch tree")
    print(f"Total nodes: {tree_summary['total_nodes']}")
    print(f"Maximum depth: {tree_summary['max_depth']}")
    print(f"Leaf nodes: {tree_summary['leaf_nodes']}")
    print(f"Maximum branching factor: {tree_summary['max_branching']}")
    print(f"Average branching factor: {tree_summary['average_branching']:.2f}")

    if not result.solved:
        print("\nNo solution was found.")
        return

    print("\nSolution moves")
    for step_number, move in enumerate(result.solution_moves, start=1):
        print(f"{step_number}. Toggle cell {move}")

    print("\nSolution path")
    for step_number, state in enumerate(result.solution_states):
        board = solver.state_to_board(state, moves=step_number)
        print(f"\nStep {step_number}")
        print(board.format_matrix())


def main():
    """
    Separate entrypoint that runs the BFS solver.
    """
    board = Board.from_csv("input/example.csv")
    board = Board.random(10, 10, 4)  # Uncomment to test with a random board instead of the example.

    print("Initial board")
    print(board.format_matrix())

    solver = BFSSolver(board.rows, board.cols)
    result = solver.solve(board)
    print_solution(result, solver)


if __name__ == "__main__":
    main()
