// Verify that the deployedBytecode recorded in the cloned hardhat-deploy
// artifacts is produced by the exact Solidity literal content embedded in the
// same artifact's compiler metadata. Run from a dir with `solc@0.8.22`:
//   node audit/verify_bytecode.js
// No RPC: this is clone-to-clone bytecode verification (criterion 1/3 evidence).
// Dependency: npm install solc@0.8.22 in the cwd (or set NODE_PATH).
// Artifact path can be overridden with OG_SERVING_CLONE.
const fs = require('fs');
const path = require('path');
let solc;
try { solc = require('solc'); }
catch (e) { solc = require('/home/user/.cache/0g-audit/solc/node_modules/solc'); }

const ART = (process.env.OG_SERVING_CLONE ||
  '/home/user/.cache/0g-audit/repos/0gfoundation__0g-serving-contract') + '/deployments/zgMainnet';
for (const fn of fs.readdirSync(ART).filter(x => x.endsWith('Impl.json')).sort()) {
  const j = JSON.parse(fs.readFileSync(path.join(ART, fn)));
  const meta = JSON.parse(j.metadata);
  const target = Object.values(meta.settings.compilationTarget)[0];
  const targetPath = Object.keys(meta.settings.compilationTarget)[0];
  const sources = {};
  for (const [p, v] of Object.entries(meta.sources)) sources[p] = { content: v.content };
  const settings = {
    optimizer: meta.settings.optimizer,
    evmVersion: meta.settings.evmVersion,
    viaIR: meta.settings.viaIR,
    metadata: meta.settings.metadata,
    remappings: meta.settings.remappings || [],
    libraries: meta.settings.libraries || {},
    outputSelection: { '*': { '*': ['evm.deployedBytecode.object', 'evm.bytecode.object', 'metadata'] } },
  };
  const out = JSON.parse(solc.compile(JSON.stringify({ language: 'Solidity', sources, settings })));
  const errs = (out.errors || []).filter(e => e.severity === 'error');
  if (errs.length) { console.log(fn, 'COMPILE ERRORS:', errs.slice(0, 2).map(e => e.formattedMessage).join('\n')); continue; }
  const c = out.contracts[targetPath][target];
  const got = '0x' + c.evm.deployedBytecode.object;
  const want = j.deployedBytecode;
  const same = got === want;
  console.log(`${fn.padEnd(34)} addr=${j.address} ${target.padEnd(20)} ` +
              `${(got.length - 2) / 2}B  bytecode_match=${same}` +
              (same ? '' : ` got=${got.slice(0, 40)}... want=${want.slice(0, 40)}...`));
}
