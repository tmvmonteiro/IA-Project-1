import argparse
import csv
import json
import multiprocessing as mp
from pathlib import Path
import queue
import random
import time
import traceback

from src.board import Board


# Benchmark settings. Edit these values first when you want to change the run.
DEFAULT_SETTINGS = {
    "board_sizes": [3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20],
    "toggle_counts": [3, 5, 8, 10, 12, 15, 20, 25, 30, 40, 50],
    "algorithms": ["bfs", "ucs", "greedy", "astar", "wastar", "gf2"],
    "boards_per_combination": 3,
    "timeout_seconds": 20.0,
    "base_seed": 1337,
    "run_name": "default_run",
    "output_root": Path("output") / "benchmark",
    "sweep_order": "toggles_first",
    "stop_after_timeout": True,
    "stop_after_error": True,
    # Algorithms listed here are not cut off on the first timeout/error.
    # The benchmark removes them only after the failure count becomes greater
    # than the configured limit, so 10 means "allow 10 failures, stop on 11".
    "algorithm_failure_limits": {"greedy": 10},
    # Override the number of boards sampled for specific algorithms.
    # GF(2) is measured once per size/toggle pair because its runtime is
    # highly stable for that combination.
    "algorithm_board_samples": {"gf2": 1},
}

ALGORITHM_LABELS = {
    "bfs": "BFS",
    "ucs": "UCS",
    "greedy": "Greedy",
    "astar": "A*",
    "wastar": "Weighted A*",
    "gf2": "GF(2)",
    "random_player": "Random Player",
}

METRIC_EXCLUSIONS = {
    "gf2": {"visited_states"},
}

RAW_FIELDNAMES = [
    "algorithm",
    "algorithm_label",
    "size",
    "toggle_count",
    "board_index",
    "board_seed",
    "board_matrix",
    "status",
    "solved",
    "execution_time_s",
    "visited_states",
    "solution_steps",
    "error_message",
    "cutoff_triggered",
]

SUMMARY_FIELDNAMES = [
    "algorithm",
    "algorithm_label",
    "size",
    "toggle_count",
    "runs",
    "planned_runs",
    "solved_runs",
    "finished_runs",
    "timeout_runs",
    "error_runs",
    "avg_execution_time_s",
    "min_execution_time_s",
    "max_execution_time_s",
    "avg_visited_states",
    "min_visited_states",
    "max_visited_states",
    "avg_solution_steps",
    "min_solution_steps",
    "max_solution_steps",
    "avg_states_per_second",
    "min_states_per_second",
    "max_states_per_second",
    "avg_execution_time_per_solution_step_s",
    "min_execution_time_per_solution_step_s",
    "max_execution_time_per_solution_step_s",
    "avg_visited_states_per_solution_step",
    "min_visited_states_per_solution_step",
    "max_visited_states_per_solution_step",
    "execution_time_ratio_vs_gf2",
]


def log(message):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def resolve_settings(overrides=None):
    settings = dict(DEFAULT_SETTINGS)
    settings["output_root"] = Path(settings["output_root"])
    settings["algorithm_failure_limits"] = dict(settings.get("algorithm_failure_limits", {}))
    settings["algorithm_board_samples"] = dict(settings.get("algorithm_board_samples", {}))

    if not overrides:
        return settings

    for key, value in overrides.items():
        if value is None:
            continue
        if key == "output_root":
            settings[key] = Path(value)
        elif key == "algorithm_failure_limits":
            settings[key] = dict(value)
        elif key == "algorithm_board_samples":
            settings[key] = dict(value)
        else:
            settings[key] = value
    return settings


def resolve_run_paths(settings, run_name=None):
    run_name = run_name or settings["run_name"]
    run_dir = Path(settings["output_root"]) / run_name
    return {
        "run_dir": run_dir,
        "raw_csv": run_dir / "benchmark_raw.csv",
        "summary_csv": run_dir / "benchmark_summary.csv",
        "settings_json": run_dir / "benchmark_settings.json",
        "plots_dir": run_dir / "plots",
    }


