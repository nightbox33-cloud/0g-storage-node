# Auditoría ofensiva — 0G Storage (nodo + contratos de flujo/minería)

Fecha: 2026-11-09 · Repo de sesión: `nightbox33-cloud/0g-storage-node` @ `f75aeae` (main)
Alcance auditado en profundidad: **0G Storage** (`0g-storage-node`, `0g-storage-contracts`,
`0g-storage-client`) y su estado desplegado en **0G Aristotle Mainnet (chain id 16661)**.

---

## 1. Requisito previo: repos de la fundación

### 1.1 Organizaciones enumeradas

| Org | Repos públicos | Estado |
|---|---|---|
| `0gfoundation` | **136** | clonados (ver 1.3) |
| `0glabs` | 0 | **bloqueado**: la org responde vacía para el token (privada o vaciada); es el namespace histórico de `0g-storage-node`, `0g-storage-contracts`, etc. |
| `0g-ai` | 1 (`0G-Play`) | clonado |
| `0g-labs` | 1 (`0gRollPlay`) | clonado |

No hay GitLab/Bitbucket de la fundación referenciados desde los repos; el remoto canónico es
`github.com/0gfoundation/*`.

### 1.2 Método

- Índice completo por API (`/orgs/0gfoundation/repos`, paginado) → `foundation/repo_index.json`.
- Clonado **completo** (historía + todas las ramas, `--no-single-branch`) de todos los repos no
  archivados; submodules y LFS incluidos por `git clone` por defecto.
- Commit exacto por repo registrado (`git rev-parse HEAD`), rama por defecto de `repo_index.json`.
- Los repos que son *forks* de terceros (geth/reth/cometbft/blockscout/wasmer/…) se clonan igual,
  pero se marcan como **no auditados línea a línea** (ver §7).

### 1.3 Commits usados para el código in-scope

| Repo | Commit auditado | Fecha | Nota |
|---|---|---|---|
| `0g-storage-node` | `f75aeae` (main) | commit 2026-10-14 | = HEAD de la sesión (`f75aeaef2cba…`); incluye todos los fixes hasta #440 (ago-2026). Release desplegable: `v1.2.0` (2026-01-13) |
| `0g-storage-contracts` | `0dcef31` (main) | 2026-06-15 | despliegue mainnet: beacon proxies, ver §2.3 |
| `0g-storage-client` | `bb56754` | 2026-08-25 | cliente Go (pago de fees / upload) |
| `0g-storage-kv` | `fce72ee` | 2026-09-02 | KV layer |
| `0gchain-NG` | `b80e685` | — | **stub** (solo README): los binarios de cadena están en releases de `0gchain-NG` (v3.0.10) y `0gchain-Aristotle` (v1.0.9, 2026-11-05) |
| `0g-da-contract` | `4653902` | 2026-06-01 | DA layer (fuera del alcance profundo) |
| `0g-serving-contract` | `3ceeff0` | 2026-05-08 | Compute/Serving (fuera del alcance profundo) |

### 1.4 Repos bloqueados / no cubiertos

- `0glabs/*`: 0 repos visibles → **no se puede declarar cobertura completa** de ese namespace.
- `0gchain-NG` / `0gchain-Aristotle`: fuente **no pública** (solo stubs + binarios en releases).
  No se auditó el cliente de consenso/ejecución.
- **135/135 repos no archivados clonados, 0 fallos** (1 repo archivado excluido y 1 repo vacío sin
  commits). Índice máquina-legible con rama y HEAD por repo: `audit/repos_clonados.tsv`.
- **RPC bloqueado por política de red del sandbox** (`evmrpc.0g.ai` solo admite POST; la salida a
  ese host está denegada). Todo `eth_call`/`eth_getBalance` se hizo por fuentes GET
  (exploradores). Ver §2 y §7.

### 1.5 Mapa dirección / artefacto → repo + ruta

