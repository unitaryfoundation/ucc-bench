import os
import requests
import pandas as pd
import sys
import argparse
from typing import Optional, Tuple
from ucc_bench.results import to_df_timing, SuiteResultsDatabase, SuiteResults

# Constants for configuration / API interaction seem reasonable to keep
DEFAULT_THRESHOLD = 10.0


def format_change(old: float, new: float, threshold: float = DEFAULT_THRESHOLD) -> str:
    """Formats the percentage change between old and new values.

    Highlights the change in Markdown bold if the absolute percentage change
    exceeds the threshold.

    Args:
        old: The old numerical value.
        new: The new numerical value.
        threshold: The percentage threshold for highlighting (default: 10.0).

    Returns:
        A string representing the formatted percentage change (e.g., "+5.2%", "**-15.0%**", "N/A").
    """
    if old == 0:
        return "N/A"  # Avoid division by zero
    delta = new - old
    percent = (delta / old) * 100
    # Use threshold for highlighting
    highlight = "**" if abs(percent) > threshold else ""
    return f"{highlight}{percent:+.1f}%{highlight}"


def build_comparison_table(
    df_old: pd.DataFrame, df_new: pd.DataFrame, threshold: float = DEFAULT_THRESHOLD
) -> pd.DataFrame:
    """
    Compares benchmark timing results between two dataframes using apply.

    Args:
        df_old: DataFrame with old results. Expected columns: 'compiler',
                'benchmark_id', 'compile_time_ms', 'compiled_multiq_gates'.
        df_new: DataFrame with new results. Expected columns match df_old.
        threshold: The percentage threshold for highlighting changes.

    Returns:
        A new DataFrame summarizing the comparison. Columns: 'Compiler',
        'Benchmark', 'Compile Time Δ', 'MultiQ Gates Δ'.
    """
    # Merge the dataframes
    merged = df_old.merge(
        df_new, on=["compiler", "benchmark_id"], suffixes=("_old", "_new"), how="inner"
    )

    # Create the comparison dataframe using apply (more idiomatic than iterrows)
    comparison_df = pd.DataFrame()
    comparison_df["Compiler"] = merged["compiler"]
    comparison_df["Benchmark"] = merged["benchmark_id"]

    comparison_df["Compile Time Base (s)"] = merged["compile_time_ms_old"] / 1000.0
    comparison_df["Compile Time New (s)"] = merged["compile_time_ms_new"] / 1000.0
    comparison_df["Compile Time Δ"] = merged.apply(
        lambda row: format_change(
            row["compile_time_ms_old"], row["compile_time_ms_new"], threshold
        ),
        axis=1,
    )
    comparison_df["MultiQ Gates Base"] = merged["compiled_multiq_gates_old"]
    comparison_df["MultiQ Gates New"] = merged["compiled_multiq_gates_new"]
    comparison_df["MultiQ Gates Δ"] = merged.apply(
        lambda row: format_change(
            row["compiled_multiq_gates_old"],
            row["compiled_multiq_gates_new"],
            threshold,
        ),
        axis=1,
    )

    return comparison_df


def _try_parse_percent(value: str) -> Optional[float]:
    """Helper to safely parse percentage string from format_change output."""
    if value == "N/A":
        return None  # Or 0.0 if preferred
    try:
        # Remove formatting characters and convert to float
        numeric_part = value.replace("%", "").replace("*", "")
        return float(numeric_part)
    except ValueError:
        # Handle unexpected format gracefully
        print(f"Warning: Could not parse '{value}' as percentage.", file=sys.stderr)
        return None  # Indicate parsing failed


def summarize_changes(
    df: pd.DataFrame, threshold: float = DEFAULT_THRESHOLD
) -> Tuple[int, int, int, int]:
    """
    Summarize the important changes (more than threshold percent) using vectorized operations.

    Args:
        df: The comparison DataFrame from build_comparison_table. Expected columns:
            'Compile Time Δ', 'MultiQ Gates Δ'.
        threshold: The absolute percentage threshold defining a significant change.

    Returns:
        A tuple: (compile_time_improvements, compile_time_regressions,
                 multiq_gates_improvements, multiq_gates_regressions)
    """
    # Use apply with the helper to parse percentages safely
    # Ensure the column names match the output of build_comparison_table
    ct_changes = df["Compile Time Δ"].apply(_try_parse_percent)
    mq_changes = df["MultiQ Gates Δ"].apply(_try_parse_percent)

    # Use boolean indexing and sum() for counting - efficient and idiomatic
    # Note: .sum() on a boolean Series counts True values. We handle None from parsing.
    ct_improvements = (ct_changes < -threshold).sum()
    ct_regressions = (ct_changes > threshold).sum()
    mq_improvements = (mq_changes < -threshold).sum()
    mq_regressions = (mq_changes > threshold).sum()

    return ct_improvements, ct_regressions, mq_improvements, mq_regressions


