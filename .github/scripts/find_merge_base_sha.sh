#!/bin/bash
set -e

# This script finds the SHA of the last commit on the main branch that is
#  -- not a [benchmark chore] commit
#  -- and is an ancestor of the feature branch

# Arguments: FEATURE_BRANCH MAIN_BRANCH
FEATURE_BRANCH=$1
MAIN_BRANCH=$2


if [[ ! -f ".github/scripts/find_merge_base.sh" ]]; then
  echo "Please run this script from the root of the repository."
  exit 1
fi

# Get the merge-base
BASE=$(git merge-base "$FEATURE_BRANCH" "$MAIN_BRANCH")

# Walk back from the base to find a non-[benchmark chore] commit
CURRENT=$BASE

while [ -n "$CURRENT" ]; do
  MESSAGE=$(git log -1 --pretty=%s "$CURRENT")
  if [[ "$MESSAGE" != "[benchmark chore"* ]]; then
    echo "$CURRENT"
    exit 0
  fi
  CURRENT=$(git rev-list --first-parent --max-count=1 "${CURRENT}^")
done

echo "❌ No non-benchmark-chore commit found in history!" >&2
exit 1
