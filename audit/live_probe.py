#!/usr/bin/env python3
"""PoC / reproduction harness: anchor LIVE state and measure third-party inventory.

Usage:
  RPC_URL=https://evmrpc.0g.ai python3 audit/live_probe.py
  python3 audit/live_probe.py --offline        # show the plan, no network

It compares eth_getCode at every address in deployment_map.json against the
deployedBytecode recorded in the cloned hardhat-deploy artifacts, reads the
deployed parameters with eth_call, and sums the balances (third-party
inventory) that an attacker would have to take from.

Status in this sandbox: RPC_URL hosts are NOT in the outbound allowlist
(only github.com / codeload / api.github.com / npm / pypi). Running without
--offline therefore fails at the network layer; that failure IS the evidence
that live state cannot be anchored here.
"""
import argparse, hashlib, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = json.load(open(os.path.join(HERE, "deployment_map.json")))
RPC = os.environ.get("RPC_URL", "https://evmrpc.0g.ai")
SELECTORS = {
    "market()": "80f55605", "blocksPerEpoch()": "f0682054", "firstBlock()": "231b0268",
    "epoch()": "900cf0cf", "submissionIndex()": "b8a409ac", "poraTarget()": "48f61441",
    "targetSubmissions()": "b776a512", "lastMinedEpoch()": "31223ba7",
    "nSubtasks()": "9dc787a2", "subtaskInterval()": "8f375b36",
    "baseReward()": "76ad03bc", "serviceFeeRateBps()": "c0575111",
    "totalBaseReward()": "7f1b5e43", "treasury()": "61d027b3",
    "foundationAdmin()": "7859f689", "releaseSeconds()": "21295931",
    "getAllLedgers(uint256,uint256)": "987086f0", "getAllActiveServices()": "9ade3972",
}
ROLES = {
    "Flow": "0x62D4144dB0F0a6fBBaeb6296c785C71B3D57C526",
    "Mine": "0xCd01c5Cd953971CE4C2c9bFb95610236a7F414fe",
    "Reward": "0x457aC76B58ffcDc118AABD6DbC63ff9072880870",
    "LedgerManager": "0x2dE54c845Cd948B72D2e32e39586fe89607074E3",
}

# Probes added by the 2026-11-09 refresh. These are the exact unresolved facts
# that decide whether any candidate is LIVE (criterion 3) and whether the
# permissionless / third-party-inventory conditions can be met (criteria 2/4).
PRECOMPILE = "0x0000000000000000000000000000000000001002"
W0G = "0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c"
AGENCY = "0xe1a5162f99e075f8c6681ae28191ab3ac250b468"
BRIDGE = "0x54EbF70B91fe29fdF6F5C6cF726983DDF0DE0750"
PROXIES = [
    ("LedgerManager", "0x2dE54c845Cd948B72D2e32e39586fe89607074E3"),
    ("InferenceServing", "0x47340d900bdFec2BD393c626E12ea0656F938d84"),
    ("FineTuningServing", "0x4e3474095518883744ddf135b7E0A23301c7F9c0"),
]
EXTRA_PROBES = [
    # uninitialized-proxy takeover would be permissionless; check the flag/owner
    ("initialized.LedgerManager", ROLES["LedgerManager"], "0x158ef93e"),
    ("initialized.InferenceServing", PROXIES[1][1], "0x158ef93e"),
    ("initialized.FineTuningServing", PROXIES[2][1], "0x158ef93e"),
    ("owner.LedgerManager", ROLES["LedgerManager"], "0x8da5cb5b"),
    ("owner.InferenceServing", PROXIES[1][1], "0x8da5cb5b"),
    ("owner.FineTuningServing", PROXIES[2][1], "0x8da5cb5b"),
    # W0G native precompile: hardcoded agency and minter caps
    ("precompile.getWA0GI", PRECOMPILE, "0xa9283a7a"),
    ("precompile.minterSupply.Bridge", PRECOMPILE,
     "0x95609212" + "0" * 24 + BRIDGE[2:].lower()),
    ("W0G.totalSupply", W0G, "0x18160ddd"),
    ("bridge.localChainID", BRIDGE, "0xb2bca683"),
    # restaking / DeFi mainnet proxies (ascend-16661.json, rewarder-16661.json)
    ("AscendRouter.getParams", "0x4af366C80Eb17F24923fE956Cc21A11A6864B33a", "0x5e615a6b"),
    ("OracleUpdater.sourceCore", "0xa57e348Afb83153cE2aB27210FFB35c9860B3A42", "0xbc6e4c1d"),
    ("OracleUpdater.maxValue", "0xa57e348Afb83153cE2aB27210FFB35c9860B3A42", "0x94a5c2e4"),
    ("OracleUpdater.owner", "0xa57e348Afb83153cE2aB27210FFB35c9860B3A42", "0x8da5cb5b"),
    ("RestakingStates.getDomains", "0xd5AB0eD30D65f01EC6d6A4BaCA6E466F395334b6", "0x9101cc65"),
]
STORAGE_PROBES = [(f"slot0.{n}", a, 0) for n, a in PROXIES] + [
    ("slot0.agency", AGENCY, 0),
]

