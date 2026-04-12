import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from benchmark_test import (
    ALGORITHM_LABELS,
    DEFAULT_SETTINGS,
    METRIC_EXCLUSIONS,
    resolve_run_paths,
    resolve_settings,
    runs_per_combination,
)


PLOT_DPI = 180
ASTAR_FAMILY = ["gf2", "astar", "wastar"]

METRICS = {
    "execution_time_s": {
        "label": "Execution Time (s)",
        "yscale": "log",
        "statuses": {"solved", "no_solution"},
    },
    "visited_states": {
        "label": "Visited States",
        "yscale": "symlog",
        "statuses": {"solved", "no_solution"},
    },
    "solution_steps": {
        "label": "Solution Steps",
        "yscale": "linear",
        "statuses": {"solved"},
    },
}


def parse_float(value):
    if value in ("", None):
        return None
    return float(value)


def parse_int(value):
    if value in ("", None):
        return None
    return int(value)


def read_raw_rows(path):
    rows = []
    with Path(path).open("r", newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            rows.append({
                "algorithm": row["algorithm"],
                "algorithm_label": row["algorithm_label"],
                "size": int(row["size"]),
                "toggle_count": int(row["toggle_count"]),
                "board_index": int(row["board_index"]),
                "board_seed": int(row["board_seed"]),
                "board_matrix": row["board_matrix"],
                "status": row["status"],
                "solved": row["solved"] == "1",
                "execution_time_s": parse_float(row["execution_time_s"]),
                "visited_states": parse_int(row["visited_states"]),
                "solution_steps": parse_int(row["solution_steps"]),
                "error_message": row["error_message"],
                "cutoff_triggered": row["cutoff_triggered"] == "1",
            })
    return rows


def load_settings_file(path):
    path = Path(path)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file_handle:
        raw_settings = json.load(file_handle)

    return resolve_settings(raw_settings)


def algorithm_order(rows, preferred=None):
    seen = {row["algorithm"] for row in rows}
    preferred = preferred or DEFAULT_SETTINGS["algorithms"]
    ordered = [algorithm for algorithm in preferred if algorithm in seen]
    extras = sorted(seen - set(ordered))
    return ordered + extras


def algorithm_colors(rows):
    algorithms = algorithm_order(rows)
    cmap = plt.get_cmap("tab10")
    return {
        algorithm: cmap(index % cmap.N)
        for index, algorithm in enumerate(algorithms)
    }


def sorted_field_values(rows, field):
    return sorted({row[field] for row in rows})


def padded_plot_name(prefix, value):
    return f"{prefix}_{int(value):03d}.png"


def ensure_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def clear_plot_outputs(plots_dir):
    plots_dir = ensure_directory(plots_dir)
    for existing_plot in plots_dir.rglob("*.png"):
        existing_plot.unlink()

    for existing_dir in sorted(
        (path for path in plots_dir.rglob("*") if path.is_dir()),
        reverse=True,
    ):
        if not any(existing_dir.iterdir()):
            existing_dir.rmdir()

    return plots_dir


def metric_rows(rows, metric_key, algorithms=None):
    allowed_statuses = METRICS[metric_key]["statuses"]
    filtered = [
        row for row in rows
        if (
            row["status"] in allowed_statuses
            and row[metric_key] is not None
            and metric_key not in METRIC_EXCLUSIONS.get(row["algorithm"], set())
        )
    ]
    if algorithms is not None:
        filtered = [row for row in filtered if row["algorithm"] in algorithms]
    return filtered


def grouped_stats(rows, group_fields, metric_key):
    grouped = {}
    for row in rows:
        key = tuple(row[field] for field in group_fields)
        grouped.setdefault(key, []).append(row[metric_key])

    stats = {}
    for key, values in grouped.items():
        stats[key] = {
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }
    return stats


def custom_metric_rows(rows, value_builder, algorithms=None):
    filtered_rows = []
    for row in rows:
        if algorithms is not None and row["algorithm"] not in algorithms:
            continue

        value = value_builder(row)
        if value is None:
            continue

        enriched_row = dict(row)
        enriched_row["metric_value"] = value
        filtered_rows.append(enriched_row)

    return filtered_rows


def grouped_metric_value_stats(rows, group_fields):
    grouped = {}
    for row in rows:
        key = tuple(row[field] for field in group_fields)
        grouped.setdefault(key, []).append(row["metric_value"])

    stats = {}
    for key, values in grouped.items():
        stats[key] = {
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }
    return stats


def comparison_candidate_rows(rows):
    non_gf2_rows = [row for row in rows if row["algorithm"] != "gf2"]
    return non_gf2_rows if non_gf2_rows else rows


def gf2_extension_limit(panel_rows, x_field):
    non_gf2_xs = sorted({row[x_field] for row in panel_rows if row["algorithm"] != "gf2"})
    if not non_gf2_xs:
        return None

    last_non_gf2_x = non_gf2_xs[-1]
    gf2_xs = sorted({row[x_field] for row in panel_rows if row["algorithm"] == "gf2"})
    next_gf2_x = next((x_value for x_value in gf2_xs if x_value > last_non_gf2_x), None)
    return next_gf2_x if next_gf2_x is not None else last_non_gf2_x


def trim_gf2_points(points, panel_rows, x_field):
    if not points:
        return points

    max_allowed_x = gf2_extension_limit(panel_rows, x_field)
    if max_allowed_x is None:
        return []

    return [point for point in points if point[0] <= max_allowed_x]


def astar_family_comparison_sizes(rows):
    search_sizes = {
        row["size"]
        for row in rows
        if row["algorithm"] in {"astar", "wastar"}
    }
    filtered_rows = [row for row in rows if row["size"] in search_sizes]
    return sorted_field_values(filtered_rows, "size")


def astar_family_toggle_window(size_rows):
    toggle_counts = sorted({
        row["toggle_count"]
        for row in size_rows
        if row["algorithm"] in {"astar", "wastar"}
    })
    if not toggle_counts:
        return []
    max_toggle = max(toggle_counts)
    gf2_toggles = sorted({row["toggle_count"] for row in size_rows if row["algorithm"] == "gf2"})
    next_gf2_toggle = next((toggle_count for toggle_count in gf2_toggles if toggle_count > max_toggle), None)
    max_allowed_toggle = next_gf2_toggle if next_gf2_toggle is not None else max_toggle
    all_toggles = sorted({row["toggle_count"] for row in size_rows})
    return [toggle_count for toggle_count in all_toggles if toggle_count <= max_allowed_toggle]


def create_subplot_grid(panel_count):
    cols = 2 if panel_count > 1 else 1
    rows = math.ceil(panel_count / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(13.8, 4.9 * rows), squeeze=False)
    return fig, axes.flatten()


def save_figure(fig, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=PLOT_DPI, bbox_inches="tight", pad_inches=0.25)


def collect_legend_entries(axes):
    entries = {}
    for axis in axes:
        handles, labels = axis.get_legend_handles_labels()
        for handle, label in zip(handles, labels):
            if label not in entries:
                entries[label] = handle
    return list(entries.values()), list(entries.keys())


def finish_figure(fig, axes, output_path, *, legend_outside=True, title=None):
    handles, labels = collect_legend_entries(axes)
    if title:
        fig.suptitle(title, y=0.99)

    rect = (0, 0, 1, 0.95)
    if handles:
        fig.legend(
            handles,
            labels,
            loc="center left",
            bbox_to_anchor=(1.01, 0.5),
            frameon=False,
        )
        rect = (0, 0, 0.82, 0.95)

    fig.tight_layout(rect=rect)
    save_figure(fig, output_path)
    plt.close(fig)


def apply_metric_scale(axis, metric_key, timeout_seconds=None):
    scale = METRICS[metric_key]["yscale"]
    if scale == "log":
        axis.set_yscale("log")
    elif scale == "symlog":
        axis.set_yscale("symlog", linthresh=1.0)


def finalize_single_axis_plot(fig, axis, output_path, *, title=None):
    if not axis.has_data():
        plt.close(fig)
        return False

    finish_figure(fig, [axis], output_path, title=title)
    return True


def plot_metric_vs_size(rows, metric_key, output_dir, timeout_seconds=None):
    filtered_rows = metric_rows(rows, metric_key)
    toggle_counts = sorted_field_values(filtered_rows, "toggle_count")
    if not toggle_counts:
        return

    colors = algorithm_colors(filtered_rows)
    output_dir = ensure_directory(output_dir)

    for toggle_count in toggle_counts:
        toggle_rows = [row for row in filtered_rows if row["toggle_count"] == toggle_count]
        fig, axis = plt.subplots(figsize=(10.8, 6.0))
        sizes = sorted({row["size"] for row in toggle_rows})
        stats = grouped_stats(toggle_rows, ("algorithm", "size"), metric_key)

        for algorithm in algorithm_order(toggle_rows):
            points = []
            for size in sizes:
                point = stats.get((algorithm, size))
                if point is not None:
                    points.append((size, point["mean"], point["min"], point["max"]))

            if algorithm == "gf2":
                points = trim_gf2_points(points, toggle_rows, "size")
            if not points:
                continue

            xs = [point[0] for point in points]
            means = [point[1] for point in points]
            mins = [point[2] for point in points]
            maxs = [point[3] for point in points]
            color = colors[algorithm]

            axis.plot(xs, means, marker="o", linewidth=2, color=color, label=ALGORITHM_LABELS.get(algorithm, algorithm.upper()))
            axis.fill_between(xs, mins, maxs, color=color, alpha=0.16)

        apply_metric_scale(axis, metric_key, timeout_seconds=timeout_seconds if metric_key == "execution_time_s" else None)
        axis.set_title(f"{METRICS[metric_key]['label']} vs Board Size\n{toggle_count} Random Toggles")
        axis.set_xlabel("Board Size")
        axis.set_ylabel(METRICS[metric_key]["label"])
        axis.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)

        finalize_single_axis_plot(
            fig,
            axis,
            output_dir / padded_plot_name("toggle", toggle_count),
        )