def post_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    """Posts a comment to a GitHub Pull Request issue.

    Args:
        token: GitHub personal access token.
        repo: GitHub repository in 'owner/name' format.
        pr_number: Pull request number.
        body: The comment content (Markdown supported).

    Raises:
        ValueError: If the token is empty or None.
        SystemExit: If the request fails.
    """
    if not token:
        raise ValueError("A valid GitHub token is required to post comments.")

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",  # Good practice
    }
    payload = {"body": body}

    try:
        response = requests.post(
            url, headers=headers, json=payload, timeout=30
        )  # Added timeout
        response.raise_for_status()  # Check for 4xx/5xx errors
        print(f"✅ Comment posted successfully to PR #{pr_number} in {repo}.")
    except requests.exceptions.RequestException as e:
        print(
            f"❌ Failed to post comment to PR #{pr_number} in {repo}: {e}",
            file=sys.stderr,
        )
        # Provide more context on error if available
        if e.response is not None:
            print(f"Response Status: {e.response.status_code}", file=sys.stderr)
            print(f"Response Body: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post benchmark comparison to a GitHub PR.",
        # Provides defaults in help message
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--repo", required=True, help="GitHub repository in 'owner/name' format"
    )
    parser.add_argument("--pr", type=int, help="Pull request number")
    # Use dest for clearer access via args.sha_base etc.
    parser.add_argument("--sha_base", required=True, help="SHA of the base commit")
    parser.add_argument("--sha_new", required=True, help="SHA of the new commit (head)")
    parser.add_argument("--root_dir", required=True, help="Root directory for results")
    parser.add_argument(
        "--runner_name",
        required=True,
        help="Name of the benchmark runner",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Percentage threshold to consider changes significant",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Dry run (prepare comment body but do not post)",
    )
    args = parser.parse_args()

    # Use os.environ.get for cleaner token retrieval
    github_token: Optional[str] = os.environ.get("GH_TOKEN")

    # Check for token early if not a dry run
    if not args.dry_run and not github_token:
        print(
            "Error: Environment variable GH_TOKEN must be set for posting comments.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load results with error handling
    try:
        results_db = SuiteResultsDatabase.from_root(args.root_dir, args.runner_name)
        results_old: Optional[SuiteResults] = results_db.from_uid(args.sha_base)
        results_new: Optional[SuiteResults] = results_db.from_uid(args.sha_new)
    except Exception as e:
        print(
            f"Error loading benchmark database from '{args.root_dir}' for runner '{args.runner_name}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check if results were found
    if results_old is None:
        print(
            f"Error: Results not found for base commit {args.sha_base} (runner: {args.runner_name}).",
            file=sys.stderr,
        )
        sys.exit(1)
    if results_new is None:
        print(
            f"Error: Results not found for new commit {args.sha_new} (runner: {args.runner_name}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Confirm the results are from the same benchmark suite and version
    spec_old = results_old.suite_specification
    spec_new = results_new.suite_specification
    if spec_old.id != spec_new.id:
        print(
            f"Error: Benchmark suite IDs do not match ('{spec_old.id}' vs '{spec_new.id}').",
            file=sys.stderr,
        )
        sys.exit(1)
    if spec_old.suite_version != spec_new.suite_version:
        # Changed to warning as per previous refinement, could be error if needed
        print(
            f"Warning: Benchmark suite versions differ ('{spec_old.suite_version}' vs '{spec_new.suite_version}'). Comparison may be less meaningful.",
            file=sys.stderr,
        )

    # Convert results to DataFrames
    df_old = to_df_timing(results_old)
    df_new = to_df_timing(results_new)

    # Build comparison table and summarize changes
    print(
        f"Comparing results for runner '{args.runner_name}' between {args.sha_base[:7]} and {args.sha_new[:7]} using threshold {args.threshold}%..."
    )
    comparison_df = build_comparison_table(df_old, df_new, threshold=args.threshold)

    if comparison_df.empty:
        print("No common benchmarks found between the two result sets.")
        markdown_table = "No common benchmarks to compare."
        ct_impr, ct_reg, mq_impr, mq_reg = 0, 0, 0, 0
    else:
        ct_impr, ct_reg, mq_impr, mq_reg = summarize_changes(
            comparison_df, threshold=args.threshold
        )
        markdown_table = comparison_df.to_markdown(index=False, floatfmt=".2f")

    # Prepare comment body

    message = f"""
## 📊 Benchmark Summary ({args.runner_name})

Comparing {args.repo}@{args.sha_new} to {args.repo}@{args.sha_base}:

- 🟢 `{ct_impr}` improvements in `compile_time_ms`
- 🔴 `{ct_reg}` regressions in `compile_time_ms`
- 🟢 `{mq_impr}` improvements in `compiled_multiq_gates`
- 🔴 `{mq_reg}` regressions in `compiled_multiq_gates`

<details>
<summary>🔍 See full benchmark table</summary>

{markdown_table}

</details>
"""

    # Post comment or print for dry run
    if args.dry_run:
        print("\n--- DRY RUN: Comment body ---")
        print(message)
        print("--- END DRY RUN ---")
    else:
        # Token presence already checked if not dry_run
        post_comment(github_token, args.repo, args.pr, message)  # type: ignore [arg-type]

    print("Benchmark comparison script finished.")


if __name__ == "__main__":
    main()
