#!/usr/bin/env bash
# Reproduce the prerequisite: clone EVERY repository of the 0G foundation orgs
# (public + private visible to the token), all branches, all tags, full commit
# graph (partial clone: blobs are fetched lazily from the same promisor remote
# so `git show <ref>:<path>` still gives the exact source of truth).
#
# Usage:  bash audit/clone_foundation.sh
# Output: $AUDIT_DIR/repos/<org>__<repo>/  +  $AUDIT_DIR/repo_manifest.tsv
#         $AUDIT_DIR/refs_manifest.tsv     +  $AUDIT_DIR/clone_failures.tsv
set -u
AUDIT_DIR=${AUDIT_DIR:-/home/user/.cache/0g-audit}
REPOS="$AUDIT_DIR/repos"
mkdir -p "$REPOS"

# 1. Enumerate orgs / spaces. 0gfoundation = 0G Foundation; 0glabs and
#    zerog-ai = 0G Labs. Add manually any other space found during scoping.
ORGS="0gfoundation 0glabs zerog-ai"
: > "$AUDIT_DIR/repo_list.tsv"
for org in $ORGS; do
  gh api --paginate "orgs/$org/repos?type=all&per_page=100" \
    --jq ".[] | [.full_name, (.private|tostring), (.archived|tostring), (.fork|tostring), (.default_branch // \"\")] | @tsv" \
    >> "$AUDIT_DIR/repo_list.tsv" 2>>"$AUDIT_DIR/enumeration_errors.log" || \
    echo "ENUM_FAILED $org" >> "$AUDIT_DIR/enumeration_errors.log"
done
sort -u -o "$AUDIT_DIR/repo_list.tsv" "$AUDIT_DIR/repo_list.tsv"

# 2. Clone with all refs, no checkout (avoids pulling multi-GB of unrelated
#    fork blobs; every blob is still reachable on demand).
clone_one() {
  full=$1; private=$2; archived=$3; fork=$4; branch=$5
  out="$REPOS/${full//\//__}"
  if [ -d "$out/.git" ]; then return 0; fi
  if timeout 300 git -c http.version=HTTP/1.1 clone --quiet --filter=blob:none \
       --no-checkout "https://github.com/$full.git" "$out" \
       >"$AUDIT_DIR/clone_${full//\//__}.log" 2>&1
  then
    # force all heads + tags (partial clone keeps this cheap)
    git -C "$out" fetch --quiet --filter=blob:none origin \
      '+refs/heads/*:refs/remotes/origin/*' '+refs/tags/*:refs/tags/*' \
      >>"$AUDIT_DIR/clone_${full//\//__}.log" 2>&1 || true
    echo "OK $full"
  else
    echo "FAIL $full $(tail -1 "$AUDIT_DIR/clone_${full//\//__}.log")"
  fi
}
export -f clone_one
export REPOS AUDIT_DIR
cat "$AUDIT_DIR/repo_list.tsv" | xargs -P 8 -L 1 bash -c 'clone_one "$@"' _ \
  >"$AUDIT_DIR/clone_results.log" 2>&1

# 3. Exact commit hash per repo (default branch HEAD) + every ref head.
printf 'repo\tprivate\tarchived\tfork\tdefault_branch\thead_commit\thead_date\thead_subject\tbranches\ttags\trefs\n' \
  > "$AUDIT_DIR/repo_manifest.tsv"
: > "$AUDIT_DIR/refs_manifest.tsv"
: > "$AUDIT_DIR/clone_failures.tsv"
while IFS=$'\t' read -r full private archived fork branch; do
  out="$REPOS/${full//\//__}"
  if [ ! -d "$out/.git" ]; then
    printf '%s\tCLONE_FAILED\n' "$full" >> "$AUDIT_DIR/clone_failures.tsv"; continue
  fi
  if ! head=$(git -C "$out" rev-parse --verify HEAD 2>/dev/null); then
    head=EMPTY_REPO_NO_COMMIT; date=''; subj='(empty repository: no commits on any ref)'
  else
    date=$(git -C "$out" log -1 --format=%cI HEAD 2>/dev/null || echo '')
    subj=$(git -C "$out" log -1 --format=%s HEAD 2>/dev/null | tr '\t' ' ' | cut -c1-120)
  fi
  nb=$(git -C "$out" for-each-ref --format='%(refname)' refs/remotes/origin | grep -v 'refs/remotes/origin/HEAD$' | wc -l)
  nt=$(git -C "$out" for-each-ref --format='%(refname)' refs/tags | wc -l)
  nr=$(git -C "$out" for-each-ref --format='%(refname)' | wc -l)
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$full" "$private" "$archived" "$fork" "$branch" "$head" "$date" "$subj" "$nb" "$nt" "$nr" \
    >> "$AUDIT_DIR/repo_manifest.tsv"
  git -C "$out" for-each-ref --format="$full\t%(objectname)\t%(refname)\t%(objecttype)\t%(creatordate:iso8601)" \
    >> "$AUDIT_DIR/refs_manifest.tsv"
done < "$AUDIT_DIR/repo_list.tsv"

echo "repos enumerated: $(wc -l < "$AUDIT_DIR/repo_list.tsv")"
echo "cloned:           $(($(wc -l < "$AUDIT_DIR/repo_manifest.tsv") - 1))"
echo "failed:           $(wc -l < "$AUDIT_DIR/clone_failures.tsv")"
echo "refs recorded:    $(wc -l < "$AUDIT_DIR/refs_manifest.tsv")"