def write_settings_file(settings, path):
    serializable = {}
    for key, value in settings.items():
        if isinstance(value, Path):
            serializable[key] = str(value)
        else:
            serializable[key] = value

    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(serializable, file_handle, indent=2)


def valid_toggle_counts(size, toggle_counts):
    return [toggle for toggle in toggle_counts if 0 < toggle <= size * size]


def board_seed_for(size, toggle_count, board_index, base_seed):
    return int(base_seed + size * 1_000_000 + toggle_count * 1_000 + board_index)


def build_board(size, toggle_count, board_seed):
    rng = random.Random(board_seed)
    return Board.random_board(size, toggle_count, rng=rng)


def runs_per_combination(settings, algorithm):
    default_runs = settings["boards_per_combination"]
    override = settings.get("algorithm_board_samples", {}).get(algorithm, default_runs)
    return max(1, min(default_runs, int(override)))


def planned_run_count(settings):
    total_combinations = sum(1 for _ in generate_case_sequence(settings))
    runs_per_case = sum(runs_per_combination(settings, algorithm) for algorithm in settings["algorithms"])
    return total_combinations * runs_per_case


def generate_case_sequence(settings):
    sweep_order = settings.get("sweep_order", "toggles_first")

    if sweep_order == "toggles_first":
        for toggle_count in settings["toggle_counts"]:
            for size in settings["board_sizes"]:
                if 0 < toggle_count <= size * size:
                    yield size, toggle_count
        return

    if sweep_order == "sizes_first":
        for size in settings["board_sizes"]:
            for toggle_count in valid_toggle_counts(size, settings["toggle_counts"]):
                yield size, toggle_count
        return

    raise ValueError(
        f"Unsupported sweep order '{sweep_order}'. "
        "Use 'toggles_first' or 'sizes_first'."
    )


def _worker_entry(result_queue, algorithm, board_matrix, board_size, random_seed):
    try:
        from src import gf2_solver, random_player, solver
        from src.board import Board

        board = Board(board_matrix, board_size, [])

        if algorithm == "gf2":
            solutions = gf2_solver.solve(board)
        elif algorithm == "random_player":
            solutions = random_player.solve(board, rng=random.Random(random_seed))
        else:
            solutions = solver.solve(board, algorithm)

        if not solutions:
            raise RuntimeError(f"Algorithm '{algorithm}' returned no result payload.")

        _, result_node, elapsed, metrics = solutions[0]
        solved = result_node is not None and result_node.state.is_solved()
        solution_steps = len(result_node.state.moves) if result_node is not None else None
        visited_states = metrics.get("visited_states")
        if "visited_states" in METRIC_EXCLUSIONS.get(algorithm, set()):
            visited_states = None

        result_queue.put({
            "status": "solved" if solved else "no_solution",
            "execution_time_s": float(elapsed),
            "visited_states": visited_states,
            "solution_steps": solution_steps,
            "solved": bool(solved),
        })
    except Exception:
        result_queue.put({
            "status": "error",
            "error_message": traceback.format_exc(),
        })


def run_algorithm_with_timeout(algorithm, board, timeout_seconds, board_seed):
    context = mp.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(
        target=_worker_entry,
        args=(result_queue, algorithm, board.matrix, board.size, board_seed + 97_531),
    )

    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join()
        if hasattr(process, "close"):
            process.close()
        result_queue.close()
        return {
            "status": "timeout",
            "solved": False,
            "execution_time_s": float(timeout_seconds),
            "visited_states": None,
            "solution_steps": None,
            "error_message": "",
        }

    try:
        result = result_queue.get(timeout=0.2)
        result.setdefault("error_message", "")
        if hasattr(process, "close"):
            process.close()
        result_queue.close()
        return result
    except queue.Empty:
        if hasattr(process, "close"):
            process.close()
        result_queue.close()

    return {
        "status": "error",
        "solved": False,
        "execution_time_s": None,
        "visited_states": None,
        "solution_steps": None,
        "error_message": f"Worker exited without reporting a result (exit code {process.exitcode}).",
    }


