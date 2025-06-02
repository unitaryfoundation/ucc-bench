#!/bin/bash
set -euo pipefail

# This script runs the benchmarks for a pull request to either ucc or ucc-bench
# repositories, and then posts the results as a comment on the pull request.

if [[ ! -f ".github/scripts/run_benchmarks_pr.sh" ]]; then
  echo "Please run this script from the root of the repository."
  exit 1
fi

if [ "$#" -ne 5 ]; then
    echo "Usage: $0 <REPO_NAME> <RUNNER_LABEL> <SHA_OR_UCC_NEW_SHA> <PR_NUMBER> <COMMENT_FILE.json>"
    exit 1
fi

REPO_NAME=$1 # the name of the repository (e.g., "ucc-bench" or "ucc")
RUNNER_LABEL=$2 # e.g. ucc-benchmarks-8-core-U22.04
SHA_OR_UCC_NEW_SHA=$3 # the SHA of the commit in ucc or ucc-bench to run
PR_NUMBER=$4 # the pull request number to post the comment to
JSON_FILE=$5

if [[ "$REPO_NAME" == "ucc-bench" ]]; then
  IS_UCC_BENCH=true
  echo "Running for ucc-bench"
else
  IS_UCC_BENCH=false
  echo "Running on ucc"
fi

# Install the project
echo "::group::Install project"
uv sync --all-extras --all-groups
echo "::endgroup::"

# Set up git config to be bot user
echo "::group::Set up git config"
git config --global user.email "github-actions@users.noreply.github.com"
git config --global user.name "github-actions"
echo "::endgroup::"

echo "::group::Show recent git history"
echo "$(git log --oneline -n 10)"
echo "::endgroup::"

if [[ "$IS_UCC_BENCH" == false ]]; then
  echo "::group::Upgrade UCC"
  UCC_NEW_SHA=$SHA_OR_UCC_NEW_SHA

  # Get baseline (current) version of UCC
  UCC_BASE_SHA=$(uv run .github/scripts/extract_ucc_revision.py ./pyproject.toml)
  echo "UCC_BASE_SHA=$UCC_BASE_SHA"

  # Upgrade to target version of UCC
  git checkout -b upgrade-ucc-${UCC_NEW_SHA}
  uv add git+https://github.com/unitaryfoundation/ucc@${UCC_NEW_SHA}
  git add pyproject.toml uv.lock
  git commit -m "Upgrade UCC to ${UCC_NEW_SHA}"
  SHA_NEW=$(git rev-parse HEAD)
  echo "SHA_NEW=$SHA_NEW"
  echo "::endgroup::"

  echo "::group::Show recent git history again"
  echo "$(git log --oneline -n 10)"
  echo "::endgroup::"
else
  # We are is simply benchmarking the configuration as of this commit
  # in ucc-bench
  SHA_NEW=$SHA_OR_UCC_NEW_SHA
fi

# Run benchmarks for PR comparison
echo "::group::Run benchmarks"
.github/scripts/run_benchmarks.sh $SHA_NEW $RUNNER_LABEL ./results
echo "::endgroup::"

echo "::group::Show benchmark result files"
echo "$(tree ./results)"
echo "::endgroup::"

# Get the SHA of the last commit on the main branch before this PR as the baseline for comparison
echo "::group::Find ancestor SHA"
ANCESTOR_SHA=$(.github/scripts/find_ancestor_sha.sh HEAD origin/main)
echo "Useful base commit: $ANCESTOR_SHA"
echo "::endgroup::"

# Post benchmark diff comment
echo "::group::Post benchmark diff comment"
if [[ "$IS_UCC_BENCH" == false ]]; then
  uv run python .github/scripts/benchmark_diff_comment.py \
  prepare --repo "ucc" \
  --pr "$PR_NUMBER" \
  --root_dir ./results \
  --runner_name $RUNNER_LABEL \
  --sha_base $ANCESTOR_SHA \
  --sha_new "$SHA_NEW" \
  --sha_ucc_base "$UCC_BASE_SHA" \
  --sha_ucc_new "$UCC_NEW_SHA" \
  --output "$JSON_FILE"
else
  uv run python .github/scripts/benchmark_diff_comment.py \
  prepare --repo "ucc-bench" \
  --pr "$PR_NUMBER" \
  --root_dir ./results \
  --runner_name $RUNNER_LABEL \
  --sha_base $ANCESTOR_SHA \
  --sha_new "$SHA_NEW" \
  --output "$JSON_FILE"
fi
echo "::endgroup::"
