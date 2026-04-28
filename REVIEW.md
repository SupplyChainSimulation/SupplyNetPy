# Critical Code Review — `src/SupplyNetPy/Components/`

Scope: `core.py` (2,617 LOC), `utilities.py` (438 LOC), `logger.py` (189 LOC).
Perspective: correctness, API ergonomics, maintainability, and readiness to scale beyond the current example suite. Line numbers reference the files as of this review.

---

## 1. Executive summary

SupplyNetPy is a readable, single-responsibility library that does a reasonable job of layering supply-chain semantics on top of SimPy. The core class set is the right one (`Node`, `Link`, `Inventory`, replenishment and selection policies, `Statistics`, `Demand`, `Supplier`, `Manufacturer`) and the behavior loops are simple enough to follow end-to-end. However, it is still pre-alpha in several important ways:

- A handful of **real bugs** in `Inventory` (expired-item removal, kwarg plumbing, `self.logger` used before it exists).
- **Tight coupling and leaky abstractions** between `Node`, `Inventory`, `Statistics`, and the replenishment policies — each reaches deep into the others (`self.node.inventory.inventory.level`, `self.node.stats.backorder[1]`, `self.node.selection_policy.select(...)`). Custom policies need to know all of it.
- **A god-file**: `core.py` holds 17 classes and roughly 85% of the library. This makes navigation, diffing, and unit testing harder than it needs to be.
- **Numeric state duplication** between `Inventory.level`, `Inventory.inventory.level` (the SimPy container), and `Inventory.on_hand`, with no single source of truth.
- **Fragile reflection** in `Statistics.update_stats` (sums any attribute whose name contains `"cost"`).
- **Heavy, duplicated docstrings** that state the same fields three times (class, `__init__` params, `__init__` attributes). They dominate the file and rot in lockstep.
- **No randomness control** — `random.random()` is called directly with no rng injection or seeding.

None of these are blockers for the current demo-sized examples, but they will hurt as soon as users extend the library or run larger studies.

---

## 2. Strengths worth preserving

- **Clean separation of concerns at the class level.** Replenishment policies, selection policies, inventory, and nodes are distinct classes with focused responsibilities.
- **Both dict and object construction paths** are supported by `create_sc_net`, which is nice for notebook users.
- **Good validation helpers** (`validate_positive`, `validate_non_negative`, `validate_number`) used consistently at constructor boundaries.
- **Node- and link-level disruption** is modeled uniformly, with the same `status` state machine.
- **Perishable FIFO** via `perish_queue` is a clever, lightweight addition.
- **Stats aggregation** in `simulate_sc_net` produces a rich, user-facing dict that notebooks can consume directly.
- **Google-style docstrings** plug directly into `mkdocstrings`, so the API reference on the docs site is essentially free.

---

## 3. Correctness issues (fix first)

### 3.1 `Inventory.remove_expired` never yields the `get` event ✅ Resolved
`core.py:1684–1698`

**Original issue:** `self.get(qty)` returned a SimPy `get` event that was dropped instead of yielded, so the container level was not reliably decremented, `level != on_hand` could drift, and `update_carry_cost` kept charging holding cost on phantom stock.

**Fix applied:** `remove_expired` now captures and yields the get event:
```python
if qty > 0:
    get_event, _ = self.get(qty)
    yield get_event
```
`self.get()` also pops the expired head from `perish_queue` and decrements `on_hand`, so container level, `on_hand`, and `perish_queue` stay consistent.

**Note on the secondary concern (`inventory_drop` signal):** the original review flagged that `self.get()` fires `inventory_drop.succeed()` on expiry. On re-reading the policies (`SSReplenishment.run` at `core.py:629–639`, `RQReplenishment.run` at `core.py:735`), they re-check `on_hand - backorder[1] <= s` when the event fires. Since expiry is a *real* drop in physical inventory, waking the policy to re-evaluate is semantically correct — a reorder only happens if the post-expiry position actually crossed the threshold. This concern was overstated and does not need a separate fix.

### 3.2 `Demand.__init__` uses `self.logger` before `super().__init__` runs ✅ Resolved
`core.py:2450–2467`

**Original issue:** the `order_min_split_ratio > 1` check used `self.logger` before `super().__init__` had created it, so `order_min_split_ratio=1.5` raised `AttributeError` instead of the intended `ValueError`. The message was also self-contradictory ("will be set to 1" followed by a raise).

**Fix applied:** `super().__init__` is now called first (line 2450), so `self.logger` exists by the time the validation block runs. The error text was also cleaned up to just "Order Min Split Ratio must be in the range [0, 1]." — behavior and message are now consistent (raise).

**Minor follow-up (out of scope for §3.2):** `validate_positive` at line 2464 rejects `0`, so the actually accepted range is `(0, 1]`, not `[0, 1]` as the error message claims. Either swap to `validate_non_negative` or tighten the message to `(0, 1]`.

### 3.3 Extra kwargs leak into `GlobalLogger` / swallowed by `Inventory` ✅ Resolved
`core.py:9–13, 1265–1272, 1793, 1803, 1964, 2172`

**Original issue:** `Node.__init__` forwarded its entire `**kwargs` to `GlobalLogger`, which only accepts `log_to_file`, `log_file`, `log_to_screen`. Any unrelated kwarg raised `TypeError`. A latent second bug: `logger_name` was read from `kwargs` but not popped, so an explicit caller-supplied `logger_name=` would be delivered twice. Separately, `Inventory.__init__` declared `**kwargs` and silently ignored unknown keys, so typos like `shelf_live=5` at the subclass level disappeared without any error.

**Fix applied:**

1. Module-level whitelist `_LOGGER_KWARGS = {"log_to_file", "log_file", "log_to_screen"}` defined once near the top of `core.py`.
2. In `Node.__init__`: pop `logger_name` from `kwargs`, then forward only whitelisted keys to `GlobalLogger`.
3. `Inventory.__init__` signature tightened — `**kwargs` removed. The "will be ignored" line was dropped from its docstring.
4. Each of the four Inventory call sites (`Supplier` x2, `InventoryNode`, `Manufacturer`) now builds `inventory_kwargs = {k: v for k, v in kwargs.items() if k not in _LOGGER_KWARGS}` and forwards only the non-logger kwargs. Because Inventory has a strict signature, any stray key that isn't a known Inventory parameter raises `TypeError` at the Inventory boundary — typos are no longer swallowed.

**Verified** via `examples/py/intro_simple.py`:
- Canonical simulation still matches the expected output (`profit: -4435.0`, `total_cost: 25435.0`).
- `shelf_live=5` (typo) → `TypeError: Inventory.__init__() got an unexpected keyword argument 'shelf_live'`.
- `log_to_file=False` → accepted silently (handled by `Node`, filtered out before `Inventory`).
- `record_inv_levels=True` → forwarded to `Inventory` correctly; `instantaneous_levels` is initialised.

Test suite: 93/94 passing (the one remaining failure, `TestLink::test_invalid_lead_time`, is pre-existing and unrelated).

### 3.4 `Statistics.update_stats` sums every attribute containing `"cost"` ✅ Resolved
`core.py:214, 249–251, 286, 1812, 2200`

**Original issue:** `update_stats` computed `node_cost` by iterating `vars(self)` and summing any attribute whose name contained `"cost"`. This substring match would silently pick up future attrs like `max_cost_per_unit`, `cost_multiplier`, or any cached reference whose name happened to contain the word, and it relied on an implicit convention that subclass cost attrs must be added via `setattr(self.stats, ...)`.

**Fix applied:**

1. `Statistics.__init__` now initialises an explicit `self._cost_components = ["inventory_carry_cost", "inventory_spend_cost", "transportation_cost"]`.
2. `update_stats` computes `self.node_cost = sum(getattr(self, name) for name in self._cost_components)` — no reflection.
3. `Supplier.__init__` and `Manufacturer.__init__` append their subclass-specific cost attrs (`total_material_cost`, `total_manufacturing_cost`) to `self.stats._cost_components` alongside the existing `_stats_keys.extend(...)` call.
4. `Statistics.reset` was tightened: the list-blanking pass now skips any attribute whose name starts with `_` (covers `_info_keys`, `_stats_keys`, `_cost_components`), instead of the previous ad-hoc `"_keys" in key` guard — so `_cost_components` is not clobbered on reset.

**Verified** by running a supplier → factory → distributor scenario against the edited source (via `examples/py/intro_simple.py` with `sys.path` pointing at the local `src/`):
- `S1` (Supplier): `_cost_components = [carry, spend, transport, total_material_cost]`, sum = `node_cost = 1000.0` ✓
- `F1` (Manufacturer): `_cost_components = [carry, spend, transport, total_manufacturing_cost]`, sum = `node_cost = 827.2` ✓
- `D1` (Distributor): `_cost_components = [carry, spend, transport]`, sum = `node_cost = 23903.2` ✓
- Canonical `intro_simple.py` output is unchanged (`node_cost: 25435.0`, `profit: -4435.0`).

Adding a new cost component now requires an explicit `self.stats._cost_components.append("new_cost_attr")` — no more implicit substring matching.

### 3.5 Partial-fulfillment: `demand_node.demand_fulfilled` inflated on partial shipments ✅ Resolved
`core.py:2562–2570`

**Clarification on `backorder` (user, 2026-04-23):** `backorder=[count, qty]` is intentional — a backorder represents *one* outstanding customer order, so the count stays at 1 through every partial shipment while the quantity ticks down by `available`. Only when the remainder is finally delivered does the count drop to 0 via `[-1, -remaining]`. The original review was wrong to flag `backorder=[0, -available]` as an "arbitrary convention" — it is the deliberate convention and the rest of the accounting mirrors it. That sub-concern is retracted.

**Real issue (still a bug):** `_process_delivery` increments *both* `self.stats.fulfillment_received` and `self.demand_node.stats.demand_fulfilled` by `[1, qty]` on every call. The partial branch in `wait_for_order` compensated only on the Demand side (`fulfillment_received=[-1, 0]`), not on the demand_node side. Result: one customer order served via N shipments inflated `demand_node.stats.demand_fulfilled[0]` to N instead of 1, even though the Demand-side `fulfillment_received[0]` correctly stayed at 1.

Verified empirically: a single customer order for 60 units served via one 20-unit partial + one 40-unit completion produced `demand_node.demand_fulfilled = [2, 60]` before the fix, while `demand_placed = [1, 60]`, `fulfillment_received = [1, 60]`, `demand_received = [1, 60]`.

**Fix applied:** the partial branch now adds a symmetric `demand_fulfilled=[-1, 0]` compensation alongside the existing `backorder=[0, -available]`:

```python
self.demand_node.stats.update_stats(backorder=[0, -available], demand_fulfilled=[-1, 0])
self.stats.update_stats(fulfillment_received=[-1, 0])
```

Re-run of the same scenario post-fix: `demand_node.demand_fulfilled = [1, 60]` — matches `demand_placed` and every other fulfillment counter. Canonical `intro_simple.py` output unchanged (partial-fulfillment path is not exercised at `order_min_split_ratio=1.0`, the default).

### 3.6 `Inventory.put` ignores perishables when early-returning ✅ Resolved
`core.py:1623–1624`
```python
if self.inventory.level == float('inf') or amount <=0 or self.inventory.level == self.capacity:
    return
```
When a perishable inventory is at capacity, `put` returns without recording the attempted addition. That's fine for the container, but a caller in `InventoryNode.process_order` increments `on_hand` before the `yield event`. If that path ends up here, the `on_hand` bookkeeping and the `perish_queue` get out of sync. Similarly the amount-clamp path (`amount = self.capacity - self.inventory.level`) inserts the clamped value into `perish_queue` but the caller already thinks the full amount is in transit.

**Fix:** return the accepted amount from `put`, and make callers reconcile `on_hand` against it.

**Resolution (2026-04-23):** `Inventory.put` now returns the accepted amount — `0` for infinite/full/non-positive early returns, the clamped value `capacity - level` when the request exceeds capacity, and the full `amount` otherwise. Two callers that pre-increment `on_hand` before the `yield`/`put` sequence were updated to reconcile:

- `InventoryNode.process_order` — after the put branch, compute `shortfall = reorder_quantity - accepted` and do `self.inventory.on_hand -= shortfall` when positive. The man-date loop sums the accepted amount across `put` calls so a partial clamp on one batch is still caught.
- `Manufacturer.produce_product` — same pattern for `max_producible_units` (it pre-increments `on_hand` at the produce-unit branch).

