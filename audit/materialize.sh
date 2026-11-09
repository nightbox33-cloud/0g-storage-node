#!/usr/bin/env bash
# Materialise (checkout) the repos that contain money/consensus/deployment code.
# Partial clones fetch these trees in one batch each -> fast and exact.
set -u
AUDIT_DIR=${AUDIT_DIR:-/home/user/.cache/0g-audit}
REPOS="$AUDIT_DIR/repos"
cat > "$AUDIT_DIR/materialize_list.txt" <<'EOF'
0gfoundation/0g-storage-contracts
0gfoundation/0g-storage-node
0gfoundation/0g-storage-client
0gfoundation/0g-storage-ts-sdk
0gfoundation/0g-storage-scan
0gfoundation/0g-deployment-scripts
0gfoundation/0gchain-Aristotle
0gfoundation/0gchain-NG
0gfoundation/0g-da-contract
0gfoundation/0g-da-node
0gfoundation/0g-da-encoder
0gfoundation/0g-da-retriever
0gfoundation/0g-da-light
0gfoundation/0g-da-op-plasma
0gfoundation/0g-serving-contract
0gfoundation/0g-serving-network
0gfoundation/0g-serving-token-counter
0gfoundation/0g-serving-user-broker-web
0gfoundation/0g-zk-settlement-server
0gfoundation/0g-zk-settlement-client
0gfoundation/0g-ito-settlement-server
0gfoundation/0g-agent-nft
0gfoundation/A0GI-contracts
0gfoundation/0g-restaking-contracts
0gfoundation/0g-contract-example
0gfoundation/0g-kms
0gfoundation/0g-tapp-verifier
0gfoundation/0g-sandbox
0gfoundation/0g-scan-backend
0gfoundation/Docker-RPC
0gfoundation/0g-testing-hub
0gfoundation/0g-ui
0gfoundation/0g-doc
0gfoundation/0g-blockscout
0gfoundation/0g-storage-kv
0gfoundation/0g-inft-oracle-server-ts
0gfoundation/0g-python-api
0gfoundation/0g-avs-server
0gfoundation/0g-eigen-avs
0gfoundation/pancake-contracts-move
0gfoundation/0gchain-NG
zerog-ai/MGVerse
EOF
sort -u -o "$AUDIT_DIR/materialize_list.txt" "$AUDIT_DIR/materialize_list.txt"
mat_one() {
  full=$1; out="$REPOS/${full//\//__}"
  [ -d "$out/.git" ] || { echo "MISSING $full"; return; }
  git -C "$out" -c filter.lfs.smudge=cat -c filter.lfs.clean=cat -c filter.lfs.required=false \
      checkout -q -f HEAD >/dev/null 2>&1
  n=$(find "$out" -path "$out/.git" -prune -o -type f -print | wc -l)
  echo "OK $full $(git -C "$out" rev-parse --verify HEAD 2>/dev/null) files=$n"
}
export -f mat_one; export REPOS
xargs -P 8 -a "$AUDIT_DIR/materialize_list.txt" -I{} bash -c 'mat_one "$@"' _ {} \
  > "$AUDIT_DIR/materialize.log" 2>&1
cat "$AUDIT_DIR/materialize.log"
echo "total disk: $(du -sh "$REPOS" | cut -f1)"