| Componente live | Dirección | Artefacto | Repo + ruta |
|---|---|---|---|
| Flow (FixedPriceFlow, beacon proxy) | `0x62D4144dB0F0a6fBBaeb6296c785C71B3D57C526` | `FixedPriceFlow` (hereda `Flow`) | `0g-storage-contracts/contracts/dataFlow/{Flow,FixedPriceFlow}.sol`, ABI en `0g-storage-node/storage-contracts-abis/Flow.json` |
| PoraMine (beacon proxy) | `0xCd01c5Cd953971CE4C2c9bFb95610236a7F414fe` | `PoraMine` | `0g-storage-contracts/contracts/miner/{Mine,MineLib,RecallRange}.sol` |
| ChunkLinearReward (beacon proxy) | `0x457aC76B58ffcDc118AABD6DbC63ff9072880870` | `ChunkLinearReward` | `0g-storage-contracts/contracts/reward/*.sol` |
| FixedPrice (market) | no legible sin `eth_call` (`Flow.market()`) | `FixedPrice` | `0g-storage-contracts/contracts/market/FixedPrice.sol` |
| Escrow de pagos (hijo de Reward) | `no legible` | `Escrow` | `0g-storage-contracts/contracts/utils/{PullPayment,Escrow}.sol` |
| Nodo de storage (binario) | — | `0g-storage-node` v1.2.0 / main | `0g-storage-node/{node,common}` |
| Params de despliegue turbo | — | `settings=0`, `initDifficulty=1e6`, `targetMineBlocks=750`, `targetSubmissions=100`, `maxShards=256`, `nSubtasks=4`, `subtaskInterval=800`, `blocksPerEpoch=3750`, `firstBlock=2386981`, `lifetimeMonth=12`, `unitPrice=33` | `0g-storage-contracts/src/networks/zerog_mainnet_contract_config_turbo.ts`; `0g-storage-node/run/config-mainnet-turbo.toml` |
| Cliente de cadena | — | releases `v1.0.9` (`0gchain-Aristotle`) / `v3.0.10` (`0gchain-NG`) | fuentes privadas |

---

## 2. Ancla del estado live