def rpc(method, params, timeout=15):
    req = urllib.request.Request(RPC, data=json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        j = json.load(r)
    if "error" in j:
        return None
    return j.get("result")

def hx(s):
    return hashlib.sha256(bytes.fromhex(s[2:])).hexdigest()[:16] if s and s.startswith("0x") else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if a.offline:
        print("PLAN (not executed):")
        print("  eth_chainId, eth_blockNumber")
        n_addr = len({r["address"] for r in MAP["rows"] if r["address"].startswith("0x")})
        print(f"  eth_getCode + eth_getBalance for {n_addr} addresses")
        print("  eth_call for", len(SELECTORS), "deployed-parameter getters on", len(ROLES), "contracts")
        print(f"  {len(EXTRA_PROBES)} refresh probes (initialized/owner, W0G precompile caps, bridge chainId)")
        print(f"  eth_getStorageAt at {len(STORAGE_PROBES)} proxy/agency slot 0 (initialization flag)")
        print("  getAllLedgers pagination for the third-party deposit inventory")
        print(f"  RPC_URL={RPC} (not reachable from this sandbox)")
        return 0
    try:
        chain = rpc("eth_chainId", [])
        block = rpc("eth_blockNumber", [])
    except Exception as e:
        print(f"BLOCKED: no JSON-RPC answer from {RPC}: {type(e).__name__}: {e}")
        print("(network allowlist: github.com, codeload.github.com, api.github.com, npm, pypi)")
        return 2
    if chain is None or block is None:
        print(f"BLOCKED: no JSON-RPC answer from {RPC} "
              "(network allowlist: github.com, codeload.github.com, api.github.com, npm, pypi)")
        return 2
    print(f"LIVE ANCHOR chainId={int(chain,16)} block={int(block,16)}")
    out = dict(chainId=int(chain, 16), block=int(block, 16), addresses=[], params={},
               extra={}, storage={}, inventory_wei=0)
    seen = set()
    for r in MAP["rows"]:
        ad = r["address"]
        if not ad.startswith("0x") or ad in seen:
            continue
        seen.add(ad)
        code = rpc("eth_getCode", [ad, "latest"])
        bal = rpc("eth_getBalance", [ad, "latest"])
        rec = None
        m = __import__("re").search(r"sha256:([0-9a-f]{16})", r["artefact"])
        if m:
            rec = m.group(1)
        live = hx(code)
        out["addresses"].append(dict(address=ad, name=r["name"], code_bytes=len(code or "0x") // 2 - 1 if code else 0,
                                    artifact_sha256=rec, live_code_sha256=live,
                                    bytecode_matches_artifact=(rec is not None and rec == live),
                                    balance_wei=int(bal, 16) if bal else None))
        if bal:
            out["inventory_wei"] += int(bal, 16)
    for role, ad in ROLES.items():
        for sig, sel in SELECTORS.items():
            if role == "Flow" and sig not in ("market()", "blocksPerEpoch()", "firstBlock()", "epoch()", "submissionIndex()"):
                continue
            if role == "Mine" and sig not in ("poraTarget()", "targetSubmissions()", "lastMinedEpoch()", "nSubtasks()", "subtaskInterval()"):
                continue
            if role == "Reward" and sig not in ("baseReward()", "serviceFeeRateBps()", "totalBaseReward()", "treasury()", "foundationAdmin()", "releaseSeconds()"):
                continue
            if role == "LedgerManager" and sig not in ("getAllActiveServices()", "getAllLedgers(uint256,uint256)"):
                continue
            args = "0" * 64 + "0" * 63 + "50" if sig.startswith("getAllLedgers") else ""
            res = rpc("eth_call", [{"to": ad, "data": "0x" + sel + args}, "latest"])
            out["params"][f"{role}.{sig}"] = res
    for label, to, data in EXTRA_PROBES:
        out["extra"][label] = rpc("eth_call", [{"to": to, "data": data}, "latest"])
    for label, to, slot in STORAGE_PROBES:
        out["storage"][label] = rpc("eth_getStorageAt", [to, hex(slot), "latest"])
    out["inventory_0G"] = out["inventory_wei"] / 1e18
    fn = os.path.join(HERE, "live_inventory.json")
    json.dump(out, open(fn, "w"), indent=2)
    print(f"measured balances (native 0G across listed addresses): {out['inventory_0G']:.6f}")
    print("bytecode matches:", sum(1 for x in out["addresses"] if x["bytecode_matches_artifact"]),
          "/", sum(1 for x in out["addresses"] if x["artifact_sha256"]))
    print("written:", fn)
    return 0

if __name__ == "__main__":
    sys.exit(main())