def initialize_raw_csv(path):
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=RAW_FIELDNAMES)
        writer.writeheader()


def append_raw_row(path, row):
    with path.open("a", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=RAW_FIELDNAMES)
        writer.writerow(row)


def summarize_rows(raw_rows, settings):
    grouped_rows = {}
    for row in raw_rows:
        key = (row["algorithm"], row["size"], row["toggle_count"])
        grouped_rows.setdefault(key, []).append(row)

    summary_rows = []
    for algorithm, size, toggle_count in sorted(grouped_rows):
        rows = grouped_rows[(algorithm, size, toggle_count)]
        finished_rows = [row for row in rows if row["status"] in {"solved", "no_solution"}]
        solved_rows = [row for row in rows if row["status"] == "solved"]
        excluded_metrics = METRIC_EXCLUSIONS.get(algorithm, set())

        execution_times = [float(row["execution_time_s"]) for row in finished_rows if row["execution_time_s"] not in ("", None)]
        if "visited_states" in excluded_metrics:
            visited_states = []
        else:
            visited_states = [int(row["visited_states"]) for row in finished_rows if row["visited_states"] not in ("", None)]
        solution_steps = [int(row["solution_steps"]) for row in solved_rows if row["solution_steps"] not in ("", None)]
        states_per_second = [
            int(row["visited_states"]) / float(row["execution_time_s"])
            for row in finished_rows
            if row["visited_states"] not in ("", None) and row["execution_time_s"] not in ("", None) and float(row["execution_time_s"]) > 0
        ]
        execution_time_per_solution_step = [
            float(row["execution_time_s"]) / int(row["solution_steps"])
            for row in solved_rows
            if row["execution_time_s"] not in ("", None) and row["solution_steps"] not in ("", None) and int(row["solution_steps"]) > 0
        ]
        visited_states_per_solution_step = [
            int(row["visited_states"]) / int(row["solution_steps"])
            for row in solved_rows
            if row["visited_states"] not in ("", None) and row["solution_steps"] not in ("", None) and int(row["solution_steps"]) > 0
        ]

        summary_rows.append({
            "algorithm": algorithm,
            "algorithm_label": ALGORITHM_LABELS.get(algorithm, algorithm.upper()),
            "size": size,
            "toggle_count": toggle_count,
            "runs": len(rows),
            "planned_runs": runs_per_combination(settings, algorithm),
            "solved_runs": sum(1 for row in rows if row["status"] == "solved"),
            "finished_runs": len(finished_rows),
            "timeout_runs": sum(1 for row in rows if row["status"] == "timeout"),
            "error_runs": sum(1 for row in rows if row["status"] == "error"),
            "avg_execution_time_s": _mean_or_blank(execution_times),
            "min_execution_time_s": _min_or_blank(execution_times),
            "max_execution_time_s": _max_or_blank(execution_times),
            "avg_visited_states": _mean_or_blank(visited_states),
            "min_visited_states": _min_or_blank(visited_states),
            "max_visited_states": _max_or_blank(visited_states),
            "avg_solution_steps": _mean_or_blank(solution_steps),
            "min_solution_steps": _min_or_blank(solution_steps),
            "max_solution_steps": _max_or_blank(solution_steps),
            "avg_states_per_second": _mean_or_blank(states_per_second),
            "min_states_per_second": _min_or_blank(states_per_second),
            "max_states_per_second": _max_or_blank(states_per_second),
            "avg_execution_time_per_solution_step_s": _mean_or_blank(execution_time_per_solution_step),
            "min_execution_time_per_solution_step_s": _min_or_blank(execution_time_per_solution_step),
            "max_execution_time_per_solution_step_s": _max_or_blank(execution_time_per_solution_step),
            "avg_visited_states_per_solution_step": _mean_or_blank(visited_states_per_solution_step),
            "min_visited_states_per_solution_step": _min_or_blank(visited_states_per_solution_step),
            "max_visited_states_per_solution_step": _max_or_blank(visited_states_per_solution_step),
            "execution_time_ratio_vs_gf2": "",
        })

    gf2_time_lookup = {
        (row["size"], row["toggle_count"]): row["avg_execution_time_s"]
        for row in summary_rows
        if row["algorithm"] == "gf2" and row["avg_execution_time_s"] not in ("", None)
    }
    for row in summary_rows:
        gf2_time = gf2_time_lookup.get((row["size"], row["toggle_count"]))
        if gf2_time in ("", None) or row["avg_execution_time_s"] in ("", None):
            continue
        if float(gf2_time) <= 0:
            continue
        row["execution_time_ratio_vs_gf2"] = float(row["avg_execution_time_s"]) / float(gf2_time)

    return summary_rows


