import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark suite")
    parser.add_argument("spec_path", help="Path to benchmark suite TOML")
    parser.add_argument("--out", default="results", help="Directory to save results")
    parser.add_argument(
        "-j", "--parallel", help="Number of benchmarks to run in parallel", default=1
    )

    args = parser.parse_args()

    # Load specification, validate it
    # Dispatch runner to run the benchmarks and generate results
    # Save results to directory


if __name__ == "__main__":
    main()
