#!/usr/bin/env bash
# Clone every submodule declared in any .gitmodules of the foundation clones.
# Most are third-party build deps (forge-std, OpenZeppelin, Symbiotic); record
# their exact commit hashes when a gitlink exists in the tree.
set -u
AUDIT_DIR=${AUDIT_DIR:-/home/user/.cache/0g-audit}
REPOS="$AUDIT_DIR/repos"
SUBS="$AUDIT_DIR/submodules"
mkdir -p "$SUBS"
: > "$AUDIT_DIR/submodules.tsv"
for out in "$REPOS"/*; do
  [ -d "$out/.git" ] || continue
  full=${out##*/}; full=${full/__/\/}
  git -C "$out" ls-tree -r --name-only HEAD 2>/dev/null | grep -E '(^|/)\.gitmodules$' | while read -r gm; do
    git -C "$out" show "HEAD:$gm" 2>/dev/null | awk -v repo="$full" -v gm="$gm" '
      /^[ \t]*path[ \t]*=/ {p=$3}
      /^[ \t]*url[ \t]*=/  {u=$3; printf "%s\t%s\t%s\t%s\n", repo, gm, p, u}
      /^[ \t]*branch[ \t]*=/ {print repo "\t" gm "\tBRANCH\t" $3}
    ' >> "$AUDIT_DIR/submodules.tsv"
  done
done
# materialise gitlinks (exact pinned commits) if any exist
: > "$AUDIT_DIR/submodule_gitlinks.tsv"
for out in "$REPOS"/*; do
  [ -d "$out/.git" ] || continue
  full=${out##*/}; full=${full/__/\/}
  git -C "$out" ls-tree -r HEAD 2>/dev/null | grep ' 160000 commit ' | \
    awk -v r="$full" '{print r "\t" $3 "\t" $4}' >> "$AUDIT_DIR/submodule_gitlinks.tsv"
done
# clone distinct URLs (third-party, all public)
cut -f4 "$AUDIT_DIR/submodules.tsv" | grep '^http' | sort -u | while read -r url; do
  name=$(echo "$url" | sed -E 's#https?://github.com/##; s/\.git$//; s#/#__#g')
  [ -d "$SUBS/$name/.git" ] || timeout 180 git -c http.version=HTTP/1.1 clone --quiet --filter=blob:none \
     --no-checkout "$url" "$SUBS/$name" >/dev/null 2>&1 || echo "SUBMODULE_CLONE_FAILED $url" >> "$AUDIT_DIR/submodule_failures.log"
done
echo "declared submodule entries: $(wc -l < "$AUDIT_DIR/submodules.tsv")"
echo "gitlinks in trees:          $(wc -l < "$AUDIT_DIR/submodule_gitlinks.tsv")"
echo "distinct submodule repos:   $(cut -f4 "$AUDIT_DIR/submodules.tsv" | grep '^http' | sort -u | wc -l)"
echo "cloned:                     $(find "$SUBS" -maxdepth 1 -type d -name '*__*' | wc -l)"
cat "$AUDIT_DIR/submodule_failures.log" 2>/dev/null || true
