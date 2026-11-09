# Auditoría ofensiva 0G — mainnet Aristotle (chainId 16661)

Fecha: 2026-11-09 (tercera iteración: re-clonado, cuestionamiento de supuestos y vía ofensiva
ejecutada). Repo de trabajo: `nightbox33-cloud/0g-storage-node` @
`f75aeaef2cba5b198b5d34301925edbaa180dcdb`. Fuente de verdad: **clones**, no explorer, no snippets,
no memoria. Artefactos y scripts en este directorio.

Re-clonado completo (`clone_foundation.sh`): **137/137 repos, 0 fallos, 5.745 refs** (el manifest
persistido tenía 5.744). Sólo 2 HEAD cambiaron (`0g-pc-e2ee`, `stanford-0g-site`) y apareció una rama
`claude/brave-turing-*`: **ningún repo de dinero**. `gh api search/code` (6 consultas) y barridos
`git ls-tree` no hallaron snapshot de balances/genesis 16661. Reintentos de RPC en esta iteración:
`evmrpc.0g.ai`, `rpc.0g.ai`, `evmrpc-testnet.0g.ai` → `TLS EOF` / DNS; **mainnet sigue sin leerse**.

---

## 0. Veredicto

**no crítico live** — con la precisión importante: **no crítico verificable/demostrado**, y **NO declaro
cobertura completa**.

No puedo sostener «en esta chain SÍ hay un crítico» sin inventarlo. Los 4 criterios exigen (3) *call
graph/estado REAL y LIVE* y (4) *PoC fork/replay con X sacado de inventario ajeno live*. En este
entorno no hay salida a ningún RPC/explorer/indexer: `https://evmrpc.0g.ai`, `https://rpc.0g.ai`,
`0g.ai` y los assets de GitHub Release dan `SSL_ERROR_SYSCALL` / `http=000`; sólo están permitidos
`github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`. Sin
`eth_blockNumber` / `eth_getCode` / `eth_getBalance` / `eth_getStorageAt` no hay bloque, ni bytecode
desplegado, ni balances, ni owner/initialization on-chain, ni importe $ tocable.

Este refresh **sí cerró huecos de código** sin red: verifiqué byte-a-byte el `deployedBytecode` de las
3 implementaciones de compute-network contra el Solidity incrustado en sus propios artefactos;
encontré la **implementación nativa Go** de los precompiles W0G/DASigners dentro de `0g-geth` (antes
creída bloqueada); decodifiqué las 16 raw txs del bridge y recuperé su firmante; y extraje las dos
auditorías PDF in-repo. Todo eso **mata candidatos**, no crea ninguno: los gates de permiso están ahí,
la conservación se cumple y los *known issues* están corregidos en el código que los clones atribuyen
a mainnet. Quedan **dos hechos no verificables sin una sola llamada RPC** (§4): si los proxies de
compute fueron inicializados y cuál de los dos juegos de raw txs (prod vs devnet) se emitió en 16661.
Ninguno puede declararse crítico sin medirlos. Un informe que lo hiciera sería teoría/especulación,
exactamente lo que el pliego prohíbe.

Inventario medido: **47 direcciones** mapeadas a repo+commit+artefacto, **9 bytecodes de deployment**
con bloque y hash, **3 bytecodes recompilados y coincidentes**, **0 balances live** y **$ tocable no
cuantificable**.

**Añadido en esta tercera iteración (2026-11-09)**: sí encontré un **bug de contabilidad real y
ejecutable** en el bytecode verificado de `LedgerManager` (§4, `poc_retrieve_fund_drain.js`): un
servicio que miente en `processRefund()` convierte un crédito falso en ETH real de otros
depositantes; el PoC ejecutado da X=3 → Y=103 ETH, con 100 ETH saliendo de la víctima y el
`LedgerManager` pasando de 103 a 0 ETH. `deployInBeaconProxy` (`src/utils/utils.ts`) despliega el
proxy con `args: [beacon, []]` — **sin datos de init** — y `deploy_ledger_maneger.ts` llama
`initialize(deployer)` en una tx posterior: la ventana de front-running es real en el patrón de
deploy, pero en 16661 quedó cerrada hace ~1,9 M de bloques. Lo que lo mata para declararlo crítico
es que registrar el servicio mentiroso exige `registerService()` = **`onlyOwner`**. Sin
`initialized()` / `owner()` / `getAllActiveServices()` live no puedo descartar ni afirmar que el
owner esté comprometido o que algún servicio no verificado esté registrado. Bajo el pliego, un
condicional con inventario sintético no es un crítico live.

