#!/usr/bin/env bash
# Anclaje read-only del estado live de 0G Storage (chain 16661).
# El sandbox de esta auditoría NO puede hacer POST a evmrpc.0g.ai; ejecutar desde un host con RPC.
#
#   RPC=https://evmrpc.0g.ai ./live_anchor.sh
#
# Requiere cast (foundry): https://book.getfoundry.sh/
set -euo pipefail
RPC="${RPC:-https://evmrpc.0g.ai}"
FLOW=0x62D4144dB0F0a6fBBaeb6296c785C71B3D57C526
MINE=0xCd01c5Cd953971CE4C2c9bFb95610236a7F414fe
REWARD=0x457aC76B58ffcDc118AABD6DbC63ff9072880870

c(){ cast call --rpc-url "$RPC" "$1" "$2" ${3:-} | tr -d '\n'; echo; }

echo "== bloque";                cast block-number --rpc-url "$RPC"
echo "== Flow $FLOW"
for f in "firstBlock()(uint256)" "blocksPerEpoch()(uint256)" "numSubmissions()(uint256)" \
         "epoch()(uint256)" "epochStartPosition()(uint256)" "market()(address)" "paused()(bool)"; do
  printf '  %-32s ' "$f"; c $FLOW "$f"
done
printf '  %-32s ' "tree()"; c $FLOW "tree()(uint256,uint256)"
printf '  %-32s ' "getContext()"; c $FLOW "getContext()((uint256,uint256,bytes32,uint256,bytes32,bytes32))"
printf '  %-32s ' "balance"; cast balance --rpc-url "$RPC" $FLOW

MARKET=$(cast call --rpc-url "$RPC" $FLOW "market()(address)")
echo "== FixedPrice $MARKET"
for f in "pricePerSector()(uint256)" "flow()(address)" "reward()(address)"; do
  printf '  %-32s ' "$f"; c $MARKET "$f"
done

echo "== PoraMine $MINE"
for f in "dataProofEnabled()(bool)" "sealDataEnabled()(bool)" "fixedDifficulty()(bool)" \
         "poraVersion()(uint64)" "poraTarget()(uint256)" "minDifficulty()(uint256)" \
         "maxShards()(uint64)" "targetSubmissions()(uint256)" "nSubtasks()(uint256)" \
         "subtaskInterval()(uint256)" "targetMineBlocks()(uint256)" \
         "lastMinedEpoch()(uint256)" "currentSubmissions()(uint256)" \
         "flow()(address)" "reward()(address)"; do
  printf '  %-32s ' "$f"; c $MINE "$f"
done
printf '  %-32s ' "balance"; cast balance --rpc-url "$RPC" $MINE

echo "== ChunkLinearReward $REWARD"
for f in "releaseSeconds()(uint256)" "baseReward()(uint256)" "totalBaseReward()(uint256)" \
         "serviceFeeRateBps()(uint256)" "treasury()(address)" "foundationAdmin()(address)" \
         "market()(address)" "mine()(address)"; do
  printf '  %-32s ' "$f"; c $REWARD "$f"
done
printf '  %-32s ' "firstRewardableChunk()"; c $REWARD "firstRewardableChunk()(uint64,uint256)"
printf '  %-32s ' "balance"; cast balance --rpc-url "$RPC" $REWARD

# Pool del chunk que contiene el padding medido (chunk = recallPosition / 32768).
# Ej.: posición de padding 2.349.499.312..2.349.502.463 => chunk ~70
for CH in 68 69 70 71; do
  printf '  rewards(%s)                      ' "$CH"; c $REWARD "rewards(uint256)((uint128,uint128,uint128,uint40,uint40))" "$CH"
done

# Código desplegado (para confirmar que las implementaciones son las del repo)
echo "== eth_getCode sizes"
for a in $FLOW $MINE $REWARD; do
  printf '  %s  %s bytes\n' "$a" $(( $(cast code --rpc-url "$RPC" $a | wc -c) / 2 ))
done

# Escrow de pagos (hijo de Reward): no hay getter en ChunkLinearReward; se localiza por evento
# Deposited del Escrow o por eth_getStorageAt del slot ERC-7201 de PullPayment.
echo "== pendiente de pago al minero atacante (una vez exista)"
echo "  cast call $REWARD 'payments(address)(uint256)' <BENEFICIARY>"
echo "  cast call $MINE  'beneficiaries(bytes32)(address)' <MINER_ID>"
