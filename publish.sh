#!/usr/bin/env bash
# Publish the current state every few minutes, without interrupting the watch.
#
# The hourly handover was the only save, so the report and the front page ran
# up to an hour behind the phone alerts -- you could be told you had lost and
# still read a balance from before it happened.
#
# Saving from the running workspace is not an option: the save resets the tree
# to the branch head, and check.py is writing to it. So this works in a
# separate clone. The running bot is never touched, and there is no gap in
# watching.
#
# Every merge here is union-based and idempotent (merge_state.py,
# merge_books.py), so racing the hourly save costs nothing -- whichever lands
# second folds the other in.
#
#   STATE=<dir> BRANCH=<name> ./publish.sh once     # one publish
#   STATE=<dir> BRANCH=<name> ./publish.sh loop 300 # every 300s until killed
set -uo pipefail

STATE="${STATE:-$PWD/cloud_state}"
BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
WORK="${WORK:-/tmp/publish_clone}"
REPO="${REPO:-$PWD}"

publish() {
  # A fresh snapshot of what the bot has written so far.
  rm -rf /tmp/pub_mine && mkdir -p /tmp/pub_mine
  cp "$STATE/check_memory.json" /tmp/pub_mine/ 2>/dev/null \
    || { echo "  no memory yet"; return 0; }
  cp -r "$STATE/orderbook" /tmp/pub_mine/ 2>/dev/null || true

  if [ ! -d "$WORK/.git" ]; then
    rm -rf "$WORK"
    git clone --quiet --branch "$BRANCH" --single-branch "$REPO" "$WORK" \
      || { echo "  clone failed"; return 1; }
    git -C "$WORK" remote set-url origin \
      "$(git -C "$REPO" remote get-url origin)"
    git -C "$WORK" config user.name  "btcbot"
    git -C "$WORK" config user.email "btcbot@users.noreply.github.com"
  fi

  for i in 1 2 3; do
    git -C "$WORK" fetch --quiet origin "$BRANCH" || { sleep $((2 ** i)); continue; }
    git -C "$WORK" reset --hard --quiet "origin/$BRANCH"

    python3 "$WORK/merge_state.py" /tmp/pub_mine/check_memory.json \
      "$WORK/cloud_state/check_memory.json" \
      "$WORK/cloud_state/check_memory.json" >/dev/null || return 1
    python3 "$WORK/merge_books.py" /tmp/pub_mine "$WORK/cloud_state" \
      "$WORK/cloud_state" >/dev/null || true

    # NTFY_TOPIC deliberately empty: --report settles pending contracts, and
    # the running bot must be the only thing that alerts about them.
    ( cd "$WORK" && NTFY_TOPIC= CHECK_STATE_DIR="$WORK/cloud_state" \
        python3 check.py --report >/dev/null 2>&1
      NTFY_TOPIC= CHECK_STATE_DIR="$WORK/cloud_state" \
        python3 make_page.py >/dev/null 2>&1 )

    git -C "$WORK" add cloud_state docs README.md
    if git -C "$WORK" diff --staged --quiet; then echo "  no change"; return 0; fi
    git -C "$WORK" commit --quiet -m "state: $(date -u +%Y-%m-%dT%H:%MZ)"
    if git -C "$WORK" push --quiet origin "HEAD:$BRANCH" 2>/dev/null; then
      echo "  published $(date -u +%H:%MZ)"; return 0
    fi
    sleep $((2 ** i))
  done
  echo "  publish failed after 3 tries"
  return 1
}

case "${1:-once}" in
  once) publish ;;
  loop) while true; do publish; sleep "${2:-300}"; done ;;
  *)    echo "usage: publish.sh [once|loop [seconds]]"; exit 2 ;;
esac