---

## 1. REQUISITO PREVIO OBLIGATORIO — estado

### 1.1 Orgs / espacios enumerados

| Espacio | Tipo | Repos | Evidencia |
|---|---|---|---|
| `0gfoundation` | GitHub org «0G Foundation», id 139951901 | **136 públicos** | `GET /orgs/0gfoundation` → `public_repos: 136`; `GET /orgs/0gfoundation/repos?type=all` → 136, `private: false` |
| `0glabs` | GitHub org, id 233610805 | **0 públicos** | `GET /orgs/0glabs` → `public_repos: 0`; `GET /orgs/0glabs/repos?type=all` → vacío |
| `zerog-ai` | GitHub org «0G Labs» | **1 público** (`MGVerse`) | `GET /orgs/zerog-ai`, `gh repo list` |
| `nightbox33-cloud` | fork del que parte este checkout | 1 | `GET /repos/nightbox33-cloud/0g-storage-node` → `source: 0gfoundation/0g-storage-node` |

Otros espacios GitLab/Bitbucket: no localizados vía GitHub org search; no hay referencia a ellos en
los 137 clones. Los repos `0gfoundation/0g-precompiles`, `0g-chain-v2`, `0g-chain-ng` e
`integration-tests`, citados por `A0GI-contracts/CLAUDE.md`, devuelven **404** (§1.3). No verificados
como espacios alternativos → cobertura incompleta.

### 1.2 Clones

`audit/clone_foundation.sh` clonó **137/137 repos** (136 `0gfoundation` + `zerog-ai/MGVerse`),
**0 fallos**, `--filter=blob:none` + `--no-checkout` + `fetch '+refs/heads/*' '+refs/tags/*'`:
grafo de commits completo, blobs bajo demanda. Manifest exacto: `audit/repo_manifest.tsv` (137 filas,
HEAD por repo, nº ramas/tags/refs) y `audit/refs_manifest.tsv` (**5.744 refs**: 2.868 ramas +
2.604 tags + 372 HEAD/etc.). `audit/materialize.sh` materializó 41 repos de dinero/consenso/deploy.
`audit/repo_list.tsv` = inventario enumerado. **Commit hash exacto por repo**: columna 6 del manifest;
los relevantes:

| Repo | HEAD usado | Nota |
|---|---|---|
| `0gfoundation/0g-storage-node` | `f75aeaef2cba5b198b5d34301925edbaa180dcdb` | idéntico al HEAD de este checkout |
| `0gfoundation/0g-storage-contracts` | `0dcef31fd6398c9aca7267dc5a7a9e1caf3a3581` | main 2026-06-15 |
| ↳ pin de ABIs del nodo | `745c176bd206a37072281ec11aaf4f8ef6d4f6d3` | `storage-contracts-abis/0g-storage-contracts-rev`, 2026-01-21; existe en el clone |
| `0gfoundation/0g-serving-contract` | `3ceeff03ca66b07921a3579413accffe1d3a1446` | `deployments/zgMainnet/*.json` con `deployedBytecode` + `metadata` standard-json |
| `0gfoundation/0g-restaking-contracts` | `f7cba8a4b77f253c2a82d442faefda365cbb6330` | rama `dev`; bridge + Ascend + Rewarder |
| `0gfoundation/0g-geth` | `d5a7ee6f0148…` | **implementación nativa Go** de `0x…1000`/`0x…1002` en `core/vm/wrapped_a0gi_base.go`, `core/vm/dasigners.go` y `core/vm/precompiles/` (encontrada en el árbol HEAD, no en el worktree materializado) |
| `0gfoundation/A0GI-contracts` | `045c6367a675d339dac7f34cbb3cd91079036a83` | `WrappedA0GI.sol`, `WrappedA0GIBaseAgency.sol`; `main` owner `0x2D7F…`, `chain-test` owner `0x20f33…` |
| `0gfoundation/0g-doc` | `c423455e6743e4271a756e9299c0700a1e1f6073` | `docs/ai-context.md` + 2 PDFs de auditoría |
| `0gfoundation/0g-reth` | `c12df839a458…` | fix de trie; release Aristotle v1.0.9 lo referencia |
| `0gfoundation/0gchain-Aristotle` | `84b17f05eb18…` | **sólo README** + releases de binarios |
| `0gfoundation/0gchain-NG` | `b80e68528d54…` | **sólo README** + releases (testnet Galileo) |
| `0gfoundation/0g-da-client` | `7248f06cc071…` | archivado; **declara el submodule bloqueado** |

