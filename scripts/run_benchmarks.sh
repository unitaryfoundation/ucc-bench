#!/bin/bash
set -e

# Ensure this script is run from the root of the repository
if [ ! -f "scripts/run_benchmarks.sh" ]; then
  echo "Please run this script from the root of the repository."
  exit 1
fi
# The first argument to the script is the commit hash
if [ -z "$1" ]; then
  echo "Usage: $0 <commit-hash>"
  exit 1
fi
commit_hash=$1

# The second argument to the script is the runner name
if [ -z "$2" ]; then
  echo "Usage: $0 <commit-hash> <runner-name>"
  exit 1
fi
runner_name=$2

# Get timestamp of the commit (in UTC)
uid_time=$(TZ=UTC git show -s --format=%cI <commit_hash>)

# Figure out the current hash of ucc that is used in this repo by parsing pyproject.toml
ucc_hash=$(grep -oP '(?<=ucc = ").*(?=")' pyproject.toml)
# Use the github API to get the commit date of the ucc hash
ucc_commit_date=$(curl -s -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/unitaryfoundation/ucc/commits/${ucc_hash}" | jq -r '.[0].commit.committer.date')

uv run ucc-bench ./benchmarks/timing_benchmarks.toml --uid '${commit_hash}' --uid_time '${uid_time}' --log_level INFO -o ./results --runner_name '${runner_name}'
uv run ucc-bench ./benchmarks/simulation_benchmarks.toml --uid '${commit_hash}' --uid_time '${uid_time}' --log_level INFO -o ./results --runner_name '${runner_name}'
