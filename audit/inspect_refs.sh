#!/usr/bin/env bash
# Record, for every cloned repo: git submodules (with their gitlink commit),
# Git LFS-tracked patterns, and the deployed-artifact / address inventory files.
set -u
AUDIT_DIR=${AUDIT_DIR:-/home/user/.cache/0g-audit}
REPOS="$AUDIT_DIR/repos"
printf 'repo\ttype\tpath\tvalue\n' > "$AUDIT_DIR/assets_manifest.tsv"
for out in "$REPOS"/*; do
  [ -d "$out/.git" ] || continue
  full=${out##*/}; full=${full/__/\/}
  head=$(git -C "$out" rev-parse HEAD 2>/dev/null) || continue
  # --- submodules (gitlinks come from the tree, no blob fetch needed)
  git -C "$out" ls-tree -r HEAD 2>/dev/null | grep -E ' 160000 commit ' | while read -r mode type sha path; do
    printf '%s\tsubmodule\t%s\tgitlink:%s\n' "$full" "$path" "$sha" >> "$AUDIT_DIR/assets_manifest.tsv"
  done
  gm=$(git -C "$out" ls-tree -r --name-only HEAD 2>/dev/null | grep -E '(^|/)\.gitmodules$' | head -1)
  if [ -n "$gm" ]; then
    git -C "$out" show "HEAD:$gm" 2>/dev/null | grep -E '^\s*(path|url|branch)\s*=' | tr -d ' ' | \
      while read -r kv; do printf '%s\tgitmodules\t%s\t%s\n' "$full" "$gm" "$kv" >> "$AUDIT_DIR/assets_manifest.tsv"; done
  fi
  # --- LFS
  git -C "$out" ls-tree -r --name-only HEAD 2>/dev/null | grep -E '(^|/)\.gitattributes$' | while read -r ga; do
    git -C "$out" show "HEAD:$ga" 2>/dev/null | grep 'filter=lfs' | \
      while read -r line; do printf '%s\tlfs\t%s\t%s\n' "$full" "$ga" "$line" >> "$AUDIT_DIR/assets_manifest.tsv"; done
  done
done
echo "assets rows: $(($(wc -l < "$AUDIT_DIR/assets_manifest.tsv") - 1))"
echo "submodules:  $(grep -c '	submodule	' "$AUDIT_DIR/assets_manifest.tsv")"
echo "lfs rows:    $(grep -c '	lfs	' "$AUDIT_DIR/assets_manifest.tsv")"