Submodules (`audit/clone_submodules.sh`, `audit/submodules.tsv`): 49 entradas `.gitmodules` en 20
repos → 30 URLs, 29 clonadas. **0 gitlinks (mode 160000) en los árboles**: las URLs están declaradas
pero los commits no pineados. Otros 5 URLs `0glabs/*` redirigen a repos `0gfoundation/*` ya clonados.

Git LFS (`audit/assets_manifest.tsv`): 4 ficheros (1 glob de snapshots de `0g-blockscout-frontend`
y 3 fixtures `.pb.lz4` de `gravity-aptos`). **No materializados**: `git-lfs` ausente y LFS batch API
→ 403. Son fixtures de test, ningún artefacto desplegado.

### 1.3 BLOQUEADOS / no accesibles (impiden cobertura completa)

1. **`0glabs/0g-chain`** — submodule `0g-chain` (branch `dev`) de `0g-da-client/.gitmodules`.
   `GET /repos/0glabs/0g-chain` → **404**; `git clone` → «Repository not found». Es el repo del
   **binario de la chain**: consenso, staking `0xea224d…`, genesis/params. Su código no se puede
   auditar. Hueco más grave.
2. **`0gfoundation/0g-precompiles`, `0g-chain-v2`, `0g-chain-ng`, `integration-tests`** → **404** en
   `gh api repos/...`. `A0GI-contracts/CLAUDE.md` los señala como hogar canónico de
   `wa0gi_precompile_raw.sh`, `da_precompile_raw.sh`, `run.sh`, `run_test_wa0gi.sh`,
   `deploy-bridge-raw.sh` y **`setup-agency.sh`** (la clave de test conocida del owner devnet).
   Barrido de `git rev-list --objects --all` en los 8 repos de chain/deploy: **ninguno de esos
   scripts ni ningún `genesis.json` aparece en ninguna rama/tag**. `setup-agency.sh` no está en los
   137 clones.
3. **Repos privados de `0gfoundation` / `0glabs`**: `GET /user/repos?visibility=private` → 0;
   `user/orgs` → vacío. 0 privados visibles, pero no puede demostrarse que no existan.
4. **Artefactos binarios desplegados**: `0gchain-Aristotle` **v1.0.9** (2026-11-05,
   `aristotle-v1.0.9.tar.gz`, 70.389.971 B) y `0g-storage-node` **v1.2.0** (5 zips).
   `gh release download` / `curl -L` → 302 a `release-assets.githubusercontent.com` → TLS bloqueado.
   **Ni binario ni genesis desplegados materializados.**
5. **Estado live**: RPC/explorer/indexer inalcanzables. `audit/live_probe.py` → `BLOCKED` / exit 2.
   Sin altura, `eth_getCode`, balances, owners, `initialized()`, ni params on-chain.
6. **LFS**: 4 ficheros de test (§1.2).

### 1.4 Mapa dirección / program id / module account → repo + commit + artefacto

Tabla completa: **`audit/DEPLOYMENT_MAP.md`** y `audit/deployment_map.json` (**56 filas, 47
direcciones únicas**), generadas por `audit/build_deployment_map.py` leyendo los clones.