def plot_metric_vs_toggles(rows, metric_key, output_dir, timeout_seconds=None):
    filtered_rows = metric_rows(rows, metric_key)
    sizes = sorted_field_values(filtered_rows, "size")
    if not sizes:
        return

    colors = algorithm_colors(filtered_rows)
    output_dir = ensure_directory(output_dir)

    for size in sizes:
        size_rows = [row for row in filtered_rows if row["size"] == size]
        fig, axis = plt.subplots(figsize=(10.8, 6.0))
        toggle_counts = sorted({row["toggle_count"] for row in size_rows})
        stats = grouped_stats(size_rows, ("algorithm", "size", "toggle_count"), metric_key)

        for algorithm in algorithm_order(size_rows):
            points = []
            for toggle_count in toggle_counts:
                point = stats.get((algorithm, size, toggle_count))
                if point is not None:
                    points.append((toggle_count, point["mean"], point["min"], point["max"]))

            if algorithm == "gf2":
                points = trim_gf2_points(points, size_rows, "toggle_count")
            if not points:
                continue

            xs = [point[0] for point in points]
            means = [point[1] for point in points]
            mins = [point[2] for point in points]
            maxs = [point[3] for point in points]
            color = colors[algorithm]

            axis.plot(xs, means, marker="o", linewidth=2, color=color, label=ALGORITHM_LABELS.get(algorithm, algorithm.upper()))
            axis.fill_between(xs, mins, maxs, color=color, alpha=0.16)

        apply_metric_scale(axis, metric_key, timeout_seconds=timeout_seconds if metric_key == "execution_time_s" else None)
        axis.set_title(f"{METRICS[metric_key]['label']} vs Random Toggle Count\n{size}x{size} Boards")
        axis.set_xlabel("Random Toggle Count")
        axis.set_ylabel(METRICS[metric_key]["label"])
        axis.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)

        finalize_single_axis_plot(
            fig,
            axis,
            output_dir / padded_plot_name("size", size),
        )


