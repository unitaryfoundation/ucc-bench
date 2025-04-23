#!/bin/bash
set -euo pipefail

# This script runs benchmarks for the UCC project and logs the results,
# using the commit hash and commit time as the uid and uid_time for the benchmark results.
# It also fetch commit hash/time for the version of UCC in pyreproject.toml.
# This enables us to map the benchmark results to a specific commit in the UCC repository.
#!/bin/bash


# Ensure this script is run from the root of the repository
if [[ ! -f ".github/scripts/run_benchmarks.sh" ]]; then
  echo "Please run this script from the root of the repository."
  exit 1
fi

# Parse arguments
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <commit-hash> <runner-name> <out-dir>"
  exit 1
fi

commit_hash="$1"
runner_name="$2"
out_dir="$3"

# Check that jq is available
if ! command -v jq > /dev/null; then
  echo "Error: jq not found. Please install jq to parse JSON."
  exit 1
fi

# Get commit time for the specified commit hash
uid_time=$(git show -s --format=%cI "${commit_hash}")

if [[ -z "$uid_time" ]]; then
  echo "Error: Could not fetch commit time for hash ${commit_hash} from GitHub."
  exit 1
fi

echo "Running benchmarks for ucc-bench@$commit_hash"
echo "Commit time for ucc-bench@$commit_hash: $uid_time"

# Extract commit information for the version of UCC
# set in pyproject.toml
ucc_hash=$(uv run .github/scripts/extract_ucc_revision.py ./pyproject.toml || true)

if [[ -n "$ucc_hash" ]]; then
  echo "ucc in pyproject-toml is ucc@$ucc_hash"

  # Get UCC commit date from GitHub, since ucc is a separate repo than ucc-bench
  ucc_commit_date=$(curl -s -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/unitaryfoundation/ucc/commits/${ucc_hash}" | \
    jq -r '.commit.committer.date // empty')

  if [[ -n "$ucc_commit_date" ]]; then
    echo "Commit time for ucc@$ucc_hash is $ucc_commit_date"
  else
    echo "Warning: Could not fetch commit date for UCC hash $ucc_hash"
    ucc_commit_date=""
  fi
else
  echo "No UCC hash found in pyproject-toml."
  ucc_commit_date=""
  ucc_hash=""
fi

# Function to run a benchmark config
run_bench() {
  local config_file="$1"
  echo "Running benchmark: $config_file"
  uv run ucc-bench "$config_file" \
    --uid "$commit_hash" \
    --uid_time "$uid_time" \
    --log_level INFO \
    -o $out_dir \
    --runner_name "$runner_name" \
    ${ucc_hash:+--ucc_hash "$ucc_hash"} \
    ${ucc_commit_date:+--ucc_time "$ucc_commit_date"}
}

# Run the benchmarks
run_bench ./benchmarks/compilation_benchmarks.toml
run_bench ./benchmarks/simulation_benchmarks.toml
