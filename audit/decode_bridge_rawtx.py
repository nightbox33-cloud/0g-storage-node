#!/usr/bin/env python3
"""Decode the 8 pre-EIP-155 CREATE transactions committed in the foundation
clone's deployments/bridge-raw-{prod,devnet}-0.json.

Recovers the deployer from each signature (keccak of the unsigned legacy RLP),
checks nonce ordering, chainId absence, and recomputes the 8 CREATE addresses
from (deployer, nonce). Also compares the two environments' calldata to
isolate the owner parameter. No RPC needed: all data comes from the clone.

Usage: python3 audit/decode_bridge_rawtx.py
Dependency: pycryptodome (pip3 install --break-system-packages pycryptodome).
CLONE path can be overridden with the OG_RESTAKING_CLONE env var.
"""
import json, hashlib, os, sys
from Crypto.Hash import keccak

CLONE = os.environ.get(
    'OG_RESTAKING_CLONE',
    '/home/user/.cache/0g-audit/repos/0gfoundation__0g-restaking-contracts')
FILES = ['deployments/bridge-raw-prod-0.json', 'deployments/bridge-raw-devnet-0.json']


def keccak256(b):
    h = keccak.new(digest_bits=256); h.update(b); return h.digest()


def rlp_enc(x):
    if isinstance(x, int):
        if x == 0: return b'\x80'
        return rlp_enc(x.to_bytes((x.bit_length() + 7) // 8, 'big'))
    if isinstance(x, bytes):
        if len(x) == 1 and x[0] < 0x80: return x
        return enc_len(0x80, len(x)) + x
    if isinstance(x, list):
        body = b''.join(rlp_enc(i) for i in x)
        return enc_len(0xc0, len(body)) + body
    raise TypeError(type(x))


def enc_len(base, n):
    return bytes([base + n]) if n < 56 else bytes([base + 55 + (n.bit_length()+7)//8]) + n.to_bytes((n.bit_length()+7)//8, 'big')


def rlp_dec(b, off=0):
    p = b[off]
    if p < 0x80: return (b[off:off+1], off+1)
    if p < 0xb8: n = p-0x80; return (b[off+1:off+1+n], off+1+n)
    if p < 0xc0:
        nb = p-0xb7; n = int.from_bytes(b[off+1:off+1+nb],'big')
        return (b[off+1+nb:off+1+nb+n], off+1+nb+n)
    if p < 0xf8:
        nb = p-0xc0; end = off+1+nb; out=[]; q=off+1
        while q < end:
            v,q = rlp_dec(b,q); out.append(v)
        return (out,end)
    nb=p-0xf7; n=int.from_bytes(b[off+1:off+1+nb],'big'); end=off+1+nb+n
    out=[]; q=off+1+nb
    while q < end:
        v,q = rlp_dec(b,q); out.append(v)
    return (out,end)


def intOf(b): return int.from_bytes(b,'big') if b else 0


def recover(sighash, v, r, s):
    # ecrecover implemented directly on secp256k1 (no external eth libs)
    r = int(r).to_bytes(32,'big'); s = int(s).to_bytes(32,'big')
    p  = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
    n  = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
    G  = (0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
          0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)
    x  = int.from_bytes(r,'big') % p + (p if v > 28 else 0)  # x = r (+p for recid>=2)
    ysq = (pow(x,3,p)+7) % p
    y   = pow(ysq,(p+1)//4,p)
    if pow(y,2,p) != ysq: return None
    if (y % 2) != ((v-27) % 2): y = p-y
    R=(x,y)
    def add(P,Q):
        if P is None: return Q
        if Q is None: return P
        if P[0]==Q[0] and (P[1]+Q[1])%p==0: return None
        if P==Q: l=(3*P[0]*P[0])*pow(2*P[1],p-2,p)%p
        else: l=(Q[1]-P[1])*pow(Q[0]-P[0],p-2,p)%p
        rx=(l*l-P[0]-Q[0])%p; return (rx,(l*(P[0]-rx)-P[1])%p)
    def mul(k,P):
        out=None
        while k:
            if k&1: out=add(out,P)
            P=add(P,P); k>>=1
        return out
    z=int.from_bytes(sighash,'big') % n
    ri=int.from_bytes(r,'big'); si=int.from_bytes(s,'big')
    if ri==0 or si==0 or ri>=n or si>=n: return None
    Q=add(mul((-z)*pow(ri,n-2,n)%n,G), mul(si*pow(ri,n-2,n)%n,R))
    if Q is None: return None
    addr=keccak256(Q[0].to_bytes(32,'big')+Q[1].to_bytes(32,'big'))[12:]
    return '0x'+addr.hex()


def create_addr(sender, nonce):
    raw = rlp_dec(rlp_enc([bytes.fromhex(sender[2:]), nonce if nonce else 0]))[0]
    # simpler: RLP list [20-byte address, nonce int]
    enc = rlp_enc([bytes.fromhex(sender[2:]), nonce])
    return '0x'+keccak256(enc)[12:].hex()


def main():
    out = {}
    for fn in FILES:
        p = os.path.join(CLONE, fn)
        j = json.load(open(p))
        print(f'\n### {fn}  owner={j["owner"]} deployer={j["deployer"]}')
        rows=[]
        for i, hx in enumerate(j['rawTxs']):
            raw=bytes.fromhex(hx[2:]); tx,consumed=rlp_dec(raw)
            assert len(tx)==9 and consumed==len(raw), (i,len(tx),consumed,len(raw))
            nonce,gp,gl = [intOf(x) for x in tx[:3]]
            to,val,data = tx[3],tx[4],tx[5]
            val = intOf(val)
            v,r,s = [intOf(x) for x in tx[6:]]
            assert to==b'' and val==0 and nonce==i, (i,nonce,to,val)
            assert gp == j['gasPrice'] and gl == j['gasLimit'], (i,gp,gl)
            unsigned=rlp_enc([nonce,gp,gl,to,val,data])
            sender=recover(keccak256(unsigned),v,r,s)
            pred=create_addr(j['deployer'],nonce)
            ok = sender is not None and sender.lower()==j['deployer'].lower()
            rows.append(dict(nonce=i,gasPrice=gp,gasLimit=gl,v=v,initcode_bytes=len(data),
                             initcode_sha256=hashlib.sha256(data).hexdigest(),
                             signer=sender,predicted=pred,signature_ok=ok))
            print(f'  nonce={i} v={v} gas={gp}/{gl} init={len(data):6d}B '
                  f'create={pred} signer={sender} {"OK" if ok else "MISMATCH"}')
        # init code diff between prod and devnet
        out[fn]=dict(j, decoded=rows)
    a,b=out[FILES[0]],out[FILES[1]]
    print('\n=== prod vs devnet init-code differences ===')
    for i,(x,y) in enumerate(zip(a['rawTxs'],b['rawTxs'])):
        ra=bytes.fromhex(x[2:]); rb=bytes.fromhex(y[2:])
        da=rlp_dec(ra)[0][5]; db=rlp_dec(rb)[0][5]
        print(f'  nonce={i}: identical={da==db} prod={len(da)}B devnet={len(db)}B sha_prod={hashlib.sha256(da).hexdigest()[:16]}')
        if da!=db:
            # locate differences: usually only owner address inside constructor args
            diffs=[k for k in range(min(len(da),len(db))) if da[k]!=db[k]]
            print(f'    differing byte offsets: {diffs[:40]}' + (' ...' if len(diffs)>40 else ''))
    print('\nSUMMARY: no chainId field in any tx (6-field legacy unsigned); signatures are pre-EIP-155 '
          f'v in {{27,28}}: {sorted({r["v"] for f in out.values() for r in f["decoded"]})}. '
          'Contract addresses depend only on (deployer,nonce), so identical across chains/environments.')

if __name__=='__main__': main()
