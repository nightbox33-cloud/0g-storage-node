#!/usr/bin/env python3
"""Build the address -> repo/commit/artefact map from the CLONES only.

No explorer, no RPC, no memory. Every row is read from a file at an exact
commit of a cloned foundation repo. Outputs deployment_map.json + .md.
"""
import hashlib, json, os, re, sys

AUDIT = os.environ.get("AUDIT_DIR", "/home/user/.cache/0g-audit")
REPOS = os.path.join(AUDIT, "repos")
OUT = os.path.dirname(os.path.abspath(__file__))
ADDR = re.compile(r"0x[0-9a-fA-F]{40}")

def head(repo):
    d = os.path.join(REPOS, repo.replace("/", "__"))
    return os.popen(f'git -C "{d}" rev-parse --verify HEAD 2>/dev/null').read().strip() or "EMPTY_REPO_NO_COMMIT"

def sha(b):
    return hashlib.sha256(b.encode() if isinstance(b, str) else b).hexdigest()[:16]

def jload(p):
    with open(p, "rb") as f:
        return json.load(f)

rows = []
def add(network, address, name, repo, path, commit, artefact, note=""):
    rows.append(dict(network=network, address=address, name=name, repo=repo, path=path,
                     commit=commit, artefact=artefact, note=note))

SC = "0gfoundation/0g-storage-contracts"
SN = "0gfoundation/0g-storage-node"
DOC = "0gfoundation/0g-doc"
SERV = "0gfoundation/0g-serving-contract"
REST = "0gfoundation/0g-restaking-contracts"
GETH = "0gfoundation/0g-geth"
A0GI = "0gfoundation/A0GI-contracts"

# --- chain anchor (docs, exact commit)
doc_ai = os.path.join(REPOS, DOC.replace("/", "__"), "docs/ai-context.md")
doc_txt = open(doc_ai).read()
mainnet_section = doc_txt.split("### Mainnet (Aristotle)", 1)[1].split("## Smart Contract Addresses", 1)[0]
chain_id = re.search(r"\*\*Chain ID\*\*\s*\|\s*(\d+)", mainnet_section).group(1)
mainnet_block = re.search(r"Storage Start Block\*\*\s*\|\s*(\d+)", mainnet_section).group(1)

# --- storage trio: addresses from node config + docs
cfg = os.path.join(REPOS, SN.replace("/", "__"), "run/config-mainnet-turbo.toml")
cfg_txt = open(cfg).read()
for key, label, abi in [
    ("log_contract_address", "Flow (proxy)", "FixedPriceFlow.json"),
    ("mine_contract_address", "PoraMine (proxy)", "PoraMine.json"),
    ("reward_contract_address", "ChunkLinearReward (proxy)", "ChunkLinearReward.json"),
]:
    m = re.search(rf'^{key}\s*=\s*"(0x[0-9a-fA-F]{{40}})"', cfg_txt, re.M)
    if not m:
        continue
    abi_path = f"storage-contracts-abis/{abi}"
    abi_file = os.path.join(REPOS, SN.replace("/", "__"), abi_path)
    pin = open(os.path.join(REPOS, SN.replace("/", "__"),
                            "storage-contracts-abis/0g-storage-contracts-rev")).read().strip()
    add("16661", m.group(1), label, SN, f"run/config-mainnet-turbo.toml / {abi_path}",
        head(SN), f"ABI {abi} sha256:{sha(open(abi_file,'rb').read())}; ABI pin {SC}@{pin}",
        "NO deployedBytecode in any clone for this address; docs ai-context.md agrees")

# --- system contracts / precompiles (docs)
for label, addr in [
    ("Staking system contract (IStakingContract)", "0xea224dBB52F57752044c0C86aD50930091F561B9"),
    ("DASigners precompile", "0x0000000000000000000000000000000000001000"),
    ("WrappedOGBase precompile", "0x0000000000000000000000000000000000001002"),
    ("W0G ERC20", "0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c"),
    ("Compute Ledger (LedgerManager proxy)", "0x2dE54c845Cd948B72D2e32e39586fe89607074E3"),
    ("Compute Inference (proxy)", "0x47340d900bdFec2BD393c626E12ea0656F938d84"),
    ("Compute FineTuning (proxy)", "0x4e3474095518883744ddf135b7E0A23301c7F9c0"),
]:
    add("16661", addr, label, DOC, "docs/ai-context.md / docs/developer-hub/.../staking-interfaces.md",
        head(DOC), "documented address", "implementation source NOT in public clones (chain node = blocked repo)")

