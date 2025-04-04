import os
import requests
import pandas as pd
import sys
import argparse
from ucc_bench.results import to_df_timing, SuiteResultsDatabase


def format_change(old, new, threshold=10):
    """Returns percent change between old and new values,
    bold in markdown if > threshold percent
    """
    if old == 0:
        return "N/A"
    delta = new - old
    percent = (delta / old) * 100
    highlight = "**" if abs(percent) > threshold else ""
    return f"{highlight}{percent:+.1f}%{highlight}"


def build_comparison_table(df_old, df_new):
    """
    Compares benchmark timing results between two dataframes
    and returns a new dataframe with the differences.
    """
    merged = df_old.merge(
        df_new, on=["compiler", "benchmark_id"], suffixes=("_old", "_new")
    )
    rows = []

    for _, row in merged.iterrows():
        compile_time_change = format_change(
            row["compile_time_ms_old"], row["compile_time_ms_new"]
        )
        gates_change = format_change(
            row["compiled_multiq_gates_old"], row["compiled_multiq_gates_new"]
        )

        rows.append(
            {
                "Compiler": row["compiler"],
                "Benchmark": row["benchmark_id"],
                "Compile Time Δ": compile_time_change,
                "MultiQ Gates Δ": gates_change,
            }
        )

    return pd.DataFrame(rows)


def summarize_changes(df, threshold=10):
    """
    Summarize the important changes (more than threshold percent)
    """
    ct_improvements = 0
    ct_regressions = 0
    mq_improvements = 0
    mq_regressions = 0

    for _, row in df.iterrows():

        def parse_percent(val):
            try:
                return float(val.replace("%", "").replace("**", ""))
            except:  # noqa: E722
                return 0.0

        ct_change = parse_percent(row["Compile Time Δ"])
        mq_change = parse_percent(row["MultiQ Gates Δ"])

        if ct_change < -threshold:
            ct_improvements += 1
        if ct_change > threshold:
            ct_regressions += 1
        if mq_change < -threshold:
            mq_improvements += 1
        if mq_change > threshold:
            mq_regressions += 1

    return ct_improvements, ct_regressions, mq_improvements, mq_regressions


def post_comment(token, repo, pr_number, body):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.post(url, headers=headers, json={"body": body})
    if response.status_code == 201:
        print("✅ Comment posted.")
    else:
        print(f"❌ Failed to post comment: {response.status_code}")
        print(response.text)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Post benchmark comparison to a GitHub PR"
    )
    parser.add_argument(
        "--repo", required=True, help="GitHub repository in 'owner/name' format"
    )
    parser.add_argument("--pr", type=int, required=False, help="Pull request number")
    parser.add_argument("--sha_base", required=True, help="SHA of the base commit")
    parser.add_argument("--sha_new", required=True, help="SHA of the new commit (head)")
    parser.add_argument("--root_dir", required=True, help="Root directory for results")
    parser.add_argument(
        "--runner_name", required=True, help="Name of the benchmark runner"
    )
    args = parser.parse_args()

    token = os.environ["GH_TOKEN"] if "GH_TOKEN" in os.environ else None

    results_db = SuiteResultsDatabase.from_root(args.root_dir, args.runner_name)
    results_old = results_db.from_uid(args.sha_base)
    if results_old is None:
        print(f"Results not found for {args.sha_base}.")
        sys.exit(1)
    results_new = results_db.from_uid(args.sha_new)
    if results_new is None:
        print(f"Results not found for {args.sha_new}.")
        sys.exit(1)

    # Confirm the results are from the same benchmark suite and version
    if results_old.suite_specification.id != results_new.suite_specification.id:
        print("Benchmark suites do not match.")
        sys.exit(1)

    if (
        results_old.suite_specification.suite_version
        != results_new.suite_specification.suite_version
    ):
        print("Benchmark suite versions do not match.")
        sys.exit(1)

    df_old = to_df_timing(results_old)
    df_new = to_df_timing(results_new)

    comparison_df = build_comparison_table(df_old, df_new)
    ct_impr, ct_reg, mq_impr, mq_reg = summarize_changes(comparison_df)

    markdown_table = comparison_df.to_markdown(index=False)

    message = f"""
## 📊 Benchmark Summary

Comparing new {args.repo}@{args.sha_new} to baseline {args.repo}@{args.sha_base}, we observe:

- 🟢 {ct_impr} improvements in `compile_time_ms`
- 🔴 {ct_reg} regressions in `compile_time_ms`
- 🟢 {mq_impr} improvements in `compiled_multiq_gates`
- 🔴 {mq_reg} regressions in `compiled_multiq_gates`

<details>
<summary>🔍 See full benchmark table</summary>

{markdown_table}

</details>

<details>
<summary>⚙️ See full benchmark results</summary>
For new {args.repo}@{args.sha_new}

```json
{results_new.model_dump_json(indent=2)}
```

For baseline {args.repo}@{args.sha_base}

```
{results_new.model_dump_json(indent=2)}
```
</details>
"""

    if args.pr:
        print("Posting comment to PR...")
        post_comment(token, args.repo, args.pr, message)
    else:
        print("Dry run enabled. Comment would be:")
        print(message)


if __name__ == "__main__":
    main()