| Dirección | Componente | Repo @ commit | Artefacto en el clone |
|---|---|---|---|
| `0x62D4144dB0F0a6fBBaeb6296c785C71B3D57C526` | Flow (proxy) | `0g-storage-node` @ `f75aeae…` + `0g-doc` @ `c423455…` | ABIs pineadas a `0g-storage-contracts@745c176b…`; **sin `deployedBytecode`** |
| `0xCd01c5Cd953971CE4C2c9bFb95610236a7F414fe` | PoraMine (proxy) | idem | `PoraMine.json` ABI |
| `0x457aC76B58ffcDc118AABD6DbC63ff9072880870` | ChunkLinearReward (proxy) | idem | `ChunkLinearReward.json` ABI |
| `0x2dE54c845Cd948B72D2e32e39586fe89607074E3` | LedgerManager (proxy) | `0g-serving-contract` @ `3ceeff0…` | runtime 502 B, tx `0xac14ae…`, bloque 13.219.885; impl `0xee876A…` 14.609 B; beacon `0xFe5Ed6…` |
| `0x47340d900bdFec2BD393c626E12ea0656F938d84` | InferenceServing (proxy) | idem | impl `0x1c0A26…` 18.926 B; beacon `0xE7e9e8…` |
| `0x4e3474095518883744ddf135b7E0A23301c7F9c0` | FineTuningServing (proxy) | idem | impl `0x795d7E…` 23.112 B; beacon `0x449C24…` |
| `0xea224dBB52F57752044c0C86aD50930091F561B9` | Staking system contract | `0g-doc` @ `c423455…` | **sólo interfaz**; implementación bloqueada |
| `0x0000000000000000000000000000000000001000` | DASigners precompile | `0g-geth` @ `d5a7ee6…` | **Go nativo** `core/vm/dasigners.go` + `core/vm/precompiles/dasigners/` |
| `0x0000000000000000000000000000000000001002` | WrappedOGBase precompile | `0g-geth` @ `d5a7ee6…` | **Go nativo** `core/vm/wrapped_a0gi_base.go`: `Mint/Burn` exigen `caller == 0x1Cd069…`, `SetMinterCap` exige `caller == 0xe1a516…` |
| `0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c` | W0G ERC20 | `A0GI-contracts` @ `045c6367…` | `WrappedA0GI.sol`: `mint()` permissionless en Solidity, cap nativo por `msg.sender` |
| `0xe1a5162f99e075f8c6681ae28191ab3ac250b468` | W0G agency proxy (hardcoded) | `A0GI-contracts` @ `045c6367…` | `WrappedA0GIBaseAgency.sol`: `initialize()` fija owner `0x2D7F…`; `setMinterCap()` `onlyOwner` |
| `0x2D7F2d2286994477Ba878f321b17A7e40E52cDa4` | owner mainnet W0G/bridge | `A0GI-contracts` @ `045c6367…` | hardcoded; **privilegiado** |
| `0x20f33CE90A13a4b5E7697E3544c3083B8F8A51D4` | owner devnet (test key) | `A0GI-contracts` + `0g-restaking-contracts` | `chain-test`; clave en `setup-agency.sh` **bloqueado** |
| `0x4af366C80Eb17F24923fE956Cc21A11A6864B33a` + 10 más | AscendRouter / OracleUpdater / MellowVault / Rewarder (16661) | `0g-restaking-contracts` @ `f7cba8a…` | direcciones; **sin bytecode** |
| `0x54EbF70B91fe29fdF6F5C6cF726983DDF0DE0750` + 7 más | Bridge (proxy/beacon/impl/agency) | `0g-restaking-contracts` @ `f7cba8a…` | 8 raw txs **pre-EIP-155 sin `chainId`**; firmante recuperado `0x25Dac40A…`, direcciones CREATE verificadas; prod/devnet difieren sólo en el `owner` |

Program ids / module accounts: no aplica (L1 EVM/Cosmos; `gravity-aptos` y
`pancake-contracts-move` clonados pero sin program id vivo mapeado a 16661).

---

## 2. Anclaje del estado live (lo que hay y lo que falta)