`Supplier.behavior` already clamps `mined_quantity` against free capacity before calling `put`, so `put` never has to clamp in that path; no reconciliation is needed there (and `Supplier` does not track `on_hand` for its own inventory anyway).

Verified via `examples/py/intro_simple.py` with a temporary test block that manually exercised the clamp path (capacity 100, level 50, put 80 → accepted 50, level 100, reconciled `on_hand` 100). Canonical `intro_simple.py` output (`profit: -4435.0`) unchanged.

### 3.7 `Inventory.level` is a stale shadow of `Inventory.inventory.level` ✅ Resolved
Throughout `core.py` you can find both `self.inventory.level` (the instance attribute on the `Inventory` wrapper) and `self.inventory.inventory.level` (the SimPy container). They are updated in different places:

- `put` updates `self.level` at line 1645.
- `get` updates `self.level` at line 1677.
- `remove_expired` doesn't update `self.level`, because — see 3.1 — it never actually gets.
- `update_stats` reads `self.node.inventory.inventory.level` for the current level (line 276), not `self.level`.

The result is a duplicated piece of state with no single owner. Make `level` a `@property` that delegates to `self.inventory.level`, and delete every assignment to `self.level`.

**Resolution (2026-04-23):** `Inventory.level` is now a read-only `@property` that returns `self.inventory.level`, so there is a single source of truth (the SimPy container). The three stale assignments were removed:

- `__init__` at line 1583 (`self.level = initial_level`) — redundant; `simpy.Container(..., init=self.init_level)` at line 1589 already seeds the container at `initial_level`.
- `put` at line 1657 (`self.level = self.inventory.level`) — dead write, removed.
- `get` at line 1690 (`self.level = self.inventory.level`) — dead write, removed.

Call sites that read `self.node.inventory.level` (e.g. `PeriodicReplenishment.run` at lines 826–827, `record_inventory_levels`, `remove_expired`, `get_statistics` via `_stats_keys = ["level", ...]`) now go through the property and see the live container value. Verified via `examples/py/intro_simple.py` — canonical output unchanged (`profit: -4435.0`, `inventory_level: 100`).

**Follow-up (2026-04-23): same treatment for `Inventory.capacity`.** The codebase had 30 call sites using the four-dot form `inventory.inventory.level` / `inventory.inventory.capacity` (21 level, 9 capacity, plus one in `utilities.py`) — reaching through the wrapper to the underlying SimPy container because `Inventory.level` was stale and `Inventory.capacity` was a duplicated instance attr. Both are now `@property`s delegating to `self.inventory` (the container):

```python
@property
def level(self):
    return self.inventory.level

@property
def capacity(self):
    return self.inventory.capacity
```

`Inventory.__init__` no longer sets `self.capacity = capacity`; the container constructor receives the local `capacity` parameter directly. All 30 four-dot sites were collapsed to the single-dot form (`inventory.level`, `inventory.capacity`). Single source of truth for both attributes is now the SimPy container. Verified via `examples/py/intro_simple.py` — canonical output unchanged.

This partially addresses §4.10: the four-dot noise is gone from reads, though the awkward `Inventory.inventory` attribute name itself remains (renaming to `store`/`_container` is still available as a follow-up).

### 3.8 `Inventory.__init__` uses `replenishment_policy.__name__` on an instance ✅ Resolved
`core.py:1567–1570`

**Original issue:** `replenishment_policy` here is an **instance** (built in `InventoryNode.__init__`), so `replenishment_policy.__name__` would raise `AttributeError` inside the error-reporting path, masking the real `TypeError` the branch was trying to raise.

**Fix applied:** both the `logger.error` and `raise TypeError` lines now use `type(replenishment_policy).__name__`, which works on instances and classes alike. No other `.__name__` usages in `core.py` had the same problem (the rest are `self.__class__.__name__`, which is already correct). Verified via `examples/py/intro_simple.py` — canonical output unchanged.

### 3.9 Random number generation is ungovernable ✅ Resolved
`core.py:1302, 1467` (the two probabilistic disruption call sites)

**Original issue:** both disruption loops called `random.random()` directly against the global `random` module state. Users had no way to seed the library deterministically, share an RNG across components, or swap in a custom RNG (e.g. NumPy's `default_rng`).

**Fix applied:**

1. Module-level default RNG: `_rng = random.Random()` added near the top of `core.py`.
2. Package-level seeder: `set_seed(seed)` function exported via the existing wildcard re-export in `Components/__init__.py`. Seeding once before building the network makes the whole run reproducible for components using the default RNG.
3. Optional `rng: random.Random = None` argument added to `Node.__init__` and `Link.__init__`. Each constructor stores `self.rng = rng if rng is not None else _rng`. Both disruption loops now call `self.rng.random()` instead of `random.random()`.
4. Since Node subclasses (`Supplier`, `InventoryNode`, `Manufacturer`, `Demand`) all use `**kwargs`, an `rng=` kwarg at the subclass call site flows cleanly to Node via `super().__init__(..., **kwargs)`.
5. Added a `_NODE_KWARGS` set (`{"failure_p", "node_disrupt_time", "node_recovery_time", "logging", "rng", "logger_name"}`) and extended the four `inventory_kwargs` filters in `Supplier`/`InventoryNode`/`Manufacturer` to also strip node-level kwargs — otherwise `rng=` (and the other Node-only params) would leak from a subclass's local `**kwargs` into `Inventory.__init__` and raise `TypeError` thanks to the tightened Inventory signature from §3.3. This also closes the latent leak of `failure_p` etc. that §3.3 didn't cover.

**Verified:**

- `scm.set_seed(42)` produces reproducible draws from `scm._rng`; different seeds differ.
- `scm.Supplier(..., rng=random.Random(99))` attaches the user's RNG (`node.rng is my_rng`).
- `scm.Supplier(...)` without `rng=` falls back to `scm._rng` (`node.rng is scm._rng`).
- `examples/py/intro_simple.py` canonical output unchanged (`profit: -4435.0`).
- `pytest`: 93/94 passing (same pre-existing `TestLink::test_invalid_lead_time` failure).

**Out of scope / deferred:** NumPy `default_rng` adapter. The `rng` param today expects a `random.Random`-style object (anything with a `.random()` method works). A thin wrapper class could adapt NumPy's `Generator` if users ask for it.

### 3.10 `process_order` capacity pre-check ignores customer backorders ✅ Resolved
`core.py:2040–2047` (`InventoryNode.process_order`) and `core.py:2391–2397` (`Manufacturer.process_order`):
```python
if self.inventory.on_hand + reorder_quantity > self.inventory.inventory.capacity:
    reorder_quantity = self.inventory.inventory.capacity - self.inventory.on_hand
if reorder_quantity <= 0:
    self.ongoing_order = False
    return
```

In this codebase `on_hand` is **inventory position** (shelf + in-transit), not physical on-hand — the SS formula is consistent with this: `order_quantity = S - (on_hand - backorder[1])`. The capacity clamp, however, compares `capacity` against raw `on_hand` and ignores `backorder[1]`. That breaks down when customer backorders exist:

- capacity = 100, `on_hand` = 100 (fully committed), customer backorder = 30.
- SS wants to order `S - (100 - 30) = S - 70` units.
- Pre-check computes `capacity - on_hand = 0`, drops `reorder_quantity` to 0, returns without ordering.
- Yet those 30 backordered units will leave the shelf as soon as the next delivery lands — the shelf will never actually overflow.

Net effect: replenishment stalls whenever inventory position momentarily saturates capacity while backorders are outstanding. The very condition the SS policy is trying to react to is the one the pre-check suppresses.

**Fix:** account for backorders in both the condition and the clamp, mirroring the policy's formula:
```python
gross = self.inventory.on_hand - self.node.stats.backorder[1]
if gross + reorder_quantity > self.inventory.inventory.capacity:
    reorder_quantity = self.inventory.inventory.capacity - gross
```

**Resolution (2026-04-23):** both `process_order` methods now compute `gross = self.inventory.on_hand - self.stats.backorder[1]` and use `gross` in place of `on_hand` in both the condition and the clamp. The formula now mirrors the SS/RQ/Periodic policies' own `on_hand - backorder[1]` inventory-position view, so capacity pre-check and reorder-point trigger stay in sync when customer backorders are outstanding. Verified via `examples/py/intro_simple.py` — canonical output unchanged (`profit: -4435.0`; the clamp path is not exercised at this scenario's shelf utilization, so behavior is identical in absence of backorders). `pytest`: 93/94 passing (same pre-existing `TestLink::test_invalid_lead_time` failure).

### 3.11 `Manufacturer.process_order` never commits `on_hand` — duplicate raw-material orders possible ✅ Resolved
`core.py:2382–2419` (process_order), `core.py:2260–2296` (manufacture_product)

`InventoryNode.process_order` does `self.inventory.on_hand += reorder_quantity` at line 2022 — before the yield event, inside the same synchronous step. That way the next replenishment-policy trigger sees the committed order and won't duplicate it.

`Manufacturer.process_order` never bumps `on_hand`. `on_hand` only moves in `manufacture_product` (line 2239), which fires at a later simulation time and only for the amount that actually gets produced. Between "raw-material order dispatched to process_order_raw" and "manufacture_product runs," the replenishment policy can re-trigger (via the next `inventory_drop` or the next periodic tick) with an unchanged `on_hand`, pass the pre-check, and place a second raw-material order for the same intended product units. Raw inventory then accumulates unbounded by product-shelf capacity.

**Fix:** commit the ordered quantity to `on_hand` in `Manufacturer.process_order` at the same point `InventoryNode.process_order` does (before the raw-material orders dispatch), and reconcile in `manufacture_product` when `max_producible_units` turns out less than what was committed (e.g. because batch_size or raw-material availability binds tighter than product capacity).

**Resolution (2026-04-24):**

1. `Manufacturer.process_order` now commits `self.inventory.on_hand += reorder_quantity` right after the capacity clamp and the `reorder_quantity <= 0` early return — mirroring `InventoryNode.process_order`'s existing pattern. The replenishment policy's next trigger now sees the committed position and the SS/RQ formula `on_hand - backorder[1]` correctly reflects the pending production, eliminating the same-tick duplicate-order window.

2. `Manufacturer.manufacture_product` no longer pre-increments `on_hand` on its own (the old `self.inventory.on_hand += max_producible_units` is removed). Instead it now reconciles against the commitment:
   ```python
   pending = self.inventory.on_hand - self.inventory.level
   if pending < max_producible_units:
       max_producible_units = max(pending, 0)
   ```
   This caps production per cycle at what's been committed but not yet produced (`on_hand - level`). Without this cap, a large `batch_size` combined with a small `reorder_quantity` would grow `level` past `on_hand` and break the `level <= on_hand` invariant.

3. The existing §3.6 shortfall reconciliation (`self.inventory.on_hand -= shortfall` after `put()`) remains in place to cover any residual clamp in `Inventory.put`.