def plot_custom_metric_vs_toggles(rows, output_dir, *, title, ylabel, yscale, value_builder, algorithms=None):
    filtered_rows = custom_metric_rows(rows, value_builder, algorithms=algorithms)
    sizes = sorted_field_values(filtered_rows, "size")
    if not sizes:
        return

    colors = algorithm_colors(filtered_rows)
    output_dir = ensure_directory(output_dir)

    for size in sizes:
        size_rows = [row for row in filtered_rows if row["size"] == size]
        fig, axis = plt.subplots(figsize=(10.8, 6.0))
        toggle_counts = sorted({row["toggle_count"] for row in size_rows})
        stats = grouped_metric_value_stats(size_rows, ("algorithm", "size", "toggle_count"))

        for algorithm in algorithm_order(size_rows):
            points = []
            for toggle_count in toggle_counts:
                point = stats.get((algorithm, size, toggle_count))
                if point is not None:
                    points.append((toggle_count, point["mean"], point["min"], point["max"]))

            if not points:
                continue

            xs = [point[0] for point in points]
            means = [point[1] for point in points]
            mins = [point[2] for point in points]
            maxs = [point[3] for point in points]
            axis.plot(xs, means, marker="o", linewidth=2, color=colors[algorithm], label=ALGORITHM_LABELS.get(algorithm, algorithm.upper()))
            axis.fill_between(xs, mins, maxs, color=colors[algorithm], alpha=0.16)

        if yscale == "log":
            axis.set_yscale("log")
        elif yscale == "symlog":
            axis.set_yscale("symlog", linthresh=1.0)

        axis.set_title(f"{size}x{size} Boards")
        axis.set_xlabel("Random Toggle Count")
        axis.set_ylabel(ylabel)
        axis.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)

        finalize_single_axis_plot(
            fig,
            axis,
            output_dir / padded_plot_name("size", size),
            title=title,
        )


