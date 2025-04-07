#!/bin/bash
set -euo pipefail

if [[ ! -f ".github/scripts/run_benchmarks_pr.sh" ]]; then
  echo "Please run this script from the root of the repository."
  exit 1
fi

# Ensure required arguments are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <RUNNER_LABEL> <UCC_NEW_SHA> <PR_NUMBER>"
    exit 1
fi

RUNNER_LABEL=$1
UCC_NEW_SHA=$2
PR_NUMBER=$3

# Install the project
uv sync --all-extras --dev

# Set up git config to be bot user
git config --global user.email "github-actions@users.noreply.github.com"
git config --global user.name "github-actions"

# Get baseline version of UCC
UCC_BASE_SHA=$(uv run .github/scripts/extract_ucc_revision.py ./pyproject.toml)
echo "UCC_BASE_SHA=$UCC_BASE_SHA"

# Upgrade to target version of UCC
git checkout -b upgrade-ucc-${UCC_NEW_SHA}
uv add git+https://github.com/unitaryfoundation/ucc@${UCC_NEW_SHA}
git add pyproject.toml uv.lock
git commit -m "Upgrade UCC to ${UCC_NEW_SHA}"
SHA_NEW=$(git rev-parse HEAD)
git push origin HEAD:upgrade-ucc-${UCC_NEW_SHA}
echo "SHA_NEW=$SHA_NEW"

# Run benchmarks for PR comparison
.github/scripts/run_benchmarks.sh $SHA_NEW $RUNNER_LABEL ./results

# Get the SHA of the last commit on the main branch before this PR as the baseline for comparison
ANCESTOR_SHA=$(.github/scripts/find_ancestor_sha.sh HEAD origin/main)
echo "Useful base commit: $ANCESTOR_SHA"

uv run python .github/scripts/post_benchmark_diff_comment.py \
--repo "unitaryfoundation/ucc" \
--pr "$PR_NUMBER" \
--root_dir ./results \
--runner_name $RUNNER_LABEL \
--sha_base $ANCESTOR_SHA \
--sha_new "$SHA_NEW" \
--sha_ucc_base "$UCC_BASE_SHA" \
--sha_ucc_new "$UCC_NEW_SHA"
