import os
import requests
import pandas as pd
import sys
import argparse
from typing import Optional, Tuple
from ucc_bench.results import to_df_timing, SuiteResultsDatabase, SuiteResults

DEFAULT_THRESHOLD = 10.0
EPS = 1e-8


def format_change(
    percent: Optional[float], threshold: float = DEFAULT_THRESHOLD
) -> str:
    """Formats the percentage change with optional highlighting."""
    if percent is None:
        return "N/A"
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

    # Create the comparison dataframe
    comparison_df = pd.DataFrame()
    comparison_df["Compiler"] = merged["compiler"]
    comparison_df["Benchmark"] = merged["benchmark_id"]

    comparison_df["Compile Time Base (s)"] = merged["compile_time_ms_old"] / 1000.0
    comparison_df["Compile Time New (s)"] = merged["compile_time_ms_new"] / 1000.0

    # Calculate percentage changes using vectorized operations
    comparison_df["Compile Time Δ Raw"] = (
        (merged["compile_time_ms_new"] - merged["compile_time_ms_old"])
        / (merged["compile_time_ms_old"] + EPS)
        * 100
    )
    comparison_df["MultiQ Gates Δ Raw"] = (
        (merged["compiled_multiq_gates_new"] - merged["compiled_multiq_gates_old"])
        / (merged["compiled_multiq_gates_old"] + EPS)
        * 100
    )

    # Format changes using vectorized operations
    comparison_df["Compile Time Δ"] = comparison_df["Compile Time Δ Raw"].map(
        lambda percent: format_change(percent, threshold)
    )
    comparison_df["MultiQ Gates Δ"] = comparison_df["MultiQ Gates Δ Raw"].map(
        lambda percent: format_change(percent, threshold)
    )

    comparison_df["MultiQ Gates Base"] = merged["compiled_multiq_gates_old"]
    comparison_df["MultiQ Gates New"] = merged["compiled_multiq_gates_new"]

    return comparison_df


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
    # Use raw percentage changes for summarization
    ct_changes = df["Compile Time Δ Raw"]
    mq_changes = df["MultiQ Gates Δ Raw"]

    ct_improvements = (ct_changes < -threshold).sum()
    ct_regressions = (ct_changes > threshold).sum()
    mq_improvements = (mq_changes < -threshold).sum()
    mq_regressions = (mq_changes > threshold).sum()

    return ct_improvements, ct_regressions, mq_improvements, mq_regressions


def post_github_comment(
    token: str,
    repo: str,
    pr_number: Optional[int],
    body: str,
    dry_run: bool,
    is_error: bool = False,
) -> None:
    """
    Posts a comment to a GitHub PR or prints it, with optional error styling.

    Args:
        token: GitHub personal access token.
        repo: GitHub repository in 'owner/name' format.
        pr_number: Pull request number.
        body: The comment content (Markdown supported).
        dry_run: Whether to only print instead of posting.
        is_error: Whether the message is an error (adds heading).
    """
    if is_error:
        body = f"## ❌ Error running benchmark comparison\n\n{body}"

    print(body)
    if dry_run or not pr_number:
        return

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"body": body}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        print(f"✅ Comment posted successfully to PR #{pr_number} in {repo}.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to post comment to PR #{pr_number} in {repo}: {e}")
        if e.response is not None:
            print(f"Response Status: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
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

    # Only commenting on timing results for now (not simulation ones)
    timing_results_db = SuiteResultsDatabase.from_root(
        args.root_dir, args.runner_name, "timing_benchmarks"
    )
    results_old: Optional[SuiteResults] = timing_results_db.from_uid(args.sha_base)
    results_new: Optional[SuiteResults] = timing_results_db.from_uid(args.sha_new)

    # Check if results were found
    if results_old is None:
        error_msg = f"Results not found for base commit {args.sha_base} (runner: {args.runner_name})."
        "You might need to rebase on more recent changes."

        post_github_comment(
            github_token, args.repo, args.pr, error_msg, args.dry_run, is_error=True
        )
        sys.exit(1)
    if results_new is None:
        error_msg = f"Results not found for new commit {args.sha_new} (runner: {args.runner_name})."
        post_github_comment(
            github_token, args.repo, args.pr, error_msg, args.dry_run, is_error=True
        )
        sys.exit(1)

    # Confirm the results are from the same benchmark suite and version
    spec_old = results_old.suite_specification
    spec_new = results_new.suite_specification
    if spec_old.id != spec_new.id:
        error_msg = (
            f"Benchmark suite IDs do not match ('{spec_old.id}' vs '{spec_new.id}')."
        )
        post_github_comment(
            github_token, args.repo, args.pr, error_msg, args.dry_run, is_error=True
        )
        sys.exit(1)

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
        # Drop raw columns before rendering the final markdown table
        comparison_df.drop(
            columns=["Compile Time Δ Raw", "MultiQ Gates Δ Raw"], inplace=True
        )
        markdown_table = comparison_df.to_markdown(index=False, floatfmt=".2f")

    # Prepare comment body

    if spec_old.suite_version != spec_new.suite_version:
        warning_msg = (
            f"Warning: Benchmark suite versions differ ('{spec_old.suite_version}' vs '{spec_new.suite_version}'). "
            "Comparison may be less meaningful."
        )
    else:
        warning_msg = ""

    message = f"""
## 📊 Benchmark Summary ({args.runner_name})

Comparing new {args.repo}@{args.sha_new} to base {args.repo}@{args.sha_base}:

- 🟢 `{ct_impr}` improvements in `compile_time_ms`
- 🔴 `{ct_reg}` regressions in `compile_time_ms`
- 🟢 `{mq_impr}` improvements in `compiled_multiq_gates`
- 🔴 `{mq_reg}` regressions in `compiled_multiq_gates`

{warning_msg}

<details>
<summary>🔍 See full benchmark table</summary>

{markdown_table}

</details>
"""

    post_github_comment(github_token, args.repo, args.pr, message, args.dry_run)

    print("Benchmark comparison script finished.")


if __name__ == "__main__":
    main()