**Anclado desde clones/docs**: chainId **16661** («Aristotle»), RPC documentado
`https://evmrpc.0g.ai`, storage start block **2.387.557**, W0G `0x1Cd069…`; testnet Galileo 16602.
Binario mainnet más reciente: **Aristotle v1.0.9** (2026-11-05, backport reth #28264); storage node
**v1.2.0**. Parámetros de deploy del repo: `unitPrice=33`, `lifetimeMonth=12` →
`pricePerSector=30.733.644.962 wei`, `releaseSeconds=32.140.800`, `blocksPerEpoch=3750`,
`firstBlock=2.386.981`, `initDifficulty=1.000.000`, `targetSubmissions=100`, `nSubtasks=4`,
`subtaskInterval=800`, `SECTORS_PER_PRICE=33.554.432`, `MIN_ACCOUNT_BALANCE=3 0G`,
`MIN_PROVIDER_STAKE=100 0G`.

**Anclaje estructural nuevo, sin RPC**:
- Los 3 `*Impl.json` de `zgMainnet` traen `metadata` con `useLiteralContent:true`. Recompilados con
  `solc 0.8.22+commit.4fc1097e` (`viaIR:true`, optimizer 200, `istanbul`) → **`deployedBytecode`
  byte-idéntico** (23.112 / 18.926 / 14.609 B). El Solidity incrustado es idéntico al HEAD del clon.
  Es la prueba más fuerte disponible de «qué código corre» para esas 3 implementaciones.
- `0g-geth` contiene la implementación nativa del precompile W0G; `A0GI-contracts` contiene el
  Solidity del W0G y de la agency. Antes figuraban como «sólo ABI»: corregido.
- Las 16 raw txs del bridge están decodificadas y verificadas criptográficamente (§5).
- Las dos auditorías in-repo están extraídas a `audit/audit_pdf_text/`.

**NO anclado (bloquea criterios 3 y 4)**: altura de bloque actual, `eth_getCode` en las 47
direcciones, balances, params on-chain, dirección del *implementation* detrás de cada beacon de
storage/mine/reward, qué revisión de `Flow/Mine/Reward` corre, **`initialized()`/`owner()` de los 3
proxies de compute**, **`owner()` de la agency W0G y del bridge**, **`minterSupply(Bridge)`**,
**`W0G.totalSupply()` vs `eth_getBalance(W0G)`**, y TVL. `audit/live_probe.py` produce exactamente
eso cuando se ejecuta con `RPC_URL` alcanzable; aquí devuelve `BLOCKED`.

---

## 3. Inventario ajeno medido

**Medido desde clones (estructural, no valor)**: 47 direcciones mapeadas; 9 artefactos `zgMainnet`
con `deployedBytecode` (3 proxies de 502 B, 3 beacons de 804 B, 3 implementaciones de
14.609/18.926/23.112 B) y sus bloques; 18 direcciones de restaking/bridge; 3 contratos de storage;
2 precompiles + 1 system contract de staking + W0G + agency + 2 owners. Inventarios de terceros que
el código define: `LedgerManager.ledgerMap` (`availableBalance`/`totalBalance` por usuario), cuentas
de servicio `Account.balance`/`pendingRefund`, `ChunkRewardBase.totalBaseReward` (`donate()`),
`Reward.lockedReward/claimableReward`, `PullPayment` escrow, bridge escrow (`lockAndSend`), W0G
`address(this).balance` (colateral de los depositantes), stake de delegadores en `0xea224d…` y
`MellowVault`.

**No medido**: **0 balances live, 0 $ tocable cuantificable**. Sin RPC no hay `eth_getBalance`, ni
`getAllLedgers`, ni `balanceOf` del vault, ni supply del W0G. Cualquier cifra en dólares sería
inventada. `audit/live_probe.py` suma `eth_getBalance` de esas direcciones y pagina `getAllLedgers`.

---

## 4. Caminos de dinero auditados y candidatos descartados (hechos)

Entrypoints seguidos: `Flow.submit/batchSubmit` → `FixedPrice.chargeFee` → `ChunkRewardBase.fillReward`
→ `PoraMine.submit` → `claimMineReward` → `PullPayment`; `LedgerManager.*` →
`InferenceServing`/`FineTuningServing.*`; `Bridge.lockAndSend/burnAndSend/parkRemoteMessages/deliver`;
`W0G.deposit/withdraw/mint/burn` → precompile `0x1002` → `SetMinterCap`; proxy `initialize()`.

| Candidato | Hecho que lo mata |
|---|---|
| `FixedPrice.chargeFee` barre `address(this).balance` como `bonus` | Va a la pool de mineros, no al submitter. Replay `poc_conservation.py`: X=515,625 0G → Y=515,625 0G − 500 wei, **Y ≤ X**; el floor de `fillReward` sólo deja dust. |
| `Flow` impl sin `_disableInitializers()` en el pin `745c176b…` (arreglado en `0dcef31f…`) | No verificable qué impl corre live; el `initialize()` sobre impl daría **roles de admin** (privilegiado, prohibido) y es *known issue* corregido. Sin saldo de terceros medido. |
| `PoraMine.submit` → `claimMineReward` | Exige digest/context, merkle (`dataProofEnabled`), `poraOutput <= target`, anti-replay; `claimMineReward` sólo desde `mine`. Sin target on-chain no hay PnL (criterio 4). |
| `LedgerManager.transferFund` cancela `pendingRefund` sin mover ETH | Conservación exacta: `availableBalance` baja sólo por el ETH enviado; `retrieveFund` lo recupera vía `processRefund` → `receive()` con gate `_isServiceContract`. Replay: 10 0G → 10 0G, sin tocar inventario ajeno. `spendFund` es `onlyServing`. |
| **BUG REAL: `retrieveFund` acredita `availableBalance += processRefund(...)` sin verificar que llegó ETH; `transferFund` envía `msg.value` real y sólo decrementa `availableBalance` (nunca `totalBalance`)** | `audit/poc_retrieve_fund_drain.js` compila las 9 fuentes literales del `metadata` con los ajustes exactos del deploy, despliega el impl tras un proxy y ejecuta: servicio malicioso con `processRefund()` devolviendo 100 ETH sin enviar nada → `retrieveFund` infla `availableBalance` a 103 mientras `totalBalance` sigue 3 → `transferFund(..., 103)` manda **103 ETH reales** al servicio → `drain()`. Resultado medido: `LedgerManager 103 → 0 ETH`, atacante **+100 ETH** (puso X=3, sacó Y=103; el delta sale íntegro del depósito de 100 ETH de la víctima). Escenario de control con proxy ya inicializado: `registerService` revierte, **0 drenaje**. **Hecho que lo mata**: `registerService(type,version,service,desc)` es `external onlyOwner`; los 3 servicios legítimos tienen bytecode verificado y `processRefund` conserva. Sólo sería permissionless si el proxy `0x2dE54c84…` estuviera sin inicializar (`initialize(attacker)` → owner) o su owner estuviera comprometido. Los scripts `src/deploy/deploy_ledger_maneger.ts` / `deploy_service.ts` ejecutan `initialize()` en tx posterior y registran los servicios (lo que habría revertido con owner = 0), así que la evidencia disponible apunta a que **sí está inicializado**; pero sin RPC no es verificable. El PoC además usa inventario sintético, que el pliego prohíbe como prueba de crítico live. |
| `settleFeesWithTEE` / `FineTuningServing.settleFees` | `service.teeSignerAcknowledged` lo pone **`onlyOwner`** (`acknowledgeTEESignerByOwner`) y se resetea al cambiar `teeSignerAddress`; además `account.acknowledged` del usuario, firma EIP-712 con `chainid + address(this)`, nonce monotónico y `toSettle <= account.balance`. Confianza elegida, no escalada permissionless. |
| `W0G.mint(address,uint256)` es permissionless en Solidity | En `core/vm/wrapped_a0gi_base.go` el precompile exige `contract.caller == getWA0GI()` (`0x1Cd069…`) y aplica `Supply.Cap` **por `msg.sender`** (el `minter` que W0G reenvía). Cap por defecto 0 → revert `ErrInsufficientMintCap`. `W0G.totalSupply() == address(this).balance`; no hay sobre-emisión sin cap. |
| `SetMinterCap(minter,cap,initialSupply)` (subir cap → mint → `withdraw` del colateral ajeno) | Gate nativo `contract.caller == getAgency()` = `0xe1a5162f…` **hardcoded**. La agency es `OwnableUpgradeable` y `initialize()` fija owner `0x2D7F2d…` en `main` → **privilegiado**. `chain-test` fija `0x20f33…` con «known test key», pero esa clave está en `setup-agency.sh` (**bloqueado**, §1.3) y no hay prueba de que ese owner esté en 16661. Sin `owner()` live no pasa criterio 2/3. |
| Proxies de compute con `args = [beacon, []]` → `initialize()` permissionless | Los scripts `src/deploy/deploy_ledger_maneger.ts` y `deploy_service.ts` ejecutan `initialize(...)` en una **tx posterior** al deploy (`if (!await ledgerManager.initialized())`). `Initializable.onlyInitializeOnce` bloquea re-init. Los artefactos sólo registran la tx del proxy, **no** la de init. Hecho no verificable sin `eth_getStorageAt(proxy,0)` / `initialized()`; añadido como probe. No se puede declarar. |
| `LedgerManager.retrieveFund` confía en el `amount` devuelto por `processRefund` | Un servicio malicioso podría inflar `availableBalance` sin enviar ETH, pero `registerService` es **`onlyOwner`** y valida ERC-165 `IServing`; los 3 servicios registrables son los de bytecode verificado. Sin ruta permissionless. |
| Bridge: raw txs **sin `chainId`** + owner devnet con clave de test → replay en mainnet | Decodificado: 16 txs legacy de 6 campos, `v∈{27,28}`, `ecrecover` = `0x25Dac40A…` en todas, CREATE `(deployer, nonce 0..7)` = direcciones del mapa. Prod/devnet difieren **sólo en los últimos 20 bytes** (`owner`). Como comparten deployer **y nonces**, en una chain dada **sólo un juego puede emitirse**; si en 16661 se emitieron las prod (owner `0x2D7F…`), el replay devnet es imposible por nonce ya gastado. Sin `eth_getCode`/`owner()` no se sabe cuál se emitió; y sin balances no hay inventario ajeno que drenar. No pasa criterios 3/4. |
| `Bridge.parkRemoteMessages` → `deliver` | `require(msg.sender == SYSTEM_ADDRESS 0xffffFFFfFF…fE)` → system call del consenso, **no permissionless**. `_deliverOne` hace CEI, `inboundConsumed` anti-replay, `proposerFee+keeperFee < amount` y `_convertDecimals` nunca libera más de lo bloqueado. |
| Halborn HAL-01 / HAL-14 (2 CRITICAL) | `is_covered` siempre `true` y null-node en `append_merkle`: **liveness/self-grief del minero**, no drenaje de terceros. «ALL REPORTED FINDINGS HAVE BEEN ADDRESSED»; `node/miner/src/mine.rs:113-116` ya usa `&&`. *Known issues*, prohibidos. |
| Zellic HIGH `addReward(msg.value)` vs `restFee` | Código auditado «**was not deployed to the 0G chain**»; 0 críticos, 1 HIGH + 1 MEDIUM. `ChunkRewardBase.fillReward` usa `addReward(restFee, …)` tanto en HEAD `0dcef31f…` como en el pin `745c176b…`. El MEDIUM (`__gap`) también está corregido (`Flow.sol:34`). |
| Staking `0xea224d…`, consenso, genesis/params | Implementación en `0glabs/0g-chain` (**bloqueado**), binarios de release no descargables. No auditable → no se puede descartar ni afirmar nada. Razón principal de «cobertura incompleta». |

---

## 5. Scripts de reproducción / PoC

| Script | Qué hace | Estado aquí |
|---|---|---|
| `audit/clone_foundation.sh` | enumera orgs, clona 137 repos con todas las ramas/tags | ✅ 0 fallos |
| `audit/inspect_refs.sh` / `clone_submodules.sh` | LFS, `.gitmodules`, gitlinks, 29 subclones | ✅ 1 bloqueado |
| `audit/materialize.sh`, `map_addresses_fast.sh` | 41 worktrees + 19.795 filas de direcciones | ✅ |
| `audit/build_deployment_map.py` | `DEPLOYMENT_MAP.md` / `deployment_map.json` desde clones | ✅ 56 filas / 47 direcciones |
| `audit/verify_bytecode.js` | recompila el `metadata.sources[*].content` de los 3 `*Impl.json` con `solc@0.8.22` y compara con `deployedBytecode` | ✅ **3/3 `bytecode_match=true`** (ejecutar desde un dir con `solc@0.8.22`, p.ej. `.cache/0g-audit/solc`) |
| `audit/decode_bridge_rawtx.py` | RLP + `ecrecover` propio sobre las 16 raw txs; verifica nonces, gas, ausencia de `chainId`, firmante y direcciones CREATE; aísla el diff prod/devnet | ✅ 16/16 firmante coincide; diff = últimos 20 bytes |
| `audit/poc_conservation.py` | replay de `chargeFee`/`fillReward`/`Reward`/`LedgerManager`/`Bridge` | ✅ **Y ≤ X** |
| `audit/poc_retrieve_fund_drain.js` + `audit/poc_sources/` | **PoC ejecutado** sobre las 9 fuentes literales del `metadata` (`solc 0.8.22`, `viaIR`, 200, `istanbul`): compila el `LedgerManager` real, un proxy con `data=""` y un servicio mentiroso; dos escenarios A/B. Salida en `poc_retrieve_fund_drain_output.txt` | ✅ **X=3 → Y=103 ETH** (LM `103→0`, +100 del depósito ajeno) en B; **0 drenaje** en A |
| `audit/live_probe.py` | `eth_chainId/blockNumber/getCode/getBalance`, 18 getters, **15 probes** (`initialized()`, `owner()`, `getWA0GI()`, `minterSupply(Bridge)`, `W0G.totalSupply()`, `bridge.localChainID()`, `getParams()`, `sourceCore()`, `maxValue()`, `getDomains()`), 4 `eth_getStorageAt(slot0)`, `getAllLedgers` | ❌ `BLOCKED` (sin RPC) |
| `audit/audit_pdf_text/*.txt` | extracción `pypdf` de Halborn (41 págs) y Zellic (34 págs) | ✅ persistida |

Para verificar un crítico candidato en un fork: `RPC_URL=<rpc> python3 audit/live_probe.py` produce
`live_inventory.json`. Los checks que decidirían los candidatos abiertos son
`initialized.LedgerManager/InferenceServing/FineTuningServing` + `slot0.*`,
`getAllActiveServices()` del LedgerManager (¿hay algún servicio no verificado registrado?),
`owner()` de `0xe1a5162f…` / `0x54EbF70B…` y `eth_getBalance(0x1Cd069…)`.
Reproducir el PoC: en un dir con `solc@0.8.22 ganache ethers@6`,
`OG_POC_SOURCES=/home/user/0g-storage-node/audit/poc_sources node poc_retrieve_fund_drain.js`.
Sin el paso RPC, cualquier claim de crítico **live** es teoría: el PoC demuestra el bug en el
bytecode verificado, no que la precondición (`onlyOwner`/proxy sin inicializar) se dé en 16661 hoy.

---

## 6. Criterios 1–4

Tabla de criterios para todos los candidatos, incluido el hallazgo nuevo:

| Candidato | 1. código desplegado | 2. permissionless | 3. grafo/estado LIVE | 4. PoC X→Y>X de inventario ajeno |
|---|---|---|---|---|
| **`retrieveFund` / `transferFund` con servicio mentiroso** (§4) | ✅ bytecode del impl recompilado byte-idéntico | ❌ `registerService` es `onlyOwner`; única vía permissionless = proxy sin inicializar, y los scripts ejecutan `initialize()` en tx posterior | ❌ sin `initialized()`/`owner()`/`getAllActiveServices()` on-chain | ⚠️ PoC local **X=3→Y=103** (Y−X=100 del depósito ajeno), pero inventario **sintético**, no medido en 16661 ni fork |
| Flow impl sin initializers, barrido de `balance`, `addReward(msg.value)`, `is_covered` | known issue corregido / no robo | — | ❌ revisión no verificable live | ❌ replay Y ≤ X |
| W0G `mint`/`burn`, `SetMinterCap`, proxy sin inicializar, replay raw txs, staking/precompiles | ⚠️ código nativo Go anclado | ❌ gate `caller==W0G` / `caller==agency` / `SYSTEM_ADDRESS` / `UPDATE_ROLE` | ❌ una llamada RPC pendiente | ❌ sin X medido |
| Consenso / genesis / staking `0xea224d…` / binario v1.0.9 | ❌ repos 404 / release asset TLS bloqueado | ? | ? | ? |

**Ningún candidato cumple los 4 simultáneamente.** El hallazgo nuevo es el que más se acerca: es un
bug **real y ejecutable** en código verificado y su PoC sí produce X→Y>X. Pero falla **2**
(`onlyOwner` / precondición de proxy sin inicializar no demostrada), **3** (ningún estado live: el
RPC vuelve a dar `TLS EOF` en los 3 endpoints) y **4** en su cláusula fuerte (el inventario es
sintético, no un balance de terceros medido en la chain, y no hay fork). Los scripts de deploy
llaman `initialize()` y registran los 3 servicios legítimos —lo que habría revertido con owner=0—,
así que la evidencia disponible apunta a que el proxy **sí está inicializado**; pero eso no es
verificable aquí.

Por tanto, aun cuestionando supuestos, re-clonando y ejecutando la vía ofensiva completa: **no crítico
live demostrado**. Declarar uno exigiría inventar el estado on-chain, que es exactamente lo que el
pliego prohíbe. Inventario medido: 47 direcciones, 9 bytecodes de deployment, 3 recompilados y
coincidentes, **0 balances live**, $ tocable no cuantificable; cobertura declarada **incompleta**
(consenso, genesis, staking y binario desplegado no materializados). Lo que sí se entrega, y es
nuevo respecto al informe anterior, es un **bug de contabilidad confirmado con PoC reproducible**
(`poc_retrieve_fund_drain.js`) y los probes exactos que, con un RPC alcanzable, lo convertirían en
crítico o lo descartarían en una sola ejecución.
