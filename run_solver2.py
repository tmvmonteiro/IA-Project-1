from src.board import Board
from src.solver2 import LinearBitsetSolver


def print_solution(result, solver):
    """
    Prints a readable summary of the optimized solver result.
    """
    print("\nSearch finished.")
    print(f"Solved: {result.solved}")
    print(f"Method: {result.method}")
    print(f"Presses in best solution: {result.press_count}")
    print(f"Rank: {result.rank}")
    print(f"Nullity: {result.nullity}")
    print(f"Enumerated candidates: {result.enumerated_candidates}")
    print(f"Time: {result.elapsed_time:.6f} seconds")

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
    Separate entrypoint that runs the optimized solver.
    """
    board = Board.from_csv("input/example.csv")
    board = Board.random(100, 100, 100)

    print("Initial board")
    print(board.format_matrix())

    solver = LinearBitsetSolver(board.rows, board.cols)
    result = solver.solve(board)
    print_solution(result, solver)


if __name__ == "__main__":
    main()