def plot_time_ratio_vs_gf2(rows, output_dir):
    filtered_rows = metric_rows(rows, "execution_time_s")
    comparison_rows = [row for row in filtered_rows if row["algorithm"] != "gf2"]
    sizes = sorted_field_values(comparison_rows, "size")
    if not sizes:
        return

    colors = algorithm_colors(filtered_rows)
    output_dir = ensure_directory(output_dir)

    for size in sizes:
        size_rows = [row for row in filtered_rows if row["size"] == size]
        fig, axis = plt.subplots(figsize=(10.8, 6.0))
        stats = grouped_stats(size_rows, ("algorithm", "size", "toggle_count"), "execution_time_s")
        toggle_counts = sorted({row["toggle_count"] for row in size_rows if row["algorithm"] != "gf2"})

        for algorithm in algorithm_order(size_rows):
            if algorithm == "gf2":
                continue

            points = []
            for toggle_count in toggle_counts:
                algorithm_point = stats.get((algorithm, size, toggle_count))
                gf2_point = stats.get(("gf2", size, toggle_count))
                if algorithm_point is None or gf2_point is None:
                    continue
                if gf2_point["mean"] <= 0:
                    continue
                ratio = algorithm_point["mean"] / gf2_point["mean"]
                points.append((toggle_count, ratio))

            if not points:
                continue

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            axis.plot(xs, ys, marker="o", linewidth=2, color=colors[algorithm], label=ALGORITHM_LABELS.get(algorithm, algorithm.upper()))

        axis.axhline(1.0, color="gray", linestyle="--", linewidth=1.0, label="GF(2) parity")
        axis.set_yscale("log")
        axis.set_title(f"Runtime Ratio Against GF(2)\n{size}x{size} Boards")
        axis.set_xlabel("Random Toggle Count")
        axis.set_ylabel("Execution Time / GF(2) Time")
        axis.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)

        finalize_single_axis_plot(
            fig,
            axis,
            output_dir / padded_plot_name("size", size),
            title="Runtime Ratio Against GF(2)\nValues above 1.0 mean the search algorithm is slower than GF(2)",
        )