- **Chain**: 0G Aristotle Mainnet, chain id **16661**; bloque de referencia **49.698.397**
  (submission #263725, `Nov-8-2026 21:10 UTC`), último bloque visto **49.697.831–49.698.397**.
- **Flow** `0x62D4…C526`: vivo, **268.312** registros de tx, balance nativo 5,202 0G
  (prepagos de usuarios sin gastar).
- **Mine** `0xCd01…4fe` y **Reward** `0x457a…870`: coinciden con `docs.0g.ai` y con
  `run/config-mainnet-turbo.toml`.
- **Parámetros de precio**: `pricePerSector = lifetimeMonth·unitPrice·1e18/2^30/12 ≈ 30,7 gwei/sector`
  (= 0,1288 0G/GB a 12 meses)
  (`deploy_market_enabled_initialization.ts:35`). Verificado empíricamente con submissions live:
  1,62 MB → `2,0456e-4 0G`; 1,35 MB → `1,7309e-4 0G` ⇒ 30,8 gwei/sector reales, 0,129 0G/GB.
- **No se pudo verificar on-chain** (`dataProofEnabled`, `sealDataEnabled`, `poraTarget`,
  `releaseSeconds`, `baseReward`, `serviceFeeRateBps`, balances de Mine/Reward): requieren
  `eth_call` y el RPC está bloqueado. Ver `audit/live_anchor.sh` para reproducirlo desde un host con
  RPC.

### 2.1 Inventario ajeno medido (StorageScan mainnet, 2026-11-08/09)

| Métrica | Valor |
|---|---|
| Ficheros subidos (total) | **263.729** |
| Datos subidos (Σ `data.length`) | **429,15 GB** |
| Longitud del flow tree (última submission, `Start Position`) | **2.349.510.656 sectores = 601,5 GB** |
| ⇒ fracción del flow **sin datos (padding = ceros)** | **28,7 % (≈172 GB)** |
| Mineros activos | **6** (lista histórica ≈160) |
| Recompensas mineras ya pagadas | **≈28,8 0G** (top-1 = 4,014 0G = 13,918 %) |
| Emisión actual | ≈0,02 0G/24 h |
| Fees cobrados acumulados (estimación con `pricePerSector`×sectores cargados) | **≈55–78 0G** |
| Gas por `submit` / `mine` | ≈0,002 0G |

**Quién puede mover qué**

| Inventario | Quién lo mueve | Función |
|---|---|---|
| Fees de usuarios en `ChunkLinearReward` (≈25–50 0G pendientes de liberar/pagar) | **cualquiera** con un `minerId` y un `PoraAnswer` válido | `PoraMine.submit` → `claimMineReward` |
| `totalBaseReward` (donaciones de la fundación) | ídem (base reward por hit) | `claimMineReward` |
| Escrow de pagos ya devengados | `withdrawPayments(payee)` (paga siempre al payee) | `PullPayment` |
| Prepagos en `Flow` (5,2 0G) | cualquiera que envíe un `submit` (el fee sale de `address(this).balance`) | `FixedPriceFlow._beforeSubmit` |
| Datos de usuarios (429 GB) | mineros (pruning por shard) | — |

---

## 3. HALLAZGO CRÍTICO — minería de sectores de padding: se cobra el pool del chunk de 8 GB sin almacenar

**¿Vulnerable ahora? Sí.** Permissionless, sobre el código desplegado que sí corre live.

### 3.1 Bug

Dos hechos que se combinan:

1. El flow tree de `Flow` se construye con `FlowTreeLib.pad()` + `insertNode()`: entre dos
   submissions, las posiciones de alineación **se saltan** (`tree.currentLength = startIndex + …`),
   es decir, quedan como hojas vacías. Una hoja vacía de 4 KB tiene hash **`zeros(4)`**, que es una
   constante del contrato (`contracts/dataFlow/FlowTreeLib.sol:zeros`), y una hoja de 256 B vacía es
   `zeros(0) = d397b3b0…8e0b5 = keccak256(256 bytes cero)`.
   `MineLib.recoverMerkleRoot()` acepta cualquier `merkleProof` cuya plegadura dé `context.flowRoot`
   y **no exige que el dato probado exista**: un seal de 4 KB de ceros plegado con los hermanos
   públicos (ladder de `zeros` + nodos reales) reconstruye el root.
   `Mine.basicCheck()` sólo valida contexto, epoch-range y `pora()` liga la posición al nonce; nada
   mira el contenido.
2. El pago es **a nivel de pricing chunk de 8 GB**, no del seal probado:
   `IReward(reward).claimMineReward(answer.recallPosition / SECTORS_PER_PRICE, …)` →
   `ChunkRewardBase.claimMineReward` paga `claimableReward / 2` de **todo el chunk**
   (`contracts/reward/ChunkRewardBase.sol:claimMineReward`, `Reward.sol:claimReward`).

Como el padding está *intercalado* con datos reales dentro de los mismos chunks de 8 GB, un atacante
que prueba un seal de ceros cobra la mitad del pool de fees pagado, en su mayoría, por datos reales
de terceros. No almacena nada y su coste marginal es sólo el gas del `submit`.

Agravante: `_baseReward()` paga además `baseReward()` por cada hit de un chunk finalizado dentro de
su ventana de 12 meses, con el mismo free-rider.

### 3.2 Evidencia on-chain del padding, submission a submission

Las tres últimas submissions de StorageScan (263723/263724/263725) dan el patrón exacto:

| submission | tamaño dato | segmentos (256 KiB) | `startIndex` | capacidad insertada (sectores) | padding hasta la siguiente |
|---|---|---|---|---|---|
| 263723 | 1,23 MB | 5 | 2.349.494.272 | 5.120 (1,25 MiB) | 3.072 sectores (37,5 %) |
| 263724 | 1,35 MB | 6 | 2.349.502.464 | 6.144 (1,5 MiB) | 2.048 sectores (25 %) |
| 263725 | 1,62 MB | 7 | 2.349.510.656 | 7.168 (1,75 MiB) | — |

Los `startIndex` avanzan **exactamente 8.192 sectores (2 MiB)** por submission, mientras el dato ocupa
5.120/6.144/7.168 sectores: el árbol rellena con hojas cero hasta el límite de 2 MiB y ese relleno
(1.024–3.072 sectores por fichero, 12,5–37,5 %) entra en el `flowRoot`, en `epochRange` y en el pool de
rewards del chunk. Para ficheros pequeños el padding relativo es aún mayor; el agregado medido es
172 GB de 601,5 GB (28,7 %).

### 3.3 Por qué es permissionless

- `PoraMine.requestMinerId(beneficiary, seed)` es público (`contracts/miner/Mine.sol`) — 1 tx.
  El `minerId` incluye `msg.sender`, así que no hay squatting posible sobre mineros honestos.
- `PoraMine.submit(answer)` es público, sin stake, sin whitelist.
- No hace falta descargar ni almacenar datos: el atacante sigue la estructura pública del árbol
  (eventos `Submit` → `nodes[].root/height`, más `getFlowRootByTxSeq`) para calcular hermanos, y
  fabrica `sealedData = seal(ceros, minerId, sealedContextDigest, recallPosition)`.
- `recallPosition` se "grindea" cambiando `nonce` (exactamente el mismo trabajo de PoRA que un minero
  honesto, pero **sin I/O de disco**: descarta al instante los loads que no son padding).

### 3.4 Call graph live

```
EOA atacante → PoraMine.requestMinerId        (1 tx, permissionless)
             → PoraMine.submit(PoraAnswer)    ── por cada hit
                  ├─ IFlow.makeContextWithResult()
                  ├─ getEpochRange(sealedContextDigest)   // posición dentro de un epoch pasado
                  ├─ recoverMerkleRoot(ceros) == context.flowRoot   // PASA (ver PoC)
                  ├─ pora() → calidad ≤ poraTarget                  // grinding normal
                  └─ IReward.claimMineReward(pos / SECTORS_PER_PRICE, beneficiary, minerId)  // SECTORS_PER_PRICE = 8 GiB/256 B = 33.554.432
                        └─ _asyncTransfer(beneficiary, claimable/2 [+ baseReward])
```
Todo está cableado y en uso: 28,8 0G ya distribuidos por esta misma ruta, 200 submissions/epoch
(`2 * targetSubmissions`), `poraTarget` ajustado on-chain.

### 3.5 PoC

`audit/poc_zero_leaf.py` (ejecutable, sin dependencias del repo) reproduce
`MineLib.recoverMerkleRoot` y demuestra:

```
zeros(0) contrato = d397b3b043d87fcd6fad1291ff0bfd16401c274896d8c63a923727f077b8e0b5
keccak(256 ceros) = d397b3b043d87fcd6fad1291ff0bfd16401c274896d8c63a923727f077b8e0b5
nodo vacío de 4KB  = 09c7082879180d28c789c05fafe7030871c76cedbe82c948b165d6a1d66ac15b (== zeros(4))
[OK] recoverMerkleRoot(unsealed=ceros, proof=zeros+siblings) == flowRoot
[OK] PoRA puede hacerse sobre padding: no hace falta almacenar nada
control (posición con datos reales, misma estrategia): rechaza (correcto)
```

`zeros(4)` **es literalmente** la constante `height == 4` de `FlowTreeLib.zeros()`: el nodo vacío del
árbol es una constante del propio contrato.

Evidencia live de que el padding existe y es grande (submissions consecutivas reales):

| seq | Start Position | fin de datos | gap al siguiente |
|---|---|---|---|
| 263723 | 2.349.494.272 | 2.349.499.312 | 3.152 sectores (807 KB) — cota superior del padding de alineación |
| 263724 | 2.349.502.464 | 2.349.507.994 | 2.662 sectores (681 KB) — idem |
| 263725 | 2.349.510.656 | 2.349.517.298 | — |

Agregado: **601,5 GB de árbol vs 429,15 GB de datos ⇒ 172 GB (28,7 %) de posiciones de ceros
cobrables sin almacenar**.

### 3.6 PnL del atacante

- Coste: 1 tx de `requestMinerId` + ~0,002 0G por `submit` (gas 489k–644k, ~80 % del bloque).
- Ingreso por hit: `claimable/2` del chunk de 8 GB. Un chunk lleno acumula
  `33.554.432 × 30,7 gwei ≈ 1,03 0G` a 12 meses; la primera visita a un chunk maduro paga ~0,51 0G
  (>250× el gas de 0,002 0G).
- Stock tocable hoy: **≈25–50 0G** (fees cobradas 55–78 0G − 28,8 0G ya distribuidas), barribles con
  ~10 hits por chunk sobre los ~70 chunks que forman el flow, muy por debajo del presupuesto de
  200 claims/epoch (≈25 min).
- Inflow marginal actual ≈0,02 0G/día (toda la emisión de la red).
- **Magnitud honesta**: decenas de 0G. Es el TVL completo de 0G Storage mainnet; en USD es pequeño
  (el precio de 0G no se pudo consultar desde el sandbox). No es dust-de-gas: cada claim renta.

### 3.7 Qué lo mataría (y no ocurre)

- Que `recoverMerkleRoot` exigiera contenido no-cero o que el payout fuera por posición y no por
  chunk: **no ocurre**.
- Que el padding no existiera en el flow live: **existe, 28,7 % medido**.
- Que `submit` fuera privilegiado: **es público**.
- Que `dataProofEnabled == false` (sin prueba de datos el ataque sería aún más simple): el constructor
  derivado del artefacto de red usado para mainnet-turbo,
  `src/networks/zerog_mainnet_contract_config_turbo.ts:6` → `settings: 0` ⇒
  `sealDataEnabled = (0 & 0x1 == 0) = true` y `dataProofEnabled = (0 & 0x2 == 0) = true`
  (`contracts/miner/Mine.sol:94-97`). El ataque de padding es por tanto el **camino real** (si
  `0x2` estuviera activo, cualquier posición —no sólo padding— sería reclamable). No verificable por
  `eth_call` desde el sandbox (§7.3): `settings` es inmutable en el constructor, así que el
  `live_anchor.sh` no lo cubre; se confirmaría con el input de creación del proxy/impl en el explorer.

Mitigación sugerida: rechazar proofs cuyo bloque de 4 KB sea íntegramente ceros (o exigir
`keccak(unsealed) != zeros(4)`), y/o pagar por posición dentro del chunk en vez de `claimable/2`
del chunk completo, y/o excluir del rango minable las posiciones de padding.

---

## 4. Candidatos evaluados y descartados (con el hecho que los mata)

| Candidato | Hecho que lo mata |
|---|---|
| **Forjar PoRA sin dato alguno** (no-padding) | `recoverMerkleRoot` debe dar `context.flowRoot`; las hojas de datos reales no se pueden sintetizar (PoC: control negativo). |
| **Reescribir historia del flow tree** para apropiarse de chunks ya pagados | `insertNode` usa `nextAlign(currentLength,height)`, monótono: nunca escribe antes de `currentLength`. |
| **Doble claim del mismo answer** | `_submittedPora[poraOutput]` + tope global `2*targetSubmissions` por epoch. |
| **Overflow/underflow en `Reward`** | `addReward` exige `amount ≤ uint128.max`; `linearDecayReward` acota a `totalReward - released`; `actualBaseReward` acotado por `totalBaseReward`. |
| **Insolvencia del escrow** | `_asyncTransfer` deposita `{value: amount}`; si no hay saldo, revierte el claim (no imprime deuda). |
| **Claim de chunk no finalizado** | `startTime == 0` ⇒ `_linearDecayReward` y `_baseReward` devuelven 0 (fix #50). |
| **Squatting de `minerId` de un nodo honesto** | `minerId = keccak(blockHash(n-1), msg.sender, seed)`: ajeno a `msg.sender` del atacante ⇒ imposible. |
| **Robo de rewards del nodo por un peer** | El nodo sólo firma `requestMinerId` (beneficiary = su propia address) y `submit(answer)` calculado localmente; no hay camino de calldata remoto. RPC admin (`findFile/shutdown/startSync*`) no firma txs. |
| **Drenar el prepago de `Flow`** | Real (`_beforeSubmit` usa `address(this).balance`, no `msg.value`), permissionless, **pero el stock es 5,202 0G medido** y sólo compra almacenamiento ⇒ dust, no crítico. |
| **DoS de nodos (AnnounceFile O(N²), OOM)** | Real y permissionless (#437 abierto, cap #431 en main), pero **no hay robo** ⇒ excluido por criterio (además `v1.2.0` es anterior al cap). |
| **Carrera de inicialización de la implementación de `Flow`** | `#69` sólo afecta al storage del *implementation*; el proxy ya está inicializado. Sin valor. |
| **`setParams` sin control de acceso** | Es one-shot (`if ($.x == 0)`) y ya está inicializado en el proxy. |
| **`subtaskDigest` predecible si `blockhash` caduca (>256 bloques)** | `Blockhash` EIP-2935 entró en #54 (jun-2025) y `Mine` pasó a usarlo en #66 (feb-2026); si el proxy desplegado no se actualizó, `blockhash(subtaskMineStart)` da 0 más allá de 256 bloques y el digest se conoce antes de la ventana: sólo adelanta el pre-cómputo, no permite proof falso ni doble claim. |
| **Reorg / revert de logs** | `confirmation_block_count = 1` + finalidad BFT; sin camino económico. |

---

## 5. Segunda pasada (sesión 2): Compute, Restaking/Bridge, DA y settlement servers

Los cuatro frentes restantes del stack in-scope se leyeron desde los clones (no desde memoria ni
explorer). En ninguno hay una entrada **permissionless** que mueva ETH de terceros hacia el atacante.
Los hechos que los matan, uno por uno:

### 5.1 Compute / Serving — `0g-serving-contract` @ `3ceeff03ca`

Despliegue mainnet (chain 16661) tal como está versionado en `deployments/zgMainnet/`:

| Contrato | Proxy | Beacon | Impl |
|---|---|---|---|
| LedgerManager | `0x2dE54c845Cd948B72D2e32e39586fe89607074E3` | `0xFe5Ed683F64aD623fAaBb7fa439745A866aD65dF` | `0xee876A55540eeA57E684Fc3e6d8c4702810E704f` |
| InferenceServing | `0x47340d900bdFec2BD393c626E12ea0656F938d84` | `0xE7e9e873371Cb1b42Ae9E8cB3aA646324932243A` | `0x1c0A264f5ae6cfC37E8695442fB139efD884Ca48` |
| FineTuningServing | `0x4e3474095518883744ddf135b7E0A23301c7F9c0` | `0x449C244C7d18dBCdd3612e6B14628EEdB236fb80` | `0x795d7E2c812AB92E815e5375a0Ca707d56A4838C` |

| Candidato | Hecho del código que lo mata |
|---|---|
| Drenar el `LedgerManager` desde un contrato/service falso | `receive()` sólo acepta `_isServiceContract(msg.sender)`, y `spendFund`/`transferFund`/`retrieveFund` son `onlyServing` con `registeredServices[msg.sender].serviceAddress != 0`. `registerService` es **onlyOwner**, exige ERC165 (`INFERENCE_SERVING_INTERFACE`) y hay tope `MAX_SERVICES = 500`. Un EOA o un contrato arbitrario no entran al ledger. |
| `spendFund` sobre saldo de otro usuario | `spendFund(user, amount)` sólo puede consumir `totalBalance - availableBalance` (los fondos que el usuario ya transfirió a *su* servicio) y el serving sólo lo llama con `accountMap[user][provider].balance` después de `settleFeesWithTEE`/`settleFees`, que exige `settlement.provider == msg.sender`, servicio registrado, nonce creciente y firma EIP-712 (`_verifySignature`) del TEE signer del servicio. |
| Auto-acknowledge del TEE signer en el depósito | `addAccount` marca `acknowledged = true` del signer del servicio al depositar. Es el **modelo de confianza elegido por el usuario** (elige proveedor), no una ruta a fondos ajenos: `acknowledgeTEESigner` es sólo proveedor y `acknowledgeTEESignerByOwner`/`revokeTEESignerAcknowledgement` son onlyOwner. |
| Doble refund / acreditar dos veces | `requestRefundAll`/`processRefund`/`depositFund`/`deleteAccount` son `onlyLedger`; `retrieveFund` sólo acredita `availableBalance`; `promptWithdraw` exige `remainingBalance == 0 || >= MIN_WITHDRAW` y `cancelRetrievingAmount` se acota en el ledger a `min(amount, retrievingAmount)`. Invariante `totalBalance = availableBalance + Σ account.balance` se mantiene en los seis caminos. |
| FineTuningServing (mismas rutas, 848 líneas) | Idénticas guardas: mutaciones de cuenta `onlyLedger`, `settleFees` resuelve `accountMap[verifierInput.user][msg.sender]` + `serviceMap[msg.sender]`, stake (100 0G) se devuelve sólo a `msg.sender` en `removeService`. |

Conclusión: **no crítico**. El valor del ledger son depósitos de usuarios a proveedores que ellos
mismos eligen; no existe llamada permissionless que toque ese ETH.

### 5.2 Restaking / Bridge / Ascend — `0g-restaking-contracts` @ `f7cba8a4b7`

| Candidato | Hecho del código que lo mata |
|---|---|
| Inyectar mensajes al bridge sin ser el CL | `Bridge.parkRemoteMessages` revierte salvo `msg.sender == SYSTEM_ADDRESS` (`0xffff…fffe`); sólo la system call del consenso escribe `pendingMessages`. |
| `deliver`/`deliverBatch` permissionless como agujero | Sí son permissionless, pero sólo consumen `pendingMessages[srcCID][nonce]` ya parkeados: el contenido (amount, token, recipient, fee) lo fija el CL. `inboundConsumed` + nonce monótono por lane dan el replay-shield; las fees están acotadas por `MAX_FEE_BPS = 10000` y `_convertDecimals` trunca (no infla). `deliverOneInternal` exige `msg.sender == address(this)`. |
| Acuñar `BridgeERC20` / añadir tokens | `mint` sólo el bridge (MINTER_ROLE); `BridgeAgency.deployAndAddBridgeToken` es `ADMIN_ROLE` (proxy `0x3f638aac…`). |
| `AscendRouter.distribute()` | `onlyRole(DISTRIBUTOR_ROLE)`; `updateParams` sólo `DEFAULT_ADMIN_ROLE` y los tres porcentajes deben sumar `1e18`. Sin entrada pública. |
| Manipular el precio del vault aOG (`OracleUpdater.setValue`) | `onlyRole(UPDATER_ROLE)`, **monótono creciente** (`value < current` revierte) y acotado por `maxValue() = (W0G del SourceCore + W0G del OFT adapter) / supply` ⇒ ni con la clave del updater se puede inflar el precio por encima del NAV on-chain. |
| `Rewarder` / `ZeroGravity*` | Roles EigenLayer (operator/middleware/admin) para todo lo que mueve shares; no hay claim permissionless con payout a `msg.sender`. |

### 5.3 DA — `0g-da-contract` @ `4653902b13`

- `submitOriginalData` paga blob fee (`msg.value >= n * blobPrice`) y sólo emite `DataUpload`.
- `submitVerifiedCommitRoots` exige agregación BLS del quórum (`getAggPkG1` + `validateSignature`) y
  `SLICE_NUMERATOR * total <= hit * SLICE_DENOMINATOR`.
- `submitSamplingResponse` es permissionless, pero: exige `commitmentExists(dataRoot, epoch, quorum)`,
  `rep.sampleSeed == currentSampleSeed`, `quality <= podasTarget`, `rep.verify()` y
  `epoch + epochWindowSize >= currentEpoch > epoch`; y el pago va a
  `DA_SIGNERS.getQuorumRow(epoch, quorumId, lineIndex)` — **el firmante del quórum, nunca
  `msg.sender`**. Enviar muestras válidas no reporta ni un wei al atacante.
- `_claimBaseReward` se financia sólo con `donate()` (payable, suma a `totalBaseReward`); no es drenable
  desde fuera.

### 5.4 Settlement servers — `0g-ito-settlement-server` @ `4a672f5b3e`, `0g-zk-settlement-server` @ `1b7ccd5001`

Son el diseño **previo** (zkSettlement: trazas off-chain + proof zk). El Compute live v1.0 usa el
`LedgerManager`/`InferenceServing`/`FineTuningServing` de §5.1 (`VERSION.json` fija las imágenes del
broker `0g-serving-broker`), y ninguno de los contratos de `contract/` de estos dos repos aparece en
el mapa de direcciones mainnet del despliegue. Quedan **fuera del estado desplegado**: se auditan como
código, no como superficie live.

---

## 6. Conclusión

- **1 crítico live** (§3): extracción permissionless del reward pool de 0G Storage minando sectores
  de padding — sin almacenar, cobrando el pool completo del chunk de 8 GB pagado por terceros.
  Tocable hoy: **≈25–50 0G** (todo el TVL de Storage mainnet), con gas ≈0,002 0G/claim.
- No se encontró ningún otro camino que mueva fondos de terceros en el nodo: el nodo **no custodia
  tokens de usuarios** (`zgs` RPC, sync, router y pruner no firman transferencias ni retiran del
  escrow), y toda la validación económica de la minería vive en los contratos.
- **Segunda pasada (§5): 0 críticos nuevos.** Compute/Serving, Restaking/Bridge/Ascend, DA y los
  settlement servers quedan descartados con el hecho concreto en el código: toda mutación de ETH está
  detrás de `onlyServing`/`onlyLedger` (con registro onlyOwner), de `SYSTEM_ADDRESS` (CL), de roles
  (`ADMIN_ROLE`/`DISTRIBUTOR_ROLE`/`UPDATER_ROLE` con bound de NAV) o paga a un tercero
  (`DA_SIGNERS.getQuorumRow`), nunca a `msg.sender`.

## 7. Límites de esta auditoría (no declaro cobertura completa)

1. `0glabs/*` inaccesible (0 repos visibles) — puede contener el código histórico desplegado.
2. Fuentes del cliente de cadena (`0gchain-Aristotle`, `0gchain-NG`) **no públicas**: sólo binarios
   en releases; no se auditó consenso/ejecución/precompiles.
3. **RPC bloqueado por el sandbox** (`evmrpc.0g.ai`: “only POST is supported”; salida denegada).
   No se pudieron leer `dataProofEnabled`, `sealDataEnabled`, `poraTarget`, `releaseSeconds`,
   `baseReward`, `serviceFeeRateBps`, `market()`, ni balances de `Mine`/`Reward`/escrow, ni
   reconstruir el flow tree desde eventos. `audit/live_anchor.sh` deja los comandos listos para
   ejecutarlos desde un host con RPC y cerrar esa verificación.
4. 135/135 repos no archivados clonados (0 fallos); 1 repo de la org está vacío (sin commits) y 1
   archivado. No se auditó en profundidad el código de forks de terceros.
5. DA (`0g-da-*`), Compute/Serving (`0g-serving-*`), bridge/restaking (`0g-restaking-contracts`) y
   los settlement servers: **leídos en la segunda pasada** (§5) pero **sin auditoría línea a línea de
   las 848 líneas de `FineTuningServing` ni del circuito zk**; los forks de consenso y los precompiles
   siguen sin auditar (fuentes no públicas, §7.2).
6. Los balances de los contratos de Compute (`LedgerManager`, `InferenceServing`,
   `FineTuningServing`) **no se pudieron medir** (explorer SPA sin datos por GET, RPC bloqueado): el
   descarte de §5.1 es por control de acceso, no por TVL.