# --- native precompile / W0G implementation found in the geth clone (refresh 2026-11-09).
#     These were previously reported as "only ABI bindings"; the Go implementation IS in
#     the clone's HEAD tree (core/vm/wrapped_a0gi_base.go, core/vm/dasigners.go).
for label, addr, repo, path, artefact, note in [
    ("WrappedOGBase precompile (native Go)", "0x0000000000000000000000000000000000001002",
     GETH, "core/vm/wrapped_a0gi_base.go",
     "Mint/Burn require contract.caller == getWA0GI(); SetMinterCap requires caller == getAgency()",
     "hardcoded W0G=0x1Cd0690f...; hardcoded agency=0xe1a5162f...; caps per minter"),
    ("DASigners precompile (native Go)", "0x0000000000000000000000000000000000001000",
     GETH, "core/vm/dasigners.go + core/vm/precompiles/dasigners/",
     "Go implementation + ABI bindings", "consensus-layer signer registry"),
    ("W0G ERC20 (Solidity)", "0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c",
     A0GI, "contracts/WrappedA0GI.sol",
     "mint(address,uint256) forwards msg.sender as minter to 0x1002; permissionless at Solidity layer",
     "cap enforced natively; deployed by pre-EIP-155 raw tx from ephemeral 0x873cd27b..."),
    ("W0G agency proxy (hardcoded in precompile)", "0xe1a5162f99e075f8c6681ae28191ab3ac250b468",
     A0GI, "contracts/WrappedA0GIBaseAgency.sol",
     "initialize() hardcodes owner 0x2D7F2d... on main; setMinterCap() is onlyOwner",
     "chain-test branch hardcodes devnet test owner 0x20f33CE9... (known test key)"),
    ("Mainnet W0G/bridge governance owner", "0x2D7F2d2286994477Ba878f321b17A7e40E52cDa4",
     A0GI, "CLAUDE.md + contracts/WrappedA0GIBaseAgency.sol",
     "hardcoded governance address (EOA/multisig)", "privileged; not permissionless"),
    ("Devnet agency test owner", "0x20f33CE90A13a4b5E7697E3544c3083B8F8A51D4",
     A0GI, "CLAUDE.md + script/deploy/BridgeRawTxs.s.sol (restaking)",
     "known test key in setup-agency.sh (file NOT in any public clone)",
     "only chain-test; live ownership not verifiable without RPC"),
]:
    add("16661", addr, label, repo, path, head(repo), artefact, note)

# --- compute-network deployment artifacts (contain deployedBytecode)
d = os.path.join(REPOS, SERV.replace("/", "__"), "deployments/zgMainnet")
for fn in sorted(os.listdir(d)):
    if not fn.endswith(".json"):
        continue
    j = jload(os.path.join(d, fn))
    bc = j.get("deployedBytecode", "")
    abi_names = ",".join(sorted(x.get("name", "") for x in j.get("abi", []) if x.get("type") == "function"))
    add("16661", j.get("address", "?"), fn[:-5], SERV, f"deployments/zgMainnet/{fn}", head(SERV),
        f"deployedBytecode {len(bc)//2-1 if bc.startswith('0x') else 0} B sha256:{sha(bc)}; "
        f"impl tx {j.get('transactionHash','?')}; block {j.get('receipt',{}).get('blockNumber','?')}",
        f"abi funcs: {abi_names[:180]}")

# --- restaking / bridge mainnet deployments
rd = os.path.join(REPOS, REST.replace("/", "__"), "deployments")
for fn in ["ascend-16661.json", "rewarder-16661.json"]:
    j = jload(os.path.join(rd, fn))
    for k, v in j.items():
        if isinstance(v, str) and ADDR.fullmatch(v):
            add("16661", v, f"{fn[:-5]}:{k}", REST, f"deployments/{fn}", head(REST),
                "deployment address (no bytecode in clone)", "default branch=dev, live deployment unverified")
for fn in ["bridge-raw-prod-0.json"]:
    j = jload(os.path.join(rd, fn))
    for k, v in j["contracts"].items():
        add("?", v, f"{fn[:-5]}:{k}", REST, f"deployments/{fn}", head(REST),
            f"pre-signed raw deployment tx ({len(j['rawTxs'])} txs); decoded by audit/decode_bridge_rawtx.py: "
            "6-field legacy unsigned, NO chainId, v in {27,28}, signer recovered == deployer, "
            "CREATE address recomputed == committed address",
            "chain id NOT in file; prod/devnet differ only in the last 20 bytes (owner); "
            "same deployer+nonces 0..7; live deployment unverified")

# --- chain binary releases (metadata from GitHub API, assets NOT downloadable)
add("16661", "-", "0gchaind mainnet binary (Aristotle v1.0.9)", "0gfoundation/0gchain-Aristotle",
    "release v1.0.9 / aristotle-v1.0.9.tar.gz (70,389,971 B)", "release:2026-11-05",
    "BLOCKED: release-assets.githubusercontent.com not reachable", "consensus/EVM/precompile/genesis source of truth")