def plot_coverage(rows, output_path):
    if not rows:
        return

    algorithms = algorithm_order(rows)
    x_positions = list(range(len(algorithms)))
    solved_counts = []
    no_solution_counts = []
    timeout_counts = []
    error_counts = []

    for algorithm in algorithms:
        algorithm_rows = [row for row in rows if row["algorithm"] == algorithm]
        solved_counts.append(sum(1 for row in algorithm_rows if row["status"] == "solved"))
        no_solution_counts.append(sum(1 for row in algorithm_rows if row["status"] == "no_solution"))
        timeout_counts.append(sum(1 for row in algorithm_rows if row["status"] == "timeout"))
        error_counts.append(sum(1 for row in algorithm_rows if row["status"] == "error"))

    fig, ax = plt.subplots(figsize=(10.8, 6.0))
    ax.bar(x_positions, solved_counts, label="Solved", color="#4CAF50")
    ax.bar(x_positions, no_solution_counts, bottom=solved_counts, label="No Solution", color="#F0AD4E")
    ax.bar(
        x_positions,
        timeout_counts,
        bottom=[solved + no_solution for solved, no_solution in zip(solved_counts, no_solution_counts)],
        label="Timeout",
        color="#D9534F",
    )
    ax.bar(
        x_positions,
        error_counts,
        bottom=[
            solved + no_solution + timeout
            for solved, no_solution, timeout in zip(solved_counts, no_solution_counts, timeout_counts)
        ],
        label="Error",
        color="#6C757D",
    )

    ax.set_xticks(x_positions)
    ax.set_xticklabels([ALGORITHM_LABELS.get(algorithm, algorithm.upper()) for algorithm in algorithms])
    ax.set_ylabel("Number of Benchmark Runs")
    ax.set_title("Benchmark Coverage by Algorithm")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    fig.tight_layout(rect=(0, 0, 0.82, 1))
    fig.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)
    save_figure(fig, output_path)
    plt.close(fig)


def plot_completion_frontier(rows, output_path, settings=None):
    if not rows:
        return

    algorithms = algorithm_order(rows)
    sizes = sorted({row["size"] for row in rows})
    toggle_counts = sorted({row["toggle_count"] for row in rows})

    fig, axes = create_subplot_grid(len(algorithms))
    image = None

    for axis_index, algorithm in enumerate(algorithms):
        axis = axes[axis_index]
        matrix = np.full((len(sizes), len(toggle_counts)), np.nan)

        for size_index, size in enumerate(sizes):
            for toggle_index, toggle_count in enumerate(toggle_counts):
                combo_rows = [
                    row for row in rows
                    if row["algorithm"] == algorithm and row["size"] == size and row["toggle_count"] == toggle_count
                ]
                if not combo_rows:
                    continue

                finished_runs = sum(1 for row in combo_rows if row["status"] in {"solved", "no_solution"})
                planned_runs = (
                    runs_per_combination(settings, algorithm)
                    if settings is not None
                    else max(row["board_index"] for row in combo_rows) + 1
                )
                matrix[size_index, toggle_index] = min(1.0, finished_runs / planned_runs)

        image = axis.imshow(
            np.ma.masked_invalid(matrix),
            aspect="auto",
            origin="lower",
            vmin=0.0,
            vmax=1.0,
            cmap="viridis",
        )
        axis.set_title(ALGORITHM_LABELS.get(algorithm, algorithm.upper()))
        axis.set_xlabel("Random Toggle Count")
        axis.set_ylabel("Board Size")
        axis.set_xticks(range(len(toggle_counts)))
        axis.set_xticklabels(toggle_counts, rotation=45, ha="right", fontsize=8)
        axis.set_yticks(range(len(sizes)))
        axis.set_yticklabels(sizes)

    for axis in axes[len(algorithms):]:
        axis.remove()

    if image is not None:
        fig.colorbar(image, ax=axes[:len(algorithms)], fraction=0.025, pad=0.02, label="Finished board ratio")

    legend_handles = [
        Patch(facecolor=plt.get_cmap("viridis")(0.15), label="Lower completion ratio"),
        Patch(facecolor=plt.get_cmap("viridis")(0.85), label="Higher completion ratio"),
        Patch(facecolor="white", edgecolor="black", label="Blank cell = no benchmark data"),
    ]
    fig.legend(
        legend_handles,
        [handle.get_label() for handle in legend_handles],
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        frameon=False,
    )

    fig.suptitle(
        "Completion Frontier by Algorithm\n1.0 means all benchmark boards finished before timeout or cutoff",
        y=0.99,
    )
    fig.subplots_adjust(left=0.08, right=0.80, bottom=0.12, top=0.90, wspace=0.35, hspace=0.35)
    save_figure(fig, output_path)
    plt.close(fig)