def _mean_or_blank(values):
    if not values:
        return ""
    return sum(values) / len(values)


def _min_or_blank(values):
    if not values:
        return ""
    return min(values)


def _max_or_blank(values):
    if not values:
        return ""
    return max(values)


def write_summary_csv(path, summary_rows):
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(summary_rows)


def print_run_result(processed_runs, total_runs, algorithm, size, toggle_count, board_index, result):
    label = ALGORITHM_LABELS.get(algorithm, algorithm.upper())
    prefix = f"Run {processed_runs}/{total_runs} | {label:12} | {size}x{size} | toggles={toggle_count:3d} | board {board_index + 1}"
    states_text = result["visited_states"] if result.get("visited_states") is not None else "-"
    steps_text = result["solution_steps"] if result.get("solution_steps") is not None else "-"

    if result["status"] == "solved":
        log(
            f"{prefix} | solved | time={result['execution_time_s']:.4f}s | "
            f"states={states_text} | steps={steps_text}"
        )
        return

    if result["status"] == "no_solution":
        log(
            f"{prefix} | no solution | time={result['execution_time_s']:.4f}s | "
            f"states={states_text}"
        )
        return

    if result["status"] == "timeout":
        log(f"{prefix} | TIMEOUT after {result['execution_time_s']:.2f}s")
        return

    error_text = (result.get("error_message") or "").strip().splitlines()
    first_line = error_text[-1] if error_text else "Unknown error"
    log(f"{prefix} | ERROR | {first_line}")


def _handle_algorithm_failure(
    algorithm,
    result,
    settings,
    active_algorithms,
    cutoff_algorithms,
    failure_counts,
    size,
    toggle_count,
    board_index,
):
    status = result["status"]
    if status not in {"timeout", "error"}:
        return False

    if status == "timeout" and not settings["stop_after_timeout"]:
        return False
    if status == "error" and not settings["stop_after_error"]:
        return False

    failure_limit = settings.get("algorithm_failure_limits", {}).get(algorithm)
    if failure_limit is not None:
        failure_counts[algorithm] = failure_counts.get(algorithm, 0) + 1
        failure_count = failure_counts[algorithm]

        if failure_count <= failure_limit:
            log(
                f"{ALGORITHM_LABELS.get(algorithm, algorithm.upper())} {status} "
                f"{failure_count}/{failure_limit} tolerated; continuing benchmark."
            )
            return False
    else:
        failure_count = failure_counts.get(algorithm, 0)
        failure_limit = None

    if algorithm in active_algorithms:
        active_algorithms.remove(algorithm)

    cutoff_algorithms[algorithm] = {
        "reason": status,
        "size": size,
        "toggle_count": toggle_count,
        "board_index": board_index,
        "failure_count": failure_counts.get(algorithm, 0),
        "failure_limit": failure_limit,
    }
    return True


