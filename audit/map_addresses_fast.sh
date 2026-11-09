#!/usr/bin/env bash
# Fast address/param inventory over MATERIALISED working trees (exact HEAD).
set -u
AUDIT_DIR=${AUDIT_DIR:-/home/user/.cache/0g-audit}
REPOS="$AUDIT_DIR/repos"
ADDR='0x[a-fA-F0-9]{40}'
printf 'repo\thead\tpath\tline\taddress_or_param\tcontext\n' > "$AUDIT_DIR/live_address_map.tsv"
for out in "$REPOS"/*; do
  [ -d "$out/.git" ] || [ -d "$out" ] || continue
  work=$(find "$out" -maxdepth 1 -type f | head -1)
  [ -n "$work" ] || continue                      # not materialised
  full=${out##*/}; full=${full/__/\/}
  head=$(git -C "$out" rev-parse --verify HEAD 2>/dev/null) || continue
  grep -rInE "$ADDR" "$out" \
    --exclude-dir=.git --exclude='*.lock' --exclude='*.min.js' --exclude='*.map' \
    --exclude='*.svg' --exclude='*.png' --exclude='*.jpg' 2>/dev/null | head -4000 | \
  while IFS=: read -r f n line; do
    p=${f#"$out/"}
    a=$(echo "$line" | grep -oE "$ADDR" | head -1)
    ctx=$(echo "$line" | cut -c1-200 | tr '\t' ' ')
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$full" "$head" "$p" "$n" "$a" "$ctx" >> "$AUDIT_DIR/live_address_map.tsv"
  done
done
echo "rows: $(($(wc -l < "$AUDIT_DIR/live_address_map.tsv") - 1))"
echo "unique addresses: $(cut -f5 "$AUDIT_DIR/live_address_map.tsv" | grep -oE "$ADDR" | sort -u | wc -l)"