def find_first_crossover(stats, size, candidate_algorithm, reference_algorithm="gf2"):
    toggle_counts = sorted({
        toggle_count
        for algorithm, current_size, toggle_count in stats
        if current_size == size and algorithm in {candidate_algorithm, reference_algorithm}
    })

    for toggle_count in toggle_counts:
        candidate = stats.get((candidate_algorithm, size, toggle_count))
        reference = stats.get((reference_algorithm, size, toggle_count))
        if candidate is None or reference is None:
            continue
        if candidate["mean"] > reference["mean"]:
            return {
                "toggle_count": toggle_count,
                "candidate_time": candidate["mean"],
                "reference_time": reference["mean"],
            }
    return None


def plot_astar_family_time_vs_toggles(rows, output_dir, timeout_seconds=None):
    filtered_rows = metric_rows(rows, "execution_time_s", algorithms=ASTAR_FAMILY)
    present_algorithms = algorithm_order(filtered_rows, preferred=ASTAR_FAMILY)
    if len(present_algorithms) < 2:
        return

    colors = algorithm_colors(filtered_rows)
    size_panels = astar_family_comparison_sizes(filtered_rows)
    if not size_panels:
        return

    output_dir = ensure_directory(output_dir)

    for size in size_panels:
        size_rows = [row for row in filtered_rows if row["size"] == size]
        fig, axis = plt.subplots(figsize=(10.8, 6.0))
        toggle_counts = astar_family_toggle_window(size_rows)
        if not toggle_counts:
            plt.close(fig)
            continue
        stats = grouped_stats(size_rows, ("algorithm", "size", "toggle_count"), "execution_time_s")

        for algorithm in present_algorithms:
            points = []
            for toggle_count in toggle_counts:
                point = stats.get((algorithm, size, toggle_count))
                if point is not None:
                    points.append((toggle_count, point["mean"]))

            if not points:
                continue

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            axis.plot(xs, ys, marker="o", linewidth=2, color=colors[algorithm], label=ALGORITHM_LABELS.get(algorithm, algorithm.upper()))

        for algorithm, label in (("astar", "A*"), ("wastar", "Weighted A*")):
            if algorithm not in present_algorithms or "gf2" not in present_algorithms:
                continue

            crossover = find_first_crossover(stats, size, algorithm, reference_algorithm="gf2")
            if crossover is None:
                continue

            axis.scatter(
                crossover["toggle_count"],
                crossover["candidate_time"],
                color=colors[algorithm],
                s=34,
                zorder=5,
            )
            axis.annotate(
                f"{label} > GF(2) at {crossover['toggle_count']}",
                xy=(crossover["toggle_count"], crossover["candidate_time"]),
                xytext=(8, 6),
                textcoords="offset points",
                fontsize=8,
                color=colors[algorithm],
            )

        apply_metric_scale(axis, "execution_time_s", timeout_seconds=timeout_seconds)
        axis.set_title(f"{size}x{size} Boards")
        axis.set_xlabel("Random Toggle Count")
        axis.set_ylabel("Execution Time (s)")
        axis.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)

        finalize_single_axis_plot(
            fig,
            axis,
            output_dir / padded_plot_name("size", size),
            title="GF(2) vs A* Family Execution Time\nAnnotated point = first observed toggle where the search solver becomes slower than GF(2)",
        )