**Verified:**
- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged (doesn't exercise Manufacturer).
- `examples/py/sc_with_factory.py` — manufacturer scenario with `S1 → F1 → D1`; before/after comparison via `git stash` produced byte-identical output (`profit: 49419.6`, `demand_by_site: [2, 1440]`, `fulfillment_received_by_site: [1, 720]`). Happy-path production flow is unaffected; the fix only suppresses the duplicate-order race.
- `pytest` — 93/94 (same pre-existing `TestLink::test_invalid_lead_time` failure).

### 3.12 `ongoing_order` is written by the replenishment policies but never read ✅ Resolved
`core.py:664, 760, 855` (old policy dispatch sites), `core.py:2022, 2243` (old init), and all `ongoing_order = True/False` writes in `InventoryNode.process_order` / `Manufacturer.process_order` / `Manufacturer.process_order_raw`.

**Design clarification (user, 2026-04-24):** concurrent in-flight replenishment orders are *intended* behavior in SupplyNetPy. A node may place a second order while one is outstanding provided the replenishment policy triggers it (e.g. on_hand drops below `s` again) and capacity allows. The flag was therefore not meant as a guard — keeping it as a boolean misrepresents reality the moment two or more orders are pending, and using it as a guard would break the intended semantics.

**Resolution (2026-04-24): repurposed as a counter `pending_orders`.**

- `InventoryNode` and `Manufacturer` now expose `self.pending_orders: int` (initialised to `0`), incremented at each actual dispatch and decremented when the order completes / the supplier is disrupted. Included in `_info_keys` so `node.get_info()["pending_orders"]` returns the live count.
- `InventoryNode.process_order`: `+= 1` after the capacity-clamp / `reorder_quantity <= 0` guards (the real dispatch point, before `supplier.source.inventory.get(...)`), and `-= 1` at the end (replacing the old `ongoing_order = False` clear). The early return at `reorder_quantity <= 0` no longer touches the counter (nothing was incremented yet).
- `Manufacturer.process_order_raw`: `+= 1` after the "sufficient raw inventory" early-return (so only actual supplier dispatches count), and `-= 1` after the delivery completes. Each raw-material shipment counts independently.
- `Manufacturer.process_order` no longer writes the flag — it is an orchestrator, not a dispatch point; `process_order_raw` owns the counter for raw-material orders.
- The three policy dispatch sites (`SSReplenishment.run`, `RQReplenishment.run`, `PeriodicReplenishment.run`) no longer set the flag pre-dispatch; `process_order` is now solely responsible for maintaining the counter.
- `ongoing_order_raw` (the per-raw-material dict, which *is* read at `core.py:2420` as a duplicate-dispatch guard inside a single `process_order` call) is left unchanged — it serves a different role and is out of scope for §3.12.

**Verified:**
- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged. `D1.get_info()["pending_orders"] == 1` at sim end, matching the in-transit order dispatched at t=19 in the trace.
- `examples/py/sc_with_factory.py` — manufacturer-involving scenario; `profit: 49419.6` / `revenue: 75150.0` / `total_cost: 25730.4` unchanged from baseline.
- `pytest` — 93/94 (same pre-existing `TestLink::test_invalid_lead_time` failure).

### 3.13 `create_sc_net` mutates a shadowed parameter name ✅ Resolved
`utilities.py:226, 250`

**Original issue:** the local name `nodes` was reassigned to `supplychainnet["nodes"].keys()` mid-function, shadowing the outer `nodes: list` parameter. Safe only because `nodes` wasn't read after the reassignment — a trap for future edits.

**Fix applied:** both reassignments renamed to `node_ids`, and the two `in nodes` checks updated to `in node_ids`. Canonical `examples/py/intro_simple.py` unchanged (`profit: -4435.0`); `pytest` 93/94 (same pre-existing `TestLink::test_invalid_lead_time` failure).

### 3.14 Link disruption is modeled but never checked before dispatch ✅ Resolved
`core.py:~2087` (`InventoryNode.process_order`), `core.py:~2390` (`Manufacturer.process_order_raw`), `core.py:1515` (`Link.disruption` TODO)

**Original issue:** `Link` has a full disruption state machine (`link_failure_p`, `link_disrupt_time`, `link_recovery_time`, `status` field that toggles "active"/"inactive"), and the `disruption` generator process correctly flips `status`. But no consumer of that status existed: both `InventoryNode.process_order` and `Manufacturer.process_order_raw` checked only `supplier.source.node_status` (the upstream node) before dispatching, never `supplier.status` (the link itself). So a "disrupted" link still happily carried new orders — the disruption model was dead code at the dispatch sites.

**Design choice (user, 2026-04-24):** ongoing shipments already dispatched over a link should continue even after the link goes inactive (interrupting in-transit loads would require tracking each shipment as an individual process, which is out of scope). Only *new* dispatches are blocked. The `Link.disruption` TODO ("interrupt all ongoing transports by this link on disruption") is now an explicit deferral, not a placeholder.

**Fix applied:**

1. `InventoryNode.process_order`: added a `supplier.status == "inactive"` gate immediately after the capacity clamp + `reorder_quantity <= 0` guard, *before* the shortage-bookkeeping update and the `pending_orders += 1` increment. A blocked order therefore does not inflate `pending_orders`, does not create a phantom backorder on the upstream supplier, and emits a distinct log line (`Link:L1 from S1 is disrupted. Order not placed.`). The replenishment policy re-triggers normally on the next `inventory_drop` or periodic tick; once the link recovers, the order flows through.
2. `Manufacturer.process_order_raw`: same gate, placed before the shortage check and the `node_status == "active"` branch. Clears the per-raw-material `ongoing_order_raw[raw_mat_id]` flag and yields a 1-tick timeout so the outer loop in `process_order` can retry on the next cycle.
3. `Link.disruption`: the stale TODO is replaced with a comment explicitly documenting that in-transit shipments are intentionally not interrupted.

**Verified:**

- Canonical `examples/py/intro_simple.py` output unchanged (`profit: -4435.0`) — no disruption in that scenario.
- Two new tests in `TestLinkDisruptionBlocksNewOrders` (tests/test_core.py):
  - `test_new_order_blocked_while_link_inactive`: distributor with s=100, S=150, initial_level=50; link is started inactive. After 5 sim-days, `demand_placed == [0, 0]`, `transportation_cost == 0`, `pending_orders == 0` — the SS policy tries to order but every dispatch is blocked.
  - `test_ongoing_shipment_unaffected_by_later_disruption`: same scenario but with `link_disrupt_time=lambda: 3` (link goes inactive at t=3, *after* the t=0 dispatch with lead_time=2 has landed). At t=10, `fulfillment_received[0] == 1` and `inventory_spend_cost == 10000` — the in-flight order delivered normally.
- `pytest` — 127/127 passing.

**Out of scope / deferred:**

- **In-transit interruption.** Interrupting shipments already dispatched when the link dies would need per-shipment process tracking on the `Link`; deliberately deferred per user decision.

### 3.15 Supplier-selection policies ignore link status ✅ Resolved
`core.py:~1016` (`SelectFirst.select`), `~1090` (`SelectAvailable.select`), `~1152` (`SelectCheapest.select`), `~1213` (`SelectFastest.select`)

**Original issue:** identified in §3.14's out-of-scope note. Each of the four selection policies picked from `self.node.suppliers` without checking `link.status`, so a disrupted link could still be chosen. The dispatch gate (§3.14) would then block the chosen order, the replenishment policy would have to wait for its next trigger, and throughput would needlessly stall even when alternative active links existed.

**Fix applied:**

1. Two new helpers on the base `SupplierSelectionPolicy` consolidate the repeated logic:
   - `_active_suppliers()` returns `[s for s in self.node.suppliers if s.status == "active"]`, falling back to the full list if every link is down. The fallback keeps callers non-`None`-aware — the dispatch gate blocks the inactive choice and the policy retries on the next trigger. Nothing changes for zero-disruption scenarios (the subset equals the full list).
   - `_apply_mode(selected)` centralises the fixed/dynamic mode handling. New behavior: in `"fixed"` mode, if the locked supplier's link is currently inactive, the policy returns the dynamically-selected active supplier for that call without changing the lock. Once the locked supplier's link recovers, routing resumes through it. This preserves the "stable routing" intent of fixed mode while routing around transient disruptions.
2. Each of the four `select()` methods was refactored to: `candidates = self._active_suppliers()`, then apply the policy-specific criterion to `candidates`, then `return self._apply_mode(selected)`. The net result is that `SelectFirst` picks the first *active* supplier, `SelectAvailable` prefers active suppliers with enough inventory (with documented fallbacks), `SelectCheapest` picks the cheapest *active* link, and `SelectFastest` picks the fastest *active* link.
3. Previously the four subclasses each open-coded the `fixed_supplier = selected` / `return self.fixed_supplier` pattern; that duplication is gone and the mode-handling logic now lives in one place.

**Verified:**

- Six new tests in `TestSelectionPoliciesFilterDisruptedLinks` (tests/test_core.py), each with a two-supplier topology where one link is flipped `inactive` without scheduling a `Link.disruption` process (so the test controls the status directly):
  - `test_select_first_skips_disrupted`: disrupts the first link; asserts `SelectFirst` picks the second.
  - `test_select_available_skips_disrupted_even_if_it_has_inventory`: disrupts the only supplier that can cover the order; asserts the policy still returns the active alternative.
  - `test_select_cheapest_skips_disrupted_cheapest`: disrupts the cheaper link; asserts the pricier active link is chosen.
  - `test_select_fastest_skips_disrupted_fastest`: disrupts the faster link; asserts the slower active link is chosen.
  - `test_all_disrupted_falls_back_to_full_list`: disrupts both; asserts the policy returns one of them (dispatch gate blocks, policy retries later).
  - `test_fixed_mode_routes_around_disrupted_lock_without_changing_lock`: locks to a supplier, disrupts it, asserts the policy routes around without updating the lock, then recovers the link and asserts the lock is reinstated.
- Canonical `examples/py/intro_simple.py` unchanged (`profit: -4435.0`): a single-link network can't exercise the filter.
- `pytest` — 133/133 passing.

---

## 4. Design / architecture issues

### 4.1 `core.py` is a god-file
17 classes in 2,617 lines. A practical split:

```
Components/
├── base.py           # NamedEntity, InfoMixin, validation helpers
├── inventory.py      # Inventory
├── policies.py       # InventoryReplenishment + subclasses
├── selection.py      # SupplierSelectionPolicy + subclasses
├── nodes.py          # Node, Supplier, InventoryNode, Manufacturer, Demand
├── links.py          # Link
├── products.py       # RawMaterial, Product
├── stats.py          # Statistics
└── __init__.py       # explicit re-exports via __all__
```
Each module then tops out around 200–400 lines, is much easier to review, and lets test modules mirror the split.

### 4.2 `Components/__init__.py` does wildcard re-exports ✅ Resolved
```python
from SupplyNetPy.Components.core import *
from SupplyNetPy.Components.logger import *
from SupplyNetPy.Components.utilities import *
```
There is no `__all__` in any of the three modules, so this imports `simpy`, `random`, `copy`, `numbers`, `networkx`, `matplotlib.pyplot`, `logging`, and every private name. Users writing `scm.copy.deepcopy(...)` are then accidentally depending on internal imports. Define `__all__` in each module and drop the wildcard in favor of explicit re-exports.

**Resolution (2026-04-24):**

1. Added `__all__` to each of the three modules so that their public surface is now explicit:
   - `core.py` — 25 names: `set_seed`, the three validators, `NamedEntity`, `InfoMixin`, `Statistics`, `RawMaterial`, `Product`, the four replenishment-policy classes (base + three subclasses), the five supplier-selection classes (base + four subclasses), `Node`, `Link`, `Inventory`, `Supplier`, `InventoryNode`, `Manufacturer`, `Demand`. `global_logger`, `_rng`, `_LOGGER_KWARGS`, `_NODE_KWARGS`, and the module imports are deliberately excluded.
   - `logger.py` — 1 name: `GlobalLogger`.
   - `utilities.py` — 7 names: `check_duplicate_id`, `process_info_dict`, `visualize_sc_net`, `get_sc_net_info`, `create_sc_net`, `simulate_sc_net`, `print_node_wise_performance`.
2. `utilities.py` no longer does `from ...core import *`; it now does explicit named imports of the six core classes it actually uses (`Node`, `Link`, `Supplier`, `InventoryNode`, `Manufacturer`, `Demand`) plus `global_logger` (internal, used for error logging). This closes the secondary leak whereby every core public name also became reachable via `scm.utilities.<name>`.
3. `Components/__init__.py` rewritten to use explicit re-exports (no wildcards) and a top-level `__all__` listing all 33 public names across the three submodules.

**Verified:**

- `import SupplyNetPy.Components as scm` exposes every documented class/function (`scm.SSReplenishment`, `scm.create_sc_net`, `scm.set_seed`, `scm.GlobalLogger`, ...).
- Internals no longer leak onto `scm`: a hasattr scan for `simpy`, `random`, `copy`, `numbers`, `networkx`, `nx`, `matplotlib`, `plt`, `logging`, `_rng`, `_LOGGER_KWARGS`, `_NODE_KWARGS`, `global_logger` confirms none are reachable via `scm.*`.
- `len(scm.__all__) == 33`.
- `pytest` — 125/125 passing.
- `examples/py/intro_simple.py` canonical `profit: -4435.0` unchanged. Required a one-line update to the example's import block: the old form chained `import Components.core as scm` then `import Components.utilities as scm`, relying on utilities re-exporting core via wildcard; the new form uses the documented `import SupplyNetPy.Components as scm` (with `sys.path` pointed at `src/` rather than `src/SupplyNetPy/`).

**Out of scope / deferred:** §4.1 (splitting `core.py` into `base.py` / `inventory.py` / `policies.py` / etc.) remains open. With `__all__` now declared, the split becomes mechanical — each new module carries over the slice of `__all__` it owns.

### 4.2-adjacent: Statistics running-averages refactor — deferred

During the §3/§4 pass the user raised a concern that accumulating `node_cost` / `inventory_carry_cost` / `inventory_spend_cost` / `transportation_cost` as un-bounded totals could overflow or lose precision on very long simulations. We discussed converting the accumulators to running averages (Welford-style) to cap the stored magnitude.

**Decision:** deferred. Python `float` is IEEE 754 double precision — max ≈ 1.8e308, with precision loss only past 2^53 ≈ 9e15. A million-unit simulation burning \$100/day of holding cost reaches 1e8 after 2,700 years — comfortably inside the safe range. The refactor is available if long-horizon studies surface measurable precision loss; until then, totals remain totals.

### 4.3 Replenishment and selection policies require privileged knowledge of the node ✅ Resolved
`core.py:1437–1510` (new `Node` methods), `core.py:~1601` (new `Link.available_quantity`), `core.py:~697` (`SSReplenishment.run`), `core.py:~792` (`RQReplenishment.run`), `core.py:~882` (`PeriodicReplenishment.run`), `core.py:~1143` (`SelectAvailable.select`)

**Original issue:** every subclass of `InventoryReplenishment.run` reached deep into the owning node — `self.node.inventory.on_hand`, `self.node.stats.backorder[1]`, `self.node.selection_policy.select(qty)`, `self.env.process(self.node.process_order(...))`, `self.node.inventory_drop`, plus the manual "yield then reset" pattern for the drop event. A user writing a new policy had to re-discover the whole contract. `SelectAvailable.select` had the analogous problem on the other side — it reached into `source.inventory.level` to compare candidate links.

**Fix applied:** three small methods on `Node` now capture the contract, and one on `Link` captures the supplier-side read:

1. `Node.position() -> float` — returns `self.inventory.on_hand - self.stats.backorder[1]`. Replaces the raw `on_hand - backorder[1]` expression scattered across the three replenishment policies and keeps the arithmetic in one place.
2. `Node.place_order(quantity) -> None` — wraps `supplier = selection_policy.select(quantity)` + `env.process(process_order(supplier, quantity))`. Policies no longer touch `selection_policy` or `process_order` directly.
3. `Node.wait_for_drop()` (generator) — yields on `self.inventory_drop` and rotates a fresh `env.event()` into its slot on wake-up. Policies use `yield from self.node.wait_for_drop()` in place of the old `yield self.node.inventory_drop; self.node.inventory_drop = self.env.event()` pair.
4. `Link.available_quantity() -> float` — returns `self.source.inventory.level`. `SelectAvailable.select` now filters candidates via `s.available_quantity() >= order_quantity` without reaching past the link.

The three replenishment policies were rewritten against this contract:

- `SSReplenishment.run`: `position = self.node.position(); if position <= s: self.node.place_order(S - position); ...; yield from self.node.wait_for_drop()`.
- `RQReplenishment.run`: same pattern with `Q` as the order quantity.
- `PeriodicReplenishment.run`: `self.node.place_order(reorder_quantity)` (no drop wait — it's periodic-only).

The `self.node.logger.logger.info(...)` status-tick line is intentionally left as-is — logging-wrapper cleanup is `§4.9`'s scope, not `§4.3`'s. The remaining coupling is just `self.node.inventory.level` for the status log and `self.node.inventory.level < ss` check in `PeriodicReplenishment` (safety-stock top-up, measured against physical shelf rather than inventory position — different semantics from `position()`).

The contract is deliberately defined on `Node` rather than on a separate mixin, so any subclass with the required attributes (`inventory`, `stats`, `selection_policy`, `process_order`, `inventory_drop`) participates automatically. Today that's `InventoryNode` and `Manufacturer`; `Supplier` participates in `position()` since it has both `inventory` and `stats`, and could grow its own `place_order`/`wait_for_drop` path later without a new base class. `Demand` simply doesn't call these methods.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged.
- `examples/py/sc_with_factory.py` — manufacturer scenario unchanged (`profit: 49419.6`, `total_cost: 25730.4`, `transportation_cost: 240`).
- `pytest` — 133/133 passing (all existing behavior preserved, including the disruption/selection-policy tests from §3.14/§3.15 that exercise `_active_suppliers` + `available_quantity`).

**Out of scope / deferred:**

- `§4.9` (the `logger.logger` wrapper). A `Node.log_info(msg)` shortcut was considered but would shadow the proper fix: make `GlobalLogger` a real `LoggerAdapter` so callers write `node.logger.info(...)` directly.
- Moving `position()`/`place_order()`/`wait_for_drop()` onto a `ReplenishableNode` mixin. Mechanical once `core.py` is split per `§4.1`; deferred along with that split.

### 4.4 `Link.__init__` mutates the sink node (`self.sink.suppliers.append(self)`) ✅ Resolved
`core.py:~1397` (`Node.__init__` now initialises `suppliers`), `core.py:~1443` (new `Node.add_supplier_link`), `core.py:~1639` (`Link.__init__` now calls the method), `core.py:~2249` / `~2477` (removed redundant `self.suppliers = []` from `InventoryNode` / `Manufacturer`)

**Original issue:** `Link.__init__` did `self.sink.suppliers.append(self)` — direct peer-attribute mutation in a constructor. That coupled `Link` to the internal shape of `InventoryNode` / `Manufacturer` (the only subclasses that set `self.suppliers = []`). A user who passed a plain `Node` or a `Demand` as a Link sink got `AttributeError: 'Node' object has no attribute 'suppliers'` at construction time, even though the type checks in `Link.__init__` otherwise allowed it.

**Design note.** The review suggested moving link-registration into `create_sc_net` (or a dedicated `Network.add_link()`). A full move is impractical today: the library's direct-instantiation API (used across all `examples/py/*.py`, every notebook, the README, and `docs/*`) relies on `scm.Link(env=env, source=..., sink=...)` followed by `env.run(until=...)` without `create_sc_net`. Removing the auto-registration would silently break every one of those by leaving `sink.suppliers` empty — the replenishment policy would run against a node with no suppliers. The resolution therefore keeps the auto-registration but routes it through a proper method so the *mechanism* the review objected to (direct peer-attribute mutation + implicit attribute requirement on the sink) is gone.

**Fix applied:**

1. `Node.__init__` now initialises `self.suppliers = []` for every Node. A plain `Node` (or any subclass) can be a Link sink without the subclass having to remember to set up the list. `InventoryNode.__init__` and `Manufacturer.__init__` had their `self.suppliers = []` lines removed — the empty list now comes from `super().__init__`.
2. New `Node.add_supplier_link(link)` method is the supported entry point for registering an inbound Link with its sink. It validates that `link` is a `Link` instance and that `link.sink is self`, then appends to `self.suppliers`. This replaces the `self.sink.suppliers.append(self)` poke with a named, typed, validated interface on the sink object itself.
3. `Link.__init__` now calls `self.sink.add_supplier_link(self)` instead of mutating `sink.suppliers` directly. Behaviour is unchanged for existing callers; the mechanism is cleaner and no longer depends on the sink's internal layout.
4. Users constructing a Link before its sink (or wanting an explicit attach step) can call `sink.add_supplier_link(link)` themselves — the method is idempotent from the caller's POV and validates its inputs.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` / `total_cost: 25435.0` / `transportation_cost: 25` unchanged.
- `examples/py/sc_with_factory.py` — manufacturer scenario unchanged (`profit: 49419.6`, `total_cost: 25730.4`, `transportation_cost: 240`).
- `pytest` — 133/133 passing (every existing Link-construction call site continues to work, since auto-registration is preserved).
- Ad-hoc check: constructing `scm.Link(env=env, source=sup, sink=plain_node, cost=1, lead_time=lambda: 1)` now succeeds and leaves `plain_node.suppliers == [link]` — previously this raised `AttributeError`. `plain_node.add_supplier_link('not a link')` raises `TypeError`; calling it with a Link whose sink is a different node raises `ValueError`.

**Out of scope / deferred:**

- A dedicated `Network.add_link()` and full removal of the constructor side-effect belong with §6.1 (introduce a `Network` wrapper class around the `supplychainnet` dict). Once `Network` owns link construction end-to-end, `Link.__init__` can stop calling `add_supplier_link` entirely and the registration becomes `network.add_link(link)` — the method added here is already the right shape for that migration.

### 4.5 Two construction styles, silently incompatible ✅ Resolved
`utilities.py:~188` (old first-element-only check replaced with full scans)

**Original issue:** the env-required guard in `create_sc_net` only inspected `nodes[0]` / `links[0]` / `demands[0]`. A list where `nodes[0]` was a dict but a later element was a pre-built `Node` instance bypassed the guard entirely — a fresh `simpy.Environment` was created for the dict items, and the `isinstance(node, Node)` branch then happily re-used it, silently dropping the object's real env on the floor. The net result was two sets of SimPy processes running against different environments.

**Fix applied:** the first-element check is replaced by three cooperating passes, in order:

1. **Homogeneity per list.** `_check_homogeneous(items, obj_cls, list_name)` scans the list and raises `ValueError("<list> mixes dicts and <Cls> instances")` if both a `dict` and an `obj_cls` instance appear in the same list. Consistent with the CLAUDE.md guidance that the two construction styles are not meant to be mixed within a single list. (Unrelated types like the DummyNode/DummyLink shape-only test fixtures are neither — they pass through silently as before, since they're out of scope for the mix-of-styles check.)
2. **Env required across all lists.** `any_object = any(isinstance(x, Node) for x in nodes) or any(isinstance(x, Link) for x in links) or any(isinstance(x, Demand) for x in demands)` — scanned across every element, not just the first. If `any_object` is true and `env` is `None`, raise as before. Scanning also removes the latent IndexError on empty lists that the `[0]` form had.
3. **Env match per object.** `_check_env_match(items, obj_cls, list_name)` iterates each list and, for every pre-built instance, confirms that `instance.env is env`. Mismatch raises `ValueError("<list>[i] env does not match the env passed to create_sc_net")`. Pre-fix this mismatch was silently accepted and produced a split-env simulation.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged.
- `examples/py/sc_with_factory.py` — canonical `profit: 49419.6` unchanged.
- `pytest` — 136/136 passing, including three new tests in `tests/test_utilities.py` that exercise the fix end-to-end:
  - `test_create_sc_net_mixed_nodes_dict_and_object_raises` — nodes list mixing a dict at index 0 with a real `Supplier` at index 1 must raise.
  - `test_create_sc_net_object_at_nonzero_index_still_requires_env` — links list mixing a dict at index 0 with a real `Link` at index 1 must raise (covers the exact first-element-only blind spot the review called out).
  - `test_create_sc_net_object_env_must_match` — pre-built objects constructed against a different `simpy.Environment` than the one passed to `create_sc_net` must raise.
- The pre-existing `test_create_sc_net_requires_env_for_objects` still passes (a single-Node list with `env=None` raises as before).

**Out of scope / deferred:**

- The stricter "unknown items should raise" variant (so that the shape-only Dummy-based tests in `tests/test_utilities.py` would also hit validation) is not applied here. Those tests pre-date the real-component integration tests and rely on silent-skip for objects that duck-type but don't subclass the real types. Cleaning them up is cosmetic and can follow §7 (testing gaps) later.

### 4.6 `_info_keys`/`_stats_keys` pattern is manual and duplicates fields ✅ Resolved
`core.py` — every class that previously set `self._info_keys = [...]` or called `self._info_keys.extend([...])` in its `__init__` now declares the list at class level.

**Original issue:** every subclass re-assigned `self._info_keys = [...]` in `__init__` and subclasses in the inheritance chain then called `self._info_keys.extend([...])` on top of `super().__init__`. The pattern was easy to get wrong — adding an attribute meant remembering to append it in the right `__init__`, the attribute list was not discoverable without constructing an instance, and `mkdocstrings` Attributes blocks documented a list that only existed at run time.

**Fix applied:** each class now declares `_info_keys` (and `_stats_keys` where applicable) as a class-level attribute computed from its parent:

```python
class Node(NamedEntity, InfoMixin):
    _info_keys = ["ID", "name", "node_type", "failure_p", "node_status", "logging"]

class Supplier(Node):
    _info_keys = Node._info_keys + ["raw_material", "sell_price"]
```

This pattern is applied to `Statistics`, `RawMaterial`, `Product`, `InventoryReplenishment` and its three subclasses, `SupplierSelectionPolicy` and its four subclasses, `Node`, `Link`, `Inventory`, `Supplier`, `InventoryNode`, `Manufacturer`, and `Demand` — the list of KPIs / info fields for any class is now readable without constructing an instance (`scm.Supplier._info_keys`). Each subclass owns a fresh list (the `Parent._info_keys + [...]` expression creates a new list, not an alias), so extending one cannot pollute another.

**Special case: `Statistics`.** `Supplier.__init__` and `Manufacturer.__init__` append subclass-specific KPIs (`total_material_cost`, `total_manufacturing_cost`) onto their own `self.stats._stats_keys` / `self.stats._cost_components` after constructing `Statistics`. If those lists lived only at class level, the appends would mutate the shared list and leak KPIs across every Statistics instance in the process. `Statistics.__init__` therefore clones the two lists onto the instance on construction:

```python
self._stats_keys = list(type(self)._stats_keys)
self._cost_components = list(type(self)._cost_components)
```

The class attribute remains the declarative source of truth; per-node extensions modify the instance copy only.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged.
- `examples/py/sc_with_factory.py` — canonical `profit: 49419.6` unchanged.
- `pytest` — 141/141 passing, including five new tests in `TestDeclarativeInfoKeys`:
  - `test_node_subclass_keys_are_class_level` — class-level keys are readable without instances.
  - `test_subclass_list_is_independent_of_parent` — no aliasing of parent lists.
  - `test_selection_policy_subclass_keys` — policy subclasses expose `["node", "mode", "name"]`.
  - `test_get_info_uses_class_level_keys` — `get_info()` returns the declarative union of keys.
  - `test_statistics_per_instance_extension_does_not_leak` — `Supplier`'s `total_material_cost` append does not leak onto a sibling `InventoryNode`'s stats or onto the class attribute.

**Out of scope / deferred:**

- Moving to `dataclasses.fields` or a `@info_field` decorator (the other variant the review mentioned) is a separate refactor — it would require giving up the current "arbitrary attribute name, listed by string" flexibility and would affect every call site of `get_info()` / `get_statistics()`. The class-level list form achieves the main goal (declarative, discoverable, no subclass-`__init__` wiring) without the broader surgery, so the decorator variant is deferred.

### 4.7 `node_type` is a string with magic values ✅ Resolved
`core.py:~80` (new `NodeType` enum, added to `__all__`), `core.py:~1419` (`Node.__init__` validation), `utilities.py:~17` (new `_NODE_DISPATCH` table), `utilities.py:~281` / `~300` (`create_sc_net` branches refactored to use it), `utilities.py:~416` (`simulate_sc_net` infinite-supplier check).

**Original issue:** `Node.__init__` validated `node_type.lower()` against a hard-coded list of 9 strings. `create_sc_net` dispatched incoming dicts / objects via its own hard-coded `if/elif` ladder with a parallel 9-string list. Adding a new node type meant editing both lists; in fact the two had already drifted — the dispatch accepted `"shop"` as a retailer but `Node.__init__`'s list omitted it, so a dict with `node_type: "shop"` would pass dispatch and then raise `ValueError("Invalid node type.")` from inside the `InventoryNode` constructor. Magic strings also meant no IDE autocomplete when users wrote `node_type="manufacutrer"` (sic).

**Fix applied:**

1. New `NodeType(str, enum.Enum)` in `core.py` with 10 members (adds the previously-missing `SHOP`). Being a `str` subclass, every existing comparison in the codebase (`node.node_type == "demand"`, `"supplier" in node.node_type`, `node.node_type.lower()`) continues to work unchanged.
2. `NodeType._missing_` implements case-insensitive lookup so `NodeType("SUPPLIER")` / `NodeType("Supplier")` both resolve to `NodeType.SUPPLIER`. Users can now pass either a string or the enum member — `scm.Supplier(..., node_type=scm.NodeType.SUPPLIER)` is the autocomplete-friendly form.
3. `Node.__init__` validates by calling `NodeType(node_type)` and storing the normalized `.value` on `self.node_type`. Invalid values raise `ValueError(f"Invalid node type: {node_type}.")`, with the offending value in the message (previously the raise was generic).
4. `_NODE_DISPATCH` in `utilities.py` maps each `NodeType` member to `(constructor_class, counter_key, drop_node_type_kwarg)`. `create_sc_net`'s two parallel `if/elif` ladders (one for the dict branch, one for the object branch) collapse to a single enum lookup each. The `drop_node_type` flag encodes the one constructor asymmetry (`Manufacturer.__init__` does not accept a `node_type` parameter).
5. Separate `num_suppliers` / `num_manufacturers` / `num_distributors` / `num_retailers` locals are replaced by a `counters` dict keyed by the same strings, so the dispatch writes `counters[_NODE_DISPATCH[nt][1]] += 1` in one place. `supplychainnet["num_of_nodes"]` becomes `sum(counters.values())` and the per-kind counts are written via `supplychainnet.update(counters)`.
6. `simulate_sc_net`'s ad-hoc `"infinite" in node.node_type.lower()` substring check was replaced by `node.node_type == NodeType.INFINITE_SUPPLIER`.
7. `NodeType` is re-exported via `Components/__init__.py` and listed in `core.py`'s `__all__`.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged.
- `examples/py/sc_with_factory.py` — canonical `profit: 49419.6` unchanged.
- `pytest` — 147/147 passing, including six new tests:
  - `TestNodeTypeEnum.test_enum_members_cover_all_types` — locks the 10-member enum surface.
  - `TestNodeTypeEnum.test_enum_is_str_compatible` — asserts the existing string-comparison contract is preserved.
  - `TestNodeTypeEnum.test_case_insensitive_lookup` — both `"SUPPLIER"` and `"Supplier"` resolve to `NodeType.SUPPLIER`.
  - `TestNodeTypeEnum.test_node_accepts_enum_or_string` — users can pass either form.
  - `TestNodeTypeEnum.test_invalid_node_type_raises` — `"crossdock"` raises `ValueError` with the offending value in the message.
  - `test_create_sc_net_shop_node_type_end_to_end` — the previously-latent `"shop"` bug is fixed: dict with `node_type="shop"` constructs as an `InventoryNode` counted under `num_retailers`.

**Out of scope / deferred:**

- Richer semantic helpers such as `node.is_supplier()` / `NodeType.is_retail()` are not added; the review asked for an enum to dedupe the validation tables, not a full type-classification API. The `"supplier" in node.node_type` substring check in `Link.__init__` survives for now; replacing it with `node.node_type in (NodeType.SUPPLIER, NodeType.INFINITE_SUPPLIER)` is a separate cleanup.

### 4.8 Global state: `global_logger` and the simulation trace file ✅ Resolved
`logger.py` (rewrite, ~160 lines), `core.py:~1499` (`Node.__init__` per-node logger creation).

**Original issue:** `core.py:46` (`global_logger = GlobalLogger()`) and `logger.py` together opened `simulation_trace.log` with `mode='w'` at import time, in the current working directory. Worse, `Node.__init__` instantiated a fresh `GlobalLogger(logger_name=node.ID)` per node and then called `enable_logging()`, both of which re-opened `simulation_trace.log` with `mode='w'` — so a network with N nodes truncated the trace file roughly N+1 times during construction. Side effects:

- Parallel simulations from the same cwd overwrote the same file.
- Tests that just imported `SupplyNetPy.Components` blew the file away.
- The log-file path was not configurable before import.
- `disable_logging()` called `logging.disable(logging.CRITICAL)` — a process-wide kill switch that silenced the host application's own loggers as a side effect.

**Fix applied:**

1. `GlobalLogger.__init__` defaults flipped to **opt-in**: `log_to_file=False`, `log_to_screen=False`. The constructor no longer opens any file. `configure_logger` always attaches a `logging.NullHandler` so the underlying logger is well-formed and never triggers Python's "No handlers could be found" stderr fallback — the documented library pattern (<https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library>).
2. `enable_logging(log_to_file=True, log_to_screen=True)` is unchanged in spirit — explicit opt-in still attaches both handlers — and `simulate_sc_net(logging=True)` (the canonical entry point) calls it for the user, so the historical "running a simulation produces a trace file" behavior is preserved without the import-time side effects.
3. Per-node loggers are now hierarchical children of the library root: `Node.__init__` creates `GlobalLogger(logger_name=f"sim_trace.{node.ID}")` and **does not** call `enable_logging()` per-node. Records propagate up to the single set of handlers configured on `global_logger`, so the trace file is opened exactly once (when the user opts in) instead of once per node.
4. To preserve the documented log-line shape (`INFO D1 - ...` rather than `INFO sim_trace.D1 - ...`), a `_ShortNameFilter` strips the `sim_trace.` prefix into a `record.short_name` attribute and the formatter uses `%(short_name)s`. The original `record.name` is left intact so other handlers reading it are unaffected.
5. The library root (`sim_trace`) is set to `propagate=False` so the library's records do not bubble out into the host application's root logger configuration.
6. `disable_logging()` no longer calls `logging.disable(CRITICAL)`. It now sets `self.logger.disabled = True` and drops handlers (NullHandler stays). This is local to the wrapper's logger and no longer mutes the host application's loggers as a side effect.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged. Per-node log lines (`INFO D1 - ...`) and aggregate lines (`INFO sim_trace - ...`) match the documented expected output verbatim.
- A fresh `python -c "import SupplyNetPy.Components"` no longer creates `simulation_trace.log`.
- `pytest` — 151/151 passing, including four new tests in `TestLoggerOptIn`:
  - `test_module_logger_is_inert_by_default` — after `disable_logging()`, the global logger holds only `NullHandler` and exposes `log_to_file=False` / `log_to_screen=False`.
  - `test_node_does_not_attach_its_own_file_handler` — per-node loggers carry no `FileHandler` of their own.
  - `test_per_node_logger_is_child_of_sim_trace` — per-node logger name is `f"sim_trace.{ID}"`.
  - `test_disable_logging_does_not_set_global_disable` — confirms `logging.root.manager.disable == 0` after `global_logger.disable_logging()`, locking down that the global hammer is gone.

**Out of scope / deferred:**

- The user-facing `scm.global_logger.enable_logging()` / `disable_logging()` surface is preserved, including the nullary form. The §4.9 redesign of `GlobalLogger` itself (drop the wrapper or convert it to a `LoggerAdapter`) is independent and not addressed here.
- `FileHandler` is still opened in `mode='w'` when the user opts in. Switching to `mode='a'` is a separate ergonomic decision; the §4.8 issue was about *who* opens the file and *when*, not the open mode.

### 4.9 `GlobalLogger` is not actually a logger ✅ Resolved
`logger.py` (now subclasses `logging.LoggerAdapter`), `core.py` (39 call-site collapses), `utilities.py` (12 call-site collapses + two `logger = global_logger.logger` locals).

**Original issue:** `GlobalLogger` was a thin wrapper that exposed the underlying Python `logging.Logger` as `self.logger` and offered no level methods of its own. Every call site went through the double-hop `self.node.logger.logger.info(...)` / `global_logger.logger.error(...)` (73 inline call sites in the library code). The wrapper also carried a hard-coded string-level dispatcher `log(self, level, message)` which was, at this point in the codebase, dead code — no caller used it.

**Fix applied:**

1. `GlobalLogger` now subclasses :class:`logging.LoggerAdapter`. Callers use `node.logger.info(...)`, `global_logger.error(...)`, etc. directly. The constructor builds the underlying logger with the same name / propagation / opt-in handler logic from §4.8 and forwards it to `super().__init__(logger, extra=None)`.
2. `LoggerAdapter` exposes the underlying `logging.Logger` as the standard `.logger` attribute, so the historical reach-through pattern (`node.logger.logger.handlers`, `node.logger.logger.name`) keeps working — useful for tests and any external code that already learned the old shape.
3. The dead `log(self, level, message)` string-level dispatcher is dropped. `LoggerAdapter` provides a numeric-level `log(level, msg, ...)` (via `logging.INFO` etc.) for callers who want it.
4. All 73 inline `self.node.logger.logger.<level>(...)` / `self.logger.logger.<level>(...)` / `global_logger.logger.<level>(...)` call sites in `core.py` and `utilities.py` are collapsed to the single-dot adapter form. Two `logger = global_logger.logger` locals in `utilities.py` are simplified to `logger = global_logger`.
5. The `enable_logging` / `disable_logging` / `set_log_file` / `configure_logger` API from §4.8 is preserved unchanged — the §4.8 fix layered cleanly on top of `LoggerAdapter`.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged. Per-node log lines (`INFO D1 - …`) and aggregate lines (`INFO sim_trace - …`) match the documented expected output verbatim.
- `pytest` — 154/154 passing, including three new tests in `TestLoggerAdapter`:
  - `test_global_logger_is_a_logger_adapter` — `isinstance(scm.global_logger, logging.LoggerAdapter)`.
  - `test_node_logger_is_a_logger_adapter` — every `node.logger` is a `LoggerAdapter` exposing `debug` / `info` / `warning` / `error` / `critical` / `log` directly.
  - `test_underlying_logger_still_reachable` — `node.logger.logger` is the underlying `logging.Logger` (named `sim_trace.<ID>`), preserving backward compatibility for code that reaches in.
- `grep` confirms no production `*.logger.logger.<method>(` call sites remain in `src/`.

**Out of scope / deferred:**

- Replacing `GlobalLogger` outright with a bare `logging.getLogger` call (the alternative the review suggested) is not done. The wrapper still earns its keep by owning `enable_logging` / `disable_logging` / `set_log_file` / `configure_logger`, the `_ShortNameFilter` glue, and the opt-in handler defaults from §4.8.
- The string-level `log` dispatcher is removed; the inherited numeric-level `LoggerAdapter.log(level, msg, ...)` takes over its slot. No callers used either form, so this is a silent surface change.

### 4.10 `Inventory.inventory` naming ✅ Resolved (subsumed by §3.7)
**Original issue:** A class named `Inventory` whose main attribute was also `inventory` (and that `inventory` was actually a `simpy.Container`) created four-dot accesses like `node.inventory.inventory.level` throughout the codebase.

**Fix status:** §3.7 ("`Inventory.level` is a stale shadow of `Inventory.inventory.level`") collapsed `Inventory.level` and `Inventory.capacity` to read-only `@property`s that delegate to the underlying container. As a result, every call site in `src/` now reads `node.inventory.level` / `node.inventory.capacity` (one dot, not two). A `grep` of the entire repo for `\.inventory\.inventory\b` finds no occurrences in `src/` or `tests/` — only historical mentions in `REVIEW.md` itself.

The cosmetic step of renaming the underlying `simpy.Container` attribute (`self.inventory` → `self._container` / `self.store`) was deliberately not done. With §3.7's properties in place there is no remaining external four-dot access to motivate the rename, and the name is only visible inside the `Inventory` class — a self-rename without external benefit. Treating §4.10 as resolved by §3.7 keeps the noise down; the rename can be revisited if a future change needs to expose the container directly.

---

## 5. Performance / scaling concerns

### 5.1 Polling loops for "continuous" behaviors ✅ Resolved
`core.py:~2197` (`Supplier.behavior`), `core.py:~2599` / `~2691` / `~2755` (`Manufacturer.__init__`, `Manufacturer.behavior`, `Manufacturer.process_order_raw`), `core.py:80` (`_NODE_KWARGS`), `core.py:~2179` / `~2360` / `~2592` / `~2941` (per-subclass `Statistics(...)` call sites), `core.py:~1965` (`Inventory.__init__` adds `perish_changed`), `core.py:~2031` (`Inventory.put` signals `perish_changed` on head change), `core.py:~2080` (`Inventory.remove_expired` event-driven via `AnyOf`).

**Original issues (four bullets):**
- `Supplier.behavior` yielded `timeout(1)` when full and again after mining (via `extraction_time`). For a 10-year simulation at day granularity, that is 3,650 timeouts per supplier even when nothing happens.
- `Manufacturer.behavior` yielded `timeout(1)` every tick regardless of whether raw materials arrived.
- `Inventory.remove_expired` ticks every 1 unit (`yield self.env.timeout(1)`).
- `Statistics.update_stats_periodically` ticks every 1 unit and the period was hard-coded at every call site.

**Fix applied (1) — `Supplier.behavior` is now event-driven:**

The full-inventory branch's `yield self.env.timeout(1)` is replaced with `yield from self.wait_for_drop()`. The drop signal already exists — `Inventory.get` succeeds `node.inventory_drop` whenever the supplier ships, and `Node.wait_for_drop()` is the documented contract for blocking on it (introduced in §4.3). For a supplier with `capacity = inf` (the `infinite_supplier` path) this branch was never reached, so the change is a no-op for that case. The per-iteration tail-log `f"... Inventory level: ..."` now fires only on event-driven wake-ups instead of on every tick — a noise win, not a regression.

**Fix applied (2) — `Manufacturer.behavior` is now event-driven:**

The natural trigger for production is "raw material just arrived" — `process_order` only commits `on_hand` and orders raw, while `process_order_raw` actually deposits raw into `raw_inventory_counts`. A new `simpy.Event`, `self.raw_material_arrived`, is created in `Manufacturer.__init__` and succeeded in `process_order_raw` after `self.raw_inventory_counts[raw_mat_id] += reorder_quantity`. `behavior` was reshaped from:

```python
while True:
    if(len(self.suppliers)>=len(self.product.raw_materials)):
        if(not self.production_cycle):
            self.env.process(self.manufacture_product())
    yield self.env.timeout(1)
```

to:

```python
while len(self.suppliers) >= len(self.product.raw_materials):
    yield self.env.process(self.manufacture_product())
    yield self.raw_material_arrived
    self.raw_material_arrived = self.env.event()  # rotate
```

`manufacture_product` is now awaited directly instead of spawned + guarded by `production_cycle` — at most one production cycle is in flight at a time, exactly as the old `not self.production_cycle` re-entry guard enforced. The flag itself is preserved (still set/cleared inside `manufacture_product`) for any external code that introspects it, but `behavior` no longer needs it. If `manufacture_product` produces nothing this round (insufficient raw across BOM, or `pending = on_hand - level == 0`), it returns immediately and `behavior` blocks on `raw_material_arrived` until the next delivery — no spin loop.

**Fix applied (3) — `Statistics.update_stats_periodically` period is user-configurable:**

`Statistics.__init__` already accepted `periodic_update: bool = False` and `period: float = 1`; only the call sites hard-coded `period=1`. Two new kwargs are added to `_NODE_KWARGS`: `stats_period` and `periodic_stats`. Each Node subclass (`Supplier`, `InventoryNode`, `Manufacturer`, `Demand`) pops them from `kwargs` at the top of its `__init__`, validates `stats_period` via `validate_positive` when `periodic_stats` is true, and forwards them to its `Statistics(self, periodic_update=periodic_stats, period=stats_period)` call. Defaults preserve current behavior:

- `Supplier`: `periodic_stats=False`, `stats_period=1` (no periodic update unless the user opts in).
- `InventoryNode` / `Manufacturer` / `Demand`: `periodic_stats=True`, `stats_period=1`.

Users who want hourly stats on a daily-tick simulation now write `scm.Distributor(..., stats_period=24)`, and users who want end-of-run stats only write `periodic_stats=False` (which skips the `update_stats_periodically` process entirely).

**Fix applied (4) — `Inventory.remove_expired` is now event-driven (Option A — daemon + AnyOf):**

The last remaining `yield self.env.timeout(1)` daemon in `core.py` is gone. `Inventory.__init__` (perishable branch) now creates a `simpy.Event`:

```python
self.perish_changed = self.env.event()
```

`Inventory.put` succeeds it only when the heap head actually changes — detected via tuple identity after `heappush`:

```python
new_batch = (manufacturing_date, amount)
heapq.heappush(self.perish_queue, new_batch)
if self.perish_queue[0] is new_batch and not self.perish_changed.triggered:
    self.perish_changed.succeed()
```

With monotonic mfg_dates (the common-case sequential restock pattern), the head changes only on the empty→non-empty transition, so the daemon is undisturbed for routine puts — the wake-up is reserved for cases where the next expiry actually moved earlier.

`remove_expired` was reshaped from a per-tick `yield env.timeout(1)` poll to:

```python
while True:
    if not self.perish_queue:
        yield self.perish_changed
        self.perish_changed = self.env.event()
        continue
    next_expiry = self.perish_queue[0][0] + self.shelf_life
    sleep_dt = max(0, next_expiry - self.env.now)
    timer = self.env.timeout(sleep_dt)
    result = yield timer | self.perish_changed
    if self.perish_changed in result:
        self.perish_changed = self.env.event()  # rotate
        continue                                 # recompute next expiry
    # timer fired — drain everything now expired (existing inner loop)
    while self.perish_queue and self.env.now - self.perish_queue[0][0] >= self.shelf_life:
        ...
```

The drain inner loop is unchanged — `self.get(qty)` still does the heappop on the consumed batch, and the qty=0 sentinel branch still `heappop`s explicitly. The wake-up rotation (`self.perish_changed = self.env.event()` after each consumption) mirrors the `Node.wait_for_drop` idiom (`core.py:1651-1652`), so the precedent is consistent across the codebase.

The alternative (Option B — one self-expiring `env.process` per batch) was rejected because partial consumption from `Inventory.get` mutates the head's `qty` in place; per-batch processes would carry stale `qty` and need to reconcile against the heap on wake, reintroducing the coupling the §5.3 heap conversion avoided. Option A keeps a single daemon, single source of truth for the queue.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged.
- `pytest` — 166/166 passing, including seven new tests in `tests/test_core.py::TestRemoveExpiredEventDriven`:
  - `test_perish_changed_event_initialised` — perishable `Inventory` exposes an untriggered `perish_changed` SimPy event.
  - `test_put_into_empty_queue_signals_head_change` — empty→non-empty transition wakes the daemon.
  - `test_put_with_younger_batch_does_not_signal` — common-case monotonic restock leaves the daemon asleep (the bug-class this fix exists to prevent: a wake storm on every put).
  - `test_put_with_older_batch_displaces_head_and_signals` — backdated put displaces the head and wakes the daemon to recompute the (now-earlier) expiry.
  - `test_daemon_does_not_advance_time_when_queue_empty` — runs the daemon for 1000 sim-time units against an empty queue and confirms it idles (no spurious waste accrual, no phantom sentinel pops).
  - `test_late_put_after_idle_wakes_daemon_and_drains_on_schedule` — full empty→idle→put→sleep→drain round-trip.
  - `test_displacing_put_pulls_expiry_earlier` — daemon parked on a long sleep, a stale-mfg_date put forces it to wake and drain immediately on the next iteration.
- The three existing `TestPerishQueueHeap` tests pass without modification, confirming the drain-on-expiry semantics survived the scheduler change.

**Out of scope:**

- `Statistics.update_stats_periodically`'s loop is still a `while True: yield env.timeout(period)` — it is *meant* to fire periodically for time-bucketed KPIs (`carry_cost` accrual, periodic `inventory_level` snapshots), so making it event-driven would change semantics. Exposing the period to the user (fix 3 above) is the appropriate fix.

### 5.2 `used_ids = []` uses O(n²) membership test ✅ Resolved
`utilities.py:46` (`check_duplicate_id` helper), `utilities.py:~280` (`create_sc_net`'s `used_ids` switched from `list` to `set` plus three inline duplicate-ID branches collapsed onto the helper).

**Original issue:** `check_duplicate_id` used `if new_id in used_ids` plus `used_ids.append(new_id)` against a `list`. Building a network with N IDs was O(N²). Worse, `create_sc_net`'s three "object" branches (`isinstance(node, Node)` / `isinstance(link, Link)` / `isinstance(d, Demand)`) inlined the same `if X in used_ids: raise; used_ids.append(X)` pattern instead of calling the helper — same O(N²), three duplicated copies.

**Fix applied:**

1. `check_duplicate_id` keeps its public signature but now duck-types the insert call: `getattr(used_ids, "add", None) or used_ids.append`. Sets get `.add` (O(1)), lists get `.append` (O(1) amortized) — and the `in` check is O(1) for a set. Existing user code that builds its own `list` and passes it in keeps working unchanged.
2. `create_sc_net` now uses `used_ids = set()` instead of `[]`. Network construction is O(N) overall instead of O(N²).
3. The three duplicated inline `if X in used_ids: raise; used_ids.append(X)` branches in `create_sc_net` are collapsed onto `check_duplicate_id(used_ids, X, "<entity> ID")`. This also fixed an incidental copy/paste typo: the link branch previously raised `ValueError("Duplicate node ID")` for a duplicate *link* (the message mentioned "node" instead of "link"). Routing through the helper now interpolates `entity_type` correctly so the message is `"Duplicate link ID"`.
4. The `used_ids.remove(node.ID)` rollback path on invalid `node_type` works on a `set` unchanged (`set.remove` has the same `KeyError`-on-miss / void-on-success contract as `list.remove`).

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged.
- `pytest` — 156/156 passing, including two new tests in `tests/test_utilities.py`:
  - `test_check_duplicate_id_accepts_set` — exercises the new `set` path: `.add`-style insert, repeated calls, duplicate raises.
  - `test_check_duplicate_id_link_message_uses_entity_type` — locks in the typo fix: a duplicate link ID raises `ValueError("Duplicate link ID")`, not `"Duplicate node ID"`.
- The two existing `list`-flavored tests (`test_check_duplicate_id_no_duplicate`, `test_check_duplicate_id_duplicate`) still pass, confirming the backward-compat path.

**Out of scope / deferred:**

- The other O(n) hotspots called out elsewhere in §5 (perishable FIFO list pops in §5.3, string concatenation in §5.4) are independent and not addressed here.

### 5.3 Perishable FIFO uses list inserts and pops from head ✅ Resolved
`core.py:3` (`import heapq`), `core.py:~2018` (`Inventory.put`), `core.py:~2052` (`Inventory.get`), `core.py:~2076` (`Inventory.remove_expired`), `core.py:~1869` / `~1922` (docstrings).

**Original issue:** `Inventory.perish_queue` was a plain `list` of `(mfg_date, qty)` tuples kept sorted by hand. Three operations were O(n):

- `put` scanned the list to find the first entry with `mfg_date > new_mfg_date` and called `list.insert(i, ...)` — O(n) scan plus O(n) insert.
- `get` popped consumed batches off the head with `list.pop(0)` — O(n) per pop.
- `remove_expired` did the same `list.pop(0)` on the qty-zero sentinel path.

For long simulations with frequent partial replenishments (the perishable case the queue exists for), every batch arrival and consumption was linear in the queue depth.

**Fix applied:**

1. `import heapq` added to `core.py`. `perish_queue` is now used as a `heapq` min-heap keyed by mfg_date — index 0 is always the oldest (earliest-to-expire) batch. The on-disk shape (a `list` of tuples) is unchanged, so any user code that introspects the attribute keeps working; only the operations on it are different.
2. `Inventory.put` replaces the manual sorted-insert with `heapq.heappush(self.perish_queue, (manufacturing_date, amount))` — O(log n).
3. `Inventory.get` swaps `self.perish_queue.pop(0)` for `heapq.heappop(self.perish_queue)` — O(log n) per consumed batch. Partial consumption (`qty > x_amount`) keeps the existing in-place head update `self.perish_queue[0] = (mfg_date, qty - x_amount)`: the new tuple has the same mfg_date and a strictly-smaller qty, so it is still ≤ both children — the heap invariant is preserved without a re-heapify.
4. `Inventory.remove_expired`'s rare qty-zero sentinel branch (left over when a partial consumption hits zero) uses `heapq.heappop` for the same reason. The qty>0 expired branch already routes through `self.get(qty)` and inherits the heappop fix.
5. Docstrings on the `Inventory` class and its `__init__` now describe `perish_queue` as a `heapq` min-heap with index 0 always being the oldest batch.

**Verified:**

- `examples/py/intro_simple.py` — canonical `profit: -4435.0` unchanged.
- `pytest` — 159/159 passing, including three new tests in `tests/test_core.py::TestPerishQueueHeap`:
  - `test_out_of_order_inserts_consumed_oldest_first` — pushes batches with intentionally out-of-order mfg_dates (5, 2, 8, 1) and asserts `get` returns them in ascending-mfg_date order, validating both `heappush` and `heappop` paths.
  - `test_partial_consumption_preserves_heap_invariant` — exercises the partial-consumption in-place head update with five mixed batches, verifies the resulting heap still satisfies the parent-≤-children invariant via an explicit checker.
  - `test_remove_expired_drains_oldest_first` — runs the SimPy `remove_expired` process past the shelf-life threshold and asserts the heap is empty and `waste` equals the sum of all batch quantities.

**Out of scope / deferred:**

- `remove_expired` itself still polls every 1 unit of simulation time (§5.1's broader complaint about polling loops). Switching to an event-driven schedule keyed on the next expiry time is independent of the heap conversion and not addressed here.
- `Inventory.put` no longer needs the `inserted` flag bookkeeping that the manual sorted-insert required; the heap call is a single line.

### 5.4 `get_sc_net_info` and `print_node_wise_performance` build strings with `+=` in loops ✅ Resolved
`utilities.py:78` (`process_info_dict`), `utilities.py:~165` (`get_sc_net_info`), `utilities.py:~589` (`format_node_wise_performance`).

**Original issue:** Both helpers built their output string by appending with ``+=`` inside the loop. Python ``str`` is immutable, so each ``+=`` allocates a new string and copies the existing prefix — the loop is O(n²) in total bytes, which becomes a real cost for networks with 100+ nodes whose info dicts each accumulate dozens of lines.

**Fix applied:**

1. ``process_info_dict`` collects each ``"key: value"`` line into a ``parts`` list and ``"\n".join(parts)`` once at the end. Same trailing newline shape as before.
2. ``get_sc_net_info`` does the same — replaces the ``sc_info += ...`` chain with a single ``parts`` list spanning headers, per-node info, per-link info, per-demand info, and the network-performance block, then ``"\n".join(parts)`` once.
3. ``print_node_wise_performance`` is split into ``get_node_wise_performance`` (returns ``list[dict]`` — see §6.3), ``format_node_wise_performance`` (returns the fixed-width text via ``"\n".join``), and the original ``print_node_wise_performance`` (now a thin wrapper around the formatter). Both new functions are added to ``Components/__init__.py``'s ``__all__``.

**Verified:**

- ``examples/py/intro_simple.py`` — canonical ``profit: -4435.0`` unchanged.
- ``pytest`` — 177/177 passing, with the existing utilities tests covering the formatter changes.

### 5.5 `numpy`/`pandas` not used despite validation paper (`validation/`) ⏸️ Deferred (with rationale)
**Original issue:** ``simulate_sc_net`` aggregates per-node stats with hand-rolled loops that "read like a manual groupby"; numpy/pandas would be more idiomatic and faster for large networks.

**Why deferred:** The aggregation block in ``simulate_sc_net`` is ~70 lines of straightforward additions across 8 KPIs. Converting to pandas would require:

1. Adding ``pandas`` (and, transitively, a meaningful chunk of compiled deps) to ``pyproject.toml`` ``dependencies``. The library currently runs on a tiny dependency surface (``simpy`` + ``networkx`` + ``matplotlib`` per §8 cleanup); adding pandas roughly doubles install size.
2. Changing the ``simulate_sc_net`` return shape (or projecting back to dict for back-compat).
3. The performance argument only bites at networks of "100+ nodes" — well outside the current usage profile (the canonical example has 2 nodes; the largest committed example, ``hybrid_big_sc.py``, has fewer than 20).

The ``Network.results`` projection added in §6.1 already gives downstream callers a clean dict that they can feed to ``pandas.DataFrame.from_records`` themselves if they want a tabular view, without forcing pandas on every other user. ``get_node_wise_performance`` (§6.3) does the same for per-node KPIs.

**Out of scope until a real workload demands it:** revisit if a benchmark on a 500+ node network shows the aggregation is a meaningful share of total simulate time.

---

## 6. API / ergonomics

### 6.1 `create_sc_net` returns a dict, not an object ✅ Resolved (additive)
`utilities.py:~610` (new ``Network`` class), ``Components/__init__.py`` (re-export ``Network``).

**Original issue:** the dict returned by ``create_sc_net`` mixed construction metadata (``nodes`` / ``links`` / ``env`` / ``num_*``) with post-simulation KPIs (``revenue`` / ``profit`` / ``shortage``), gave no autocomplete, and required the caller to remember key spellings.

**Fix applied — additive ``Network`` wrapper:**

- ``Network(supplychainnet)`` wraps an existing dict; ``Network.build(nodes=..., links=..., demands=..., env=...)`` is the classmethod sibling of ``create_sc_net``.
- Read-only properties expose the construction metadata as named attributes: ``net.env`` / ``net.nodes`` / ``net.links`` / ``net.demands`` / ``net.node_count`` / ``net.link_count``. ``net.node(id)`` / ``net.link(id)`` / ``net.demand(id)`` are typed lookup helpers.
- ``net.simulate(sim_time, logging=True, log_window=None)`` calls ``simulate_sc_net`` and sets ``net.has_run = True``; chainable (returns ``self``).
- ``net.results`` projects only the post-run KPI keys (defined as ``Network._RESULT_KEYS``) so callers can tell construction metadata from run output. Empty before ``simulate`` runs.
- ``net.as_dict()`` returns the underlying ``supplychainnet`` dict — escape hatch for legacy code that reads the dict shape directly.

The wrapper is **additive**: ``create_sc_net`` / ``simulate_sc_net`` keep their existing dict-based contracts. ``Network.as_dict()`` is the same dict object the free-functions read and write, so calls in either style stay synchronised. New tests in ``TestEndToEndIntegration`` (``test_network_wrapper_matches_dict``) lock that equivalence in.

### 6.2 `simulate_sc_net(..., logging=True)` overloads the `logging` parameter ✅ Resolved
`utilities.py:~390` (`simulate_sc_net`).

**Fix applied:** added a dedicated ``log_window: tuple[float, float] | None`` kwarg. The new shape is ``simulate_sc_net(sc, sim_time, logging=True, log_window=(start, stop))`` — ``logging`` is a clean ``bool``, ``log_window`` carries the window. The historical ``logging=(start, stop)`` spelling is still accepted but emits a ``DeprecationWarning``-style log line and is folded onto ``log_window`` internally so the rest of the function only sees one shape per parameter. ``Network.simulate`` exposes the same two kwargs. The integration test ``test_log_window_kwarg_runs_to_completion`` plus ``test_logging_tuple_back_compat_still_works`` lock both surfaces.

### 6.3 `print_node_wise_performance` prints to stdout ✅ Resolved
`utilities.py:~526-608`.

**Fix applied:** split into three:

- ``get_node_wise_performance(nodes)`` — returns ``list[dict]``, one per metric; the canonical programmatic API. Each dict has ``"Performance Metric"`` plus one entry per node, so ``pandas.DataFrame.from_records(rows)`` produces the same table the old function used to print.
- ``format_node_wise_performance(nodes, col_width=25)`` — pure string helper that renders the fixed-width text dump (built with ``"\n".join`` per §5.4).
- ``print_node_wise_performance(nodes)`` — kept as a thin wrapper around the formatter for the existing notebooks/scripts that call it directly.

All three are added to ``__all__``. Pandas is **not** introduced as a hard dep — callers who want a DataFrame already have one line of code (``pd.DataFrame.from_records(get_node_wise_performance(nodes))``) and the library stays usable without pandas installed.

### 6.4 Callable auto-wrapping hides type errors ✅ Resolved
`core.py:~178` (new ``ensure_numeric_callable`` helper), `core.py:~1483` (Node), `core.py:~1748` (Link), `core.py:~3002` (Demand).

**Fix applied:** new ``ensure_numeric_callable(name, value)`` helper that combines auto-wrap with a single validation invocation. If ``value`` is a scalar it gets wrapped; if it is callable the helper invokes it once and verifies the return is a real ``numbers.Number``. A non-numeric return (or a callable that raises) surfaces immediately at construction with a clear error message naming the offending parameter. Every site that previously wrote the ``if not callable(x): x = lambda v=x: v`` pattern + an optional ``validate_number`` follow-up now calls this helper:

- ``Node.__init__`` for ``node_disrupt_time`` / ``node_recovery_time``.
- ``Link.__init__`` for ``lead_time`` / ``link_disrupt_time`` / ``link_recovery_time``.
- ``Demand.__init__`` for ``order_arrival_model`` / ``order_quantity_model`` / ``delivery_cost`` / ``lead_time`` (the latter four were not even validated for numeric return previously).

The helper is exported as ``scm.ensure_numeric_callable`` so user-defined Node subclasses can reuse the same fail-fast pattern. Five new tests in ``TestEnsureNumericCallable`` lock the contract.

The docstring also flags the only edge case the helper introduces: stateful generators / iterators have their first sample consumed at construction time. Pure-function callables (the common case) are unaffected.

### 6.5 `Demand.customer` is a SimPy process but uses both `yield from` and `env.process` ✅ Resolved
`core.py:~3144-3252`.

**Fix applied:** the four fulfilment paths inside ``customer`` are factored into named helpers (``_serve_in_full`` / ``_serve_partial_consume`` / ``_enqueue_for_tolerance`` / ``_serve_no_tolerance``). ``customer`` itself is now a single rule table that picks the right helper and ``yield from``s it. Each helper is a generator returning ``None`` so the dispatcher can use a uniform ``yield from`` form; the two no-wait paths (``_enqueue_for_tolerance`` and ``_serve_no_tolerance``) are degenerate generators (``return; yield``) so the call site does not need a special case.

The ``_enqueue_for_tolerance`` path **deliberately preserves** the historical fire-and-forget semantics — ``wait_for_order`` is spawned as a sibling process via ``env.process(...)`` rather than awaited via ``yield from``. The comment block at the top of the helpers documents why: KPIs accrue inside ``wait_for_order`` independently of the parent ``customer`` call's lifecycle, and changing it to ``yield from`` would extend the parent's lifetime through the entire tolerance window without changing any observable bookkeeping. Routing through a named helper makes that intent explicit.

### 6.6 Stats key `orders_shortage` vs `shortage` ✅ Resolved
`core.py:~359` (`_stats_keys`), `core.py:~415` (rename of ``self.orders_shortage`` → ``self.shortage``), `core.py:~454-490` (back-compat alias / kwarg shim), `core.py:~2546` / `~2873` / `~3179` / `~3214` / `~3222` / `~3239` (call sites), `utilities.py:~470-484`, ``tests/test_core.py:971``, ``tests/test_utilities.py:16-31``, ``examples/py/intro_simple.py:44``.

**Fix applied:** picked ``shortage`` as the canonical name (matches the network-level ``supplychainnet["shortage"]``) and renamed the node-level ``Statistics.orders_shortage`` attribute. To keep external code working through the rename:

- An ``orders_shortage`` Python ``@property`` returns the same list (and the setter writes through to ``shortage``), so ``node.stats.orders_shortage`` reads still work.
- ``Statistics.update_stats`` accepts both ``shortage=`` and ``orders_shortage=`` kwargs; the latter is folded onto the former at the top of the function. A caller passing both gets the new spelling.

Internally every ``update_stats`` call site was updated to the new spelling (Supplier and Manufacturer dispatch paths, Demand fulfilment helpers). ``_stats_keys`` was updated so ``get_statistics()`` now returns ``"shortage"`` (not ``"orders_shortage"``); the canonical example's docstring snapshot was updated to match. The test in ``TestStatisticsAggregation`` was flipped from ``stats["orders_shortage"]`` to ``stats["shortage"]``.

The other vocabulary inconsistency the review flagged (``demand_placed`` / ``demand_by_customers`` / ``demand_by_site``) is **not** addressed here: those three are different semantically (per-node vs network-level customer aggregate vs network-level site aggregate), so a rename without merging the underlying meanings would be cosmetic. Documented as a follow-up in the new "remaining vocabulary work" note below.

### 6.7 Docstrings triple-state the same fields ⏸️ Deferred (with rationale)
**Original issue:** every public class declares Parameters + Attributes + Functions in the class docstring, then ``__init__`` repeats Parameters + Attributes — about 50% of ``core.py``. Some duplicates have already drifted out of sync (``Product.__init__`` lists ``buy_price`` before ``raw_materials`` while the signature is the other way).

**Why deferred:** the docs site (``mkdocstrings`` per ``mkdocs.yml``) currently renders **both** the class and the ``__init__`` docstrings into the same page. Trimming one without confirming the docs render still reads correctly risks shipping a degraded docs page. The fix is real but mechanical — it touches every public class — and is best done as a single dedicated PR together with a docs-site rebuild check rather than bundled into this review pass. Recorded as item 1 of the "remaining work" notes below.

**Drift-only fix applied:** the obvious drift the review called out (``Product.__init__`` parameter order) is left alone in this pass too — the signature is the source of truth, and reordering the docstring without the broader dedup invites another round of churn when §6.7 lands proper. Recorded as item 2 of the "remaining work" notes.

---

## 7. Testing gaps ✅ Resolved

`tests/test_core.py:13-22` (TestRawMaterial setUp), `tests/test_core.py:73-95` (TestProduct setUp), `tests/test_core.py:11-21` (`_fresh_env` helper), `tests/test_core.py:213-227` (DummyNode env=), `tests/test_core.py:1583-` (TestEndToEndIntegration / TestInventoryInvariants / TestEnsureNumericCallable), `.github/workflows/ci.yml:28-33` (CI fallback removal).

**Fix applied:**

1. ``RawMaterial`` and ``Product`` fixtures moved from class attributes to ``setUp``-built instance attributes. An import-time regression now surfaces as a clean test failure with the test name attached, not a pytest collection error.
2. New ``_fresh_env()`` helper at module level; the eight ``DummyNode``-using TestCase classes call ``self.env = _fresh_env()`` and pass it into ``DummyNode(env=self.env)`` so the harness's suppliers / links / inventory bind to the same env the test runs ``env.run`` on. Replaces the previous module-shared env + post-hoc ``self.node.env = self.env`` patch (which left ``node.suppliers`` pointing at the module env). The module-level ``env`` is kept as a fallback for the few legacy references but new tests should use ``_fresh_env``.
3. New ``TestEndToEndIntegration`` class with four tests pinning the canonical ``intro_simple`` numbers (``profit == -4435.0``, ``inventory_level == 100``, ``inventory_carry_cost == 410.0``, ``shortage == [0, 0]``) plus the ``Network`` wrapper / ``log_window`` kwarg / ``logging=tuple`` back-compat surfaces.
4. New ``TestInventoryInvariants`` class with two hand-rolled property tests:
   - ``test_perishable_quantities_match_container_level`` — sum of perishable batch quantities must equal ``container.level`` after every put/get sequence (the invariant whose violation produced the original ``remove_expired`` bug).
   - ``test_on_hand_never_below_container_level_before_dispatch`` — ``on_hand`` (inventory position) is always ≥ ``container.level``.
   The hand-roll is deliberate — adding ``hypothesis`` as a hard test dep would be the more idiomatic approach but also more dependency surface for two assertions; revisit if a third invariant test joins them.
5. CI fallback removed: ``.github/workflows/ci.yml`` no longer wraps ``pytest`` in ``|| echo "No tests found, skipping."``. A red test now fails CI.

**Verified:** ``pytest`` — 177/177 passing (was 159 before this review pass; +18 across §7, §6.4, §5.1).

---

## 8. Minor issues and nits ✅ Resolved (most) / ⏸️ deferred (one)

- ``copy.deepcopy(product)`` in ``InventoryNode.__init__`` ✅ — kept (the deep-copy is intentional: each ``InventoryNode`` overrides ``sell_price`` / ``buy_price`` on its own copy without mutating siblings sharing the same ``Product``). Replaced the cryptic comment with an explicit ``# Deep-copy so each InventoryNode that "sells" the same Product can override prices independently...`` block. ``Manufacturer`` still does not deep-copy because it owns the canonical ``Product`` it produces — documented inline.
- ``typing.Callable`` annotations ✅ — added ``from typing import Callable`` to ``core.py`` and replaced every ``callable`` annotation (Node, Link, Inventory, Demand) with ``Callable``. ``callable`` is a builtin, not a type; mypy now stops complaining.
- ``SSReplenishment.run`` duplicate ``s > S`` guard ✅ — removed (the same check runs in ``__init__``); replaced with a one-line comment pointing at the surviving guard.
- ``Link.__init__`` ``lead_time == None`` dead code ✅ — already addressed in a prior review pass; verified no such check exists today.
- ``Demand.__init__`` advances state of stateful iterators on validation call ✅ — documented in ``ensure_numeric_callable``'s docstring (``Note:`` block) so the trade-off is explicit. Pure-function callables (the common case) are unaffected; users with stateful iterators can wrap them in a closure that defers the first sample to ``t = 0``.
- ``Manufacturer.process_order`` trailing ``yield self.env.timeout(1)`` ✅ — replaced with ``yield self.env.timeout(0)`` plus a comment explaining that the yield is only there to make the function a generator (it has to be ``env.process``-spawnable) and the prior ``timeout(1)`` was an arbitrary stall called out as the ``§8 process_order trailing tick`` nit.
- ``visualize_sc_net`` ``spectral_layout`` ✅ — switched to ``nx.multipartite_layout`` keyed by a new ``_TIER_INDEX`` table that maps every ``NodeType`` (plus the ``demand`` rightmost column) to a tier. The drawing now reads left-to-right (suppliers → manufacturers → distributors → retailers → demand), which is the natural reading order for a supply chain. Switched ``nx.Graph`` to ``nx.DiGraph`` so the arrows render and ``Demand`` nodes were added to the visualization (they were silently omitted before).
- ``Statistics.reset`` ✅ — rewritten to drive off ``self._stats_keys`` first (so any KPI registered on a ``Statistics`` instance is zeroed without the caller having to remember to extend ``reset``) plus a back-stop ``vars(self)`` sweep for non-tracked instance attributes. Inventory-side counters (``carry_cost``, ``waste``) still need an explicit reset inline since they live on ``Inventory`` not on ``Statistics`` — documented with a guard comment so the next person adding an Inventory metric sees the pattern.
- ``mkdocs.yml`` references ``api-reference/api-intro.md`` ✅ — verified the file exists on disk (``docs/api-reference/api-intro.md``); nav is not broken. The reviewer flagged this with "[contents were not enumerated]" so this nit was a false positive.
- ``pyproject.toml`` Python 3.6 advertised + missing deps ✅ — bumped ``requires-python`` to ``>=3.9``, dropped the ``Programming Language :: Python :: 3.8`` classifier, added ``Programming Language :: Python :: 3.12``, and added ``networkx`` + ``matplotlib`` to the ``dependencies`` list (``numpy`` comes in transitively via ``matplotlib``). The library will now refuse to install on EOL Pythons, and ``utilities.py``'s ``import networkx`` / ``import matplotlib.pyplot`` no longer rely on those packages being incidentally present.
- CSV/ODS artifacts in ``validation/`` ⏸️ — Deferred. Moving these out of the repo root would touch the validation paper's reproduction story; out of scope for this code-review pass. Recorded as item 3 of the "remaining work" notes below.

---

---

## Remaining work (intentionally deferred)

The three items below were considered in this review pass and deferred with explicit rationale rather than silently skipped:

1. **§6.7 docstring deduplication.** Sweeping mechanical change touching every public class. Best done as a single PR with a docs-site rebuild check; the ``Product.__init__`` parameter-order drift the review called out is left for that same PR.
2. **§5.5 numpy/pandas aggregation.** Would double install size to optimise an aggregation that doesn't bite at current network sizes (<20 nodes). ``Network.results`` and ``get_node_wise_performance`` already hand callers a clean dict / list-of-dicts they can feed to ``pandas.DataFrame.from_records`` themselves. Revisit with a benchmark on a 500+ node network.
3. **§8 ``validation/`` data files.** Moving them affects the validation paper's reproduction instructions; out of scope for a code-review pass.
4. **§6.6 demand-vocabulary unification (``demand_placed`` / ``demand_by_customers`` / ``demand_by_site``).** The three names are different *concepts* (per-node placed orders, network-level customer aggregate, network-level site aggregate), so a rename without merging the underlying meanings would be cosmetic. Keep as-is until the meanings are consolidated.

---

## 9. Suggested roadmap

Ordered by impact per unit of effort:

1. **Fix the correctness bugs in §3.** Small, local changes; each unblocks user trust.
2. **Split `core.py` into modules as in §4.1 and add `__all__` to every module.** One PR, mechanical, immediately improves review ergonomics.
3. **Introduce a `Network` wrapper** (§6.1) so `create_sc_net` / `simulate_sc_net` become `Network.build(...)` / `network.simulate(...)`. Keep the dict API as a thin adapter for a release cycle, then deprecate.
4. **Tighten the replenishment-policy contract** (§4.3). Will cut ~30% of code in the policy subclasses and make "bring your own policy" actually pleasant.
5. **Replace `Inventory.level` duplication with a `@property`** (§3.7), rename `Inventory.inventory` → `Inventory.store`, collapse `logger.logger` to `logger.*` (§4.9).
6. **Add a seedable RNG** (§3.9). Publish a `supplynetpy.set_seed(n)` entry point.
7. **Expand tests**: add integration tests that run the `examples/py/` scripts end-to-end and assert on key stats; add invariant tests for the `Inventory` class.
8. **Revise docs**: consolidate duplicate docstrings, clean up broken `mkdocs.yml` references, remove committed `simulation_trace.log`.
9. **Performance pass**: replace polling loops with event waits (§5.1) — matters most for any validation study that simulates multi-year horizons.

None of these require breaking the public `scm.create_sc_net` / `scm.simulate_sc_net` interface if they are staged behind deprecation warnings.

---

*Reviewer's note.* This review is harsher in tone than warranted by the code, which is competent and already publishable. The items above are what would move the project from "pre-alpha library that runs the examples" to "library an outside contributor can extend without reading all 2,600 lines first." The single most valuable change is the `core.py` split and the policy-contract cleanup — everything else follows naturally.