def run_benchmark(settings=None, run_name=None):
    settings = resolve_settings(settings)
    paths = resolve_run_paths(settings, run_name=run_name)
    paths["run_dir"].mkdir(parents=True, exist_ok=True)
    paths["plots_dir"].mkdir(parents=True, exist_ok=True)

    initialize_raw_csv(paths["raw_csv"])
    write_settings_file(settings, paths["settings_json"])

    raw_rows = []
    active_algorithms = list(settings["algorithms"])
    cutoff_algorithms = {}
    failure_counts = {algorithm: 0 for algorithm in active_algorithms}
    processed_runs = 0
    total_runs = planned_run_count(settings)
    sweep_order = settings.get("sweep_order", "toggles_first")

    log(f"Benchmark run: {paths['run_dir']}")
    log(f"Algorithms: {', '.join(ALGORITHM_LABELS.get(name, name.upper()) for name in active_algorithms)}")
    log(f"Board sizes: {settings['board_sizes']}")
    log(f"Toggle counts: {settings['toggle_counts']}")
    if settings.get("algorithm_board_samples"):
        log(
            "Board samples per size/toggle pair: "
            + ", ".join(
                f"{ALGORITHM_LABELS.get(algorithm, algorithm.upper())}={runs_per_combination(settings, algorithm)}"
                for algorithm in settings["algorithms"]
                if algorithm in settings["algorithm_board_samples"]
            )
        )
    if settings.get("algorithm_failure_limits"):
        log(
            "Failure limits before cutoff: "
            + ", ".join(
                f"{ALGORITHM_LABELS.get(algorithm, algorithm.upper())}={limit}"
                for algorithm, limit in settings["algorithm_failure_limits"].items()
            )
        )
    if sweep_order == "toggles_first":
        log("Sweep order: toggles first, then board size. This preserves more cross-size data before hard boards cut algorithms off.")
    else:
        log("Sweep order: board size first, then toggle count.")
    log(
        "Each size/toggle pair uses "
        f"{settings['boards_per_combination']} boards with timeout {settings['timeout_seconds']:.1f}s."
    )

    stop_all = False
    current_group_key = None

    for size, toggle_count in generate_case_sequence(settings):
        if stop_all or not active_algorithms:
            break

        group_key = toggle_count if sweep_order == "toggles_first" else size
        if group_key != current_group_key:
            current_group_key = group_key
            if sweep_order == "toggles_first":
                valid_sizes = [candidate for candidate in settings["board_sizes"] if 0 < toggle_count <= candidate * candidate]
                log(
                    f"Starting toggle count {toggle_count} across sizes {valid_sizes} "
                    f"with active algorithms {', '.join(ALGORITHM_LABELS.get(name, name.upper()) for name in active_algorithms)}"
                )
            else:
                size_toggle_counts = valid_toggle_counts(size, settings["toggle_counts"])
                log(
                    f"Starting size {size}x{size} with toggles {size_toggle_counts} "
                    f"and active algorithms {', '.join(ALGORITHM_LABELS.get(name, name.upper()) for name in active_algorithms)}"
                )

        log(f"Preparing boards for {size}x{size} with {toggle_count} random toggles.")

        for board_index in range(settings["boards_per_combination"]):
            if stop_all or not active_algorithms:
                break

            board_seed = board_seed_for(size, toggle_count, board_index, settings["base_seed"])
            board = build_board(size, toggle_count, board_seed)
            log(
                f"Board {board_index + 1}/{settings['boards_per_combination']} ready "
                f"(seed={board_seed}, matrix=0x{board.matrix:x})."
            )

            for algorithm in list(active_algorithms):
                if board_index >= runs_per_combination(settings, algorithm):
                    continue

                processed_runs += 1
                result = run_algorithm_with_timeout(
                    algorithm,
                    board,
                    settings["timeout_seconds"],
                    board_seed,
                )
                cutoff_triggered = False

                cutoff_triggered = _handle_algorithm_failure(
                    algorithm,
                    result,
                    settings,
                    active_algorithms,
                    cutoff_algorithms,
                    failure_counts,
                    size,
                    toggle_count,
                    board_index,
                )
                if cutoff_triggered:
                    cutoff_details = cutoff_algorithms[algorithm]
                    if cutoff_details["failure_limit"] is None:
                        limit_text = "first failure"
                    else:
                        limit_text = (
                            f"{cutoff_details['failure_count']} failures "
                            f"(limit {cutoff_details['failure_limit']})"
                        )
                    log(
                        f"Cutting off {ALGORITHM_LABELS.get(algorithm, algorithm.upper())} after {result['status']} "
                        f"at {size}x{size}, {toggle_count} toggles, board {board_index + 1} "
                        f"because it reached {limit_text}."
                    )

                row = {
                    "algorithm": algorithm,
                    "algorithm_label": ALGORITHM_LABELS.get(algorithm, algorithm.upper()),
                    "size": size,
                    "toggle_count": toggle_count,
                    "board_index": board_index,
                    "board_seed": board_seed,
                    "board_matrix": f"0x{board.matrix:x}",
                    "status": result["status"],
                    "solved": int(bool(result.get("solved"))),
                    "execution_time_s": (
                        "" if result.get("execution_time_s") is None else result.get("execution_time_s")
                    ),
                    "visited_states": (
                        "" if result.get("visited_states") is None else result.get("visited_states")
                    ),
                    "solution_steps": (
                        "" if result.get("solution_steps") is None else result.get("solution_steps")
                    ),
                    "error_message": result.get("error_message", ""),
                    "cutoff_triggered": int(cutoff_triggered),
                }
                raw_rows.append(row)
                append_raw_row(paths["raw_csv"], row)
                print_run_result(processed_runs, total_runs, algorithm, size, toggle_count, board_index, result)

            if not active_algorithms:
                log("All algorithms have been cut off. Stopping the benchmark early.")
                stop_all = True

    summary_rows = summarize_rows(raw_rows, settings)
    write_summary_csv(paths["summary_csv"], summary_rows)

    log(f"Benchmark complete. Raw data: {paths['raw_csv']}")
    log(f"Benchmark complete. Summary: {paths['summary_csv']}")
    if cutoff_algorithms:
        for algorithm, details in cutoff_algorithms.items():
            if details["failure_limit"] is None:
                failure_text = "first failure"
            else:
                failure_text = f"{details['failure_count']} failures (limit {details['failure_limit']})"
            log(
                f"{ALGORITHM_LABELS.get(algorithm, algorithm.upper())} stopped after {details['reason']} "
                f"at {details['size']}x{details['size']} with {details['toggle_count']} toggles "
                f"(board {details['board_index'] + 1}, {failure_text})."
            )

    return {
        "paths": paths,
        "raw_rows": raw_rows,
        "summary_rows": summary_rows,
        "cutoff_algorithms": cutoff_algorithms,
        "settings": settings,
    }