def plot_astar_vs_wastar_ratio(rows, output_dir):
    filtered_rows = metric_rows(rows, "execution_time_s", algorithms=["astar", "wastar"])
    if len({row["algorithm"] for row in filtered_rows}) < 2:
        return

    size_panels = sorted_field_values(filtered_rows, "size")
    if not size_panels:
        return

    output_dir = ensure_directory(output_dir)

    for size in size_panels:
        size_rows = [row for row in filtered_rows if row["size"] == size]
        fig, axis = plt.subplots(figsize=(10.8, 6.0))
        stats = grouped_stats(size_rows, ("algorithm", "size", "toggle_count"), "execution_time_s")
        toggle_counts = sorted({
            toggle_count
            for algorithm, current_size, toggle_count in stats
            if current_size == size and {"astar", "wastar"} <= {
                entry_algorithm
                for entry_algorithm, entry_size, entry_toggle in stats
                if entry_size == size and entry_toggle == toggle_count
            }
        })

        if not toggle_counts:
            plt.close(fig)
            continue

        ratios = []
        for toggle_count in toggle_counts:
            astar_time = stats[("astar", size, toggle_count)]["mean"]
            wastar_time = stats[("wastar", size, toggle_count)]["mean"]
            ratios.append(astar_time / wastar_time)

        axis.plot(
            toggle_counts,
            ratios,
            marker="o",
            linewidth=2,
            color="#1f77b4",
            label="A* time / Weighted A* time",
        )
        axis.axhline(1.0, color="gray", linestyle="--", linewidth=1.0, label="Parity line")
        axis.set_title(f"{size}x{size} Boards")
        axis.set_xlabel("Random Toggle Count")
        axis.set_ylabel("A* Time / Weighted A* Time")
        axis.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)

        finalize_single_axis_plot(
            fig,
            axis,
            output_dir / padded_plot_name("size", size),
            title="A* vs Weighted A* Time Ratio\nValues above 1.0 mean Weighted A* is faster",
        )


def plot_astar_family_crossover(rows, output_path):
    filtered_rows = metric_rows(rows, "execution_time_s", algorithms=ASTAR_FAMILY)
    if "gf2" not in {row["algorithm"] for row in filtered_rows}:
        return

    stats = grouped_stats(filtered_rows, ("algorithm", "size", "toggle_count"), "execution_time_s")
    sizes = sorted({row["size"] for row in filtered_rows})
    crossover_series = {}

    for algorithm in ("astar", "wastar"):
        points = []
        for size in sizes:
            crossover = find_first_crossover(stats, size, algorithm, reference_algorithm="gf2")
            if crossover is not None:
                points.append((size, crossover["toggle_count"]))
        if points:
            crossover_series[algorithm] = points

    if not crossover_series:
        return

    fig, ax = plt.subplots(figsize=(10.8, 6.0))
    colors = algorithm_colors(filtered_rows)

    for algorithm, points in crossover_series.items():
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        ax.plot(
            xs,
            ys,
            marker="o",
            linewidth=2,
            color=colors[algorithm],
            label=f"{ALGORITHM_LABELS.get(algorithm, algorithm.upper())} crossover",
        )

    ax.set_xlabel("Board Size")
    ax.set_ylabel("First Observed Slower-Than-GF(2) Toggle Count")
    ax.set_title("GF(2) Crossover Point by Board Size")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)
    fig.tight_layout(rect=(0, 0, 0.82, 1))
    fig.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)
    save_figure(fig, output_path)
    plt.close(fig)


