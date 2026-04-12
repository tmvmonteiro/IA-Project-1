import argparse

from benchmark_plot import generate_plots
from benchmark_test import build_arg_parser as build_test_arg_parser
from benchmark_test import run_benchmark, settings_from_args


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run the Lights Out benchmark end-to-end and generate plots.",
        parents=[build_test_arg_parser(add_help=False)],
        add_help=True,
    )
    return parser


def main():
    args = build_arg_parser().parse_args()
    settings = settings_from_args(args)
    benchmark_result = run_benchmark(settings=settings, run_name=args.run_name)

    generate_plots(
        benchmark_result["paths"]["raw_csv"],
        benchmark_result["paths"]["plots_dir"],
        timeout_seconds=benchmark_result["settings"]["timeout_seconds"],
        settings=benchmark_result["settings"],
    )

    print(f"Benchmark data written to {benchmark_result['paths']['run_dir']}", flush=True)
    print(f"Plots written to {benchmark_result['paths']['plots_dir']}", flush=True)


if __name__ == "__main__":
    main()