def build_arg_parser(add_help=True):
    parser = argparse.ArgumentParser(description="Run the Lights Out algorithm benchmark.", add_help=add_help)
    parser.add_argument("--run-name", help="Subdirectory name under the benchmark output root.")
    parser.add_argument("--output-root", help="Root directory where benchmark runs are written.")
    parser.add_argument("--sizes", nargs="+", type=int, help="Board sizes to benchmark.")
    parser.add_argument("--toggles", nargs="+", type=int, help="Random toggle counts to benchmark.")
    parser.add_argument("--algorithms", nargs="+", choices=sorted(ALGORITHM_LABELS), help="Algorithms to benchmark.")
    parser.add_argument("--boards-per-combination", type=int, help="How many boards to test for each size/toggle pair.")
    parser.add_argument("--timeout", type=float, dest="timeout_seconds", help="Per-run timeout in seconds.")
    parser.add_argument("--base-seed", type=int, help="Base random seed used to generate benchmark boards.")
    parser.add_argument(
        "--sweep-order",
        choices=["toggles_first", "sizes_first"],
        help="Benchmark order. 'toggles_first' collects low-toggle data across sizes before moving to harder boards.",
    )
    return parser


def settings_from_args(args):
    return resolve_settings({
        "run_name": args.run_name,
        "output_root": args.output_root,
        "board_sizes": args.sizes,
        "toggle_counts": args.toggles,
        "algorithms": args.algorithms,
        "boards_per_combination": args.boards_per_combination,
        "timeout_seconds": args.timeout_seconds,
        "base_seed": args.base_seed,
        "sweep_order": args.sweep_order,
    })


def main():
    args = build_arg_parser().parse_args()
    run_benchmark(settings=settings_from_args(args), run_name=args.run_name)


if __name__ == "__main__":
    main()