def generate_plots(raw_csv_path, plots_dir, timeout_seconds=None, settings=None):
    raw_rows = read_raw_rows(raw_csv_path)
    if settings is None:
        settings = load_settings_file(Path(raw_csv_path).parent / "benchmark_settings.json")
    plots_dir = clear_plot_outputs(plots_dir)

    metric_root = plots_dir / "metrics"
    derived_root = plots_dir / "derived"
    special_root = plots_dir / "special"
    summary_root = plots_dir / "summary"

    plot_metric_vs_size(
        raw_rows,
        "execution_time_s",
        metric_root / "execution_time" / "vs_size",
        timeout_seconds=timeout_seconds,
    )
    plot_metric_vs_size(
        raw_rows,
        "visited_states",
        metric_root / "visited_states" / "vs_size",
    )
    plot_metric_vs_size(
        raw_rows,
        "solution_steps",
        metric_root / "solution_steps" / "vs_size",
    )

    plot_metric_vs_toggles(
        raw_rows,
        "execution_time_s",
        metric_root / "execution_time" / "vs_toggles",
        timeout_seconds=timeout_seconds,
    )
    plot_metric_vs_toggles(
        raw_rows,
        "visited_states",
        metric_root / "visited_states" / "vs_toggles",
    )
    plot_metric_vs_toggles(
        raw_rows,
        "solution_steps",
        metric_root / "solution_steps" / "vs_toggles",
    )
    plot_custom_metric_vs_toggles(
        raw_rows,
        derived_root / "states_per_second" / "vs_toggles",
        title="Search Throughput vs Random Toggle Count\nHigher is better",
        ylabel="Visited States per Second",
        yscale="log",
        value_builder=lambda row: (
            row["visited_states"] / row["execution_time_s"]
            if row["visited_states"] is not None and row["execution_time_s"] is not None and row["execution_time_s"] > 0
            else None
        ),
    )
    plot_custom_metric_vs_toggles(
        raw_rows,
        derived_root / "visited_states_per_solution_step" / "vs_toggles",
        title="Search Effort per Solution Move vs Random Toggle Count\nHigher means the algorithm explores more states for each move in the final solution",
        ylabel="Visited States per Solution Step",
        yscale="log",
        value_builder=lambda row: (
            row["visited_states"] / row["solution_steps"]
            if row["visited_states"] is not None and row["solution_steps"] is not None and row["solution_steps"] > 0
            else None
        ),
    )
    plot_time_ratio_vs_gf2(raw_rows, derived_root / "time_ratio_vs_gf2" / "vs_toggles")

    plot_coverage(raw_rows, summary_root / "benchmark_coverage.png")
    plot_completion_frontier(raw_rows, summary_root / "completion_frontier.png", settings=settings)
    plot_astar_family_time_vs_toggles(
        raw_rows,
        special_root / "astar_family_vs_gf2" / "vs_toggles",
        timeout_seconds=timeout_seconds,
    )
    plot_astar_vs_wastar_ratio(
        raw_rows,
        special_root / "astar_vs_weighted_astar_ratio" / "vs_toggles",
    )
    plot_astar_family_crossover(raw_rows, special_root / "astar_family_gf2_crossover.png")
    return plots_dir


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Generate benchmark plots from benchmark CSV data.")
    parser.add_argument("--run-name", help="Benchmark run directory name under the benchmark output root.")
    parser.add_argument("--output-root", help="Root directory where benchmark runs are stored.")
    parser.add_argument("--raw-csv", help="Path to the raw benchmark CSV. Overrides run-name/output-root.")
    parser.add_argument("--plots-dir", help="Directory where plot images are written.")
    parser.add_argument("--timeout", type=float, help="Optional timeout line to overlay on execution-time plots.")
    return parser


def main():
    args = build_arg_parser().parse_args()
    settings = None

    if args.raw_csv:
        raw_csv_path = Path(args.raw_csv)
        plots_dir = Path(args.plots_dir) if args.plots_dir else raw_csv_path.parent / "plots"
        timeout_seconds = args.timeout
        settings = load_settings_file(raw_csv_path.parent / "benchmark_settings.json")
    else:
        settings = resolve_settings({"output_root": args.output_root} if args.output_root else None)
        paths = resolve_run_paths(settings, run_name=args.run_name or settings["run_name"])
        raw_csv_path = paths["raw_csv"]
        plots_dir = Path(args.plots_dir) if args.plots_dir else paths["plots_dir"]
        settings = load_settings_file(paths["settings_json"]) or settings
        timeout_seconds = args.timeout if args.timeout is not None else settings["timeout_seconds"]

    generate_plots(raw_csv_path, plots_dir, timeout_seconds=timeout_seconds, settings=settings)
    print(f"Plots written to {plots_dir}", flush=True)


if __name__ == "__main__":
    main()