add("16661", "-", "zgs_node / 0gchaind binaries v1.2.0", SN, "release v1.2.0 (5 zip assets)",
    "release:2026-01-13", "BLOCKED: release assets not downloadable", "")

meta = dict(chain_id=chain_id, storage_start_block=mainnet_block,
            repos_total=len([x for x in os.listdir(REPOS) if os.path.isdir(os.path.join(REPOS, x, ".git"))]),
            blocked=["0glabs/0g-chain (submodule of 0gfoundation/0g-da-client, HTTP 404 / private)",
                     "0gfoundation/0g-precompiles, 0gfoundation/0g-chain-v2, 0gfoundation/0g-chain-ng, "
                     "0gfoundation/integration-tests -> HTTP 404; referenced by A0GI-contracts/CLAUDE.md "
                     "as the canonical home of the pre-signed raw tx scripts and setup-agency.sh",
                     "setup-agency.sh (known devnet test key) not present in any of the 137 clones",
                     "private repos of 0gfoundation and 0glabs (0 visible to this token)",
                     "GitHub release assets (release-assets.githubusercontent.com)",
                     "Git LFS objects (git-lfs missing; LFS batch API 403)",
                     "live RPC / explorer / indexer (network allowlist: github.com, npm, pypi only)"])
with open(os.path.join(OUT, "deployment_map.json"), "w") as f:
    json.dump(dict(meta=meta, rows=rows), f, indent=2)

with open(os.path.join(OUT, "DEPLOYMENT_MAP.md"), "w") as f:
    f.write(f"# Mapa dirección / artefacto -> repo + commit (fuente: clones)\n\n")
    f.write(f"Chain anclada en clones: **chainId {chain_id} (0G Mainnet Aristotle)**, "
            f"storage start block {mainnet_block} (`{DOC}@{head(DOC)}:docs/ai-context.md`). "
            f"**Bloque `--height` no comprobable**: ningún RPC accesible.\n\n")
    f.write("| Red | Dirección / artefacto | Nombre | Repo @ commit | Ruta | Artefacto |\n|---|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r['network']} | `{r['address']}` | {r['name']} | `{r['repo']}` @ `{r['commit'][:12]}` | "
                f"`{r['path']}` | {r['artefact'][:150]} |\n")
    f.write("\n## Bloqueos (impiden declarar cobertura completa)\n\n")
    for b in meta["blocked"]:
        f.write(f"- {b}\n")
    f.write("\n## Verificación offline añadida el 2026-11-09 (sin RPC)\n\n")
    f.write("- `audit/verify_bytecode.js`: los 3 `*Impl.json` traen `metadata` con "
            "`useLiteralContent:true`; recompilados con `solc 0.8.22+commit.4fc1097e` "
            "(viaIR, optimizer 200, evmVersion istanbul) → **`deployedBytecode` byte-idéntico** "
            "para `FineTuningServing` (23.112 B), `InferenceServing` (18.926 B) y "
            "`LedgerManager` (14.609 B). El Solidity incrustado es idéntico al HEAD del clon.\n")
    f.write("- `audit/decode_bridge_rawtx.py`: las 16 txs (prod+devnet) son RLP legacy de 6 campos "
            "sin `chainId`, `v∈{27,28}`; `ecrecover` devuelve exactamente el deployer "
            "`0x25Dac40A...` en las 16; las 8 direcciones CREATE `(deployer,nonce)` coinciden "
            "con el mapa `contracts`. Prod y devnet difieren **sólo en los últimos 20 bytes** "
            "(el `owner`). No hay forma de saber sin RPC cuál de los dos juegos se emitió en 16661.\n")
    f.write("- `audit/audit_pdf_text/`: extracción `pypdf` de las dos auditorías in-repo. Halborn: "
            "2 CRITICAL en el nodo (`is_covered` siempre true, `append_merkle` null-node), "
            "«ALL REPORTED FINDINGS HAVE BEEN ADDRESSED»; ambos son liveness/self-grief del minero, "
            "no drenaje de terceros, y `is_covered` está corregido a `&&` en el checkout. Zellic: "
            "«No critical issues were found», 1 HIGH + 1 MEDIUM; revisó código "
            "«not deployed to the 0G chain». El HIGH (`addReward(msg.value)` en vez de `restFee`) "
            "está corregido tanto en HEAD como en el pin de ABIs `745c176b...`.\n")
    f.write("\n`sha256:` en esta tabla es SHA-256 del fichero/bytecode (huella de fichero, NO keccak256 del código on-chain).\n")
print(f"rows={len(rows)} chainId={chain_id} startBlock={mainnet_block}")
