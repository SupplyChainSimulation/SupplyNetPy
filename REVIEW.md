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

### 4.3 Replenishment and selection policies require privileged knowledge of the node
Every subclass of `InventoryReplenishment.run` directly manipulates:

- `self.node.logger.logger.info(...)`
- `self.node.inventory.inventory.level`
- `self.node.inventory.on_hand`
- `self.node.stats.backorder[1]`
- `self.node.ongoing_order`
- `self.node.selection_policy.select(qty)`
- `self.env.process(self.node.process_order(...))`
- `self.node.inventory_drop`

A user writing a new policy has to re-discover this whole contract. Define the contract explicitly on `Node`, e.g.:

```python
class Node:
    def position(self) -> float: ...         # on_hand - backorder[1]
    def place_order(self, quantity) -> None: # wraps selection + process_order
    def wait_for_drop(self) -> Event: ...
```
and have the policies speak only in those terms. The current `SSReplenishment.run` shrinks to ~10 lines.

Similarly, `SelectAvailable.select` reaches into `source.inventory.inventory.level`. A `supplier.available_quantity()` method on the `Link` (or `Supplier`) would hide that.

### 4.4 `Link.__init__` mutates the sink node (`self.sink.suppliers.append(self)`)
`core.py:1425`

This is a side-effect in a constructor. It couples `Link` to the internal shape of `InventoryNode` / `Manufacturer`, and it is the reason `Node` objects need a `suppliers` attribute even though `Node` itself does not declare one. A user who constructs a plain `Node` (e.g. demand) as a link sink hits `AttributeError`.

**Fix:** move link-registration into `create_sc_net` (or a dedicated `Network.add_link()`), and stop relying on mutation from peer objects.

### 4.5 Two construction styles, silently incompatible
`create_sc_net` accepts a mix of dicts and objects for nodes/links/demands, but only the first element is checked for type to decide whether `env` is required (`utilities.py:167`). A list where `nodes[0]` is a dict but `nodes[1]` is an object will:

- Skip the "env required" check, creating a fresh environment.
- Then `isinstance(node, Node)` branch runs with that fresh env, and the object's original env (if different) is ignored.

Either require all-or-nothing, or loop and validate consistently.

### 4.6 `_info_keys`/`_stats_keys` pattern is manual and duplicates fields
Every subclass does `self._info_keys = [...]` in `__init__` and then `self._info_keys.extend([...])` in subclass `__init__`. This is error-prone — it is easy to add an attribute and forget to list it. A declarative form at the class level would be sturdier:

```python
class Supplier(Node):
    _info_keys = Node._info_keys + ["raw_material", "sell_price"]
```
Or simply use `dataclasses.fields` / a `@info_field` decorator.

### 4.7 `node_type` is a string with magic values
`Node.__init__` validates against a hard-coded list of 9 strings, and `create_sc_net` dispatches via another hard-coded list. Add a new node type (e.g. `crossdock`) and you must edit both. An `enum.Enum` (`NodeType`) removes the lookup duplication and gives IDEs autocomplete.

### 4.8 Global state: `global_logger` and the simulation trace file
`core.py:7` and `logger.py:26` together create a file handler on `simulation_trace.log` *at import time*, in the current working directory. The committed `simulation_trace.log` in the repo root is the residue of that. Problems:

- Parallel simulations overwrite the same file (mode='w').
- Tests that import the module all blow that file away.
- The log file location is not configurable before import.

**Fix:** make logging opt-in (no file handler until `enable_logging(log_to_file=True)` is called explicitly), and route module-level errors through a `NullHandler` by default — which is the documented best practice for libraries (<https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library>).

### 4.9 `GlobalLogger` is not actually a logger
The pattern `self.node.logger.logger.info(...)` — `logger.logger` — appears hundreds of times. It signals the wrapper is not pulling its weight. Either:

- Make `GlobalLogger` a proper `logging.LoggerAdapter` (then users write `self.node.logger.info(...)`), or
- Drop the wrapper and use `logging.getLogger(...)` directly.

The current `log(self, level, message)` method that hard-codes a string-level dispatch is unnecessary; the `logging` module already has level constants.

### 4.10 `Inventory.inventory` naming
A class named `Inventory` whose main attribute is also `inventory` (and that `inventory` is actually a `simpy.Container`) creates four-dot accesses (`node.inventory.inventory.level`). Rename the container attribute to `_container` or `store`, expose a single `.level` property, and most of the noise goes away.

---

## 5. Performance / scaling concerns

### 5.1 Polling loops for "continuous" behaviors
- `Supplier.behavior` yields `timeout(1)` when full (`core.py:1825`) and again after mining (via `extraction_time`). For a 10-year simulation at day granularity, that is 3,650 timeouts per supplier even when nothing happens.
- `Manufacturer.behavior` yields `timeout(1)` every tick regardless of whether raw materials arrived.
- `Inventory.remove_expired` ticks every 1 unit (`yield self.env.timeout(1)`).
- `Statistics.update_stats_periodically` ticks every 1 unit.

Each of these should be event-driven (wait on `inventory_raised` / `inventory_drop` / the next expiry time) rather than polling.

### 5.2 `used_ids = []` uses O(n²) membership test
`utilities.py:176` — `used_ids.append(...)` plus `if new_id in used_ids` inside `check_duplicate_id`. Use a `set`.

### 5.3 Perishable FIFO uses list inserts and pops from head
`Inventory.put` uses `self.perish_queue.insert(i, ...)` (`core.py:1638`) and `get` uses `self.perish_queue.pop(0)` (`core.py:1670`). Both are O(n). Use `collections.deque` with `appendleft`/`popleft`, or keep the list sorted by expiry with `heapq`.

### 5.4 `get_sc_net_info` and `print_node_wise_performance` build strings with `+=` in loops
Minor, but for large networks a `"\n".join(parts)` is cleaner and faster.

### 5.5 `numpy`/`pandas` not used despite validation paper (`validation/`)
The aggregation in `simulate_sc_net` reads like a manual `groupby`. For networks with 100+ nodes, using NumPy arrays or a small pandas DataFrame for stats aggregation would simplify the code and speed it up significantly.

---

## 6. API / ergonomics

### 6.1 `create_sc_net` returns a dict, not an object
A `Network` class wrapping the dict would:

- Offer `.simulate(sim_time, ...)` instead of a free function.
- Provide typed getters: `network.node("D1")`, `network.stats`.
- Hide the implementation (`"num_of_nodes"` key vs `network.node_count`).
- Make autocomplete useful.

The dict also mixes construction metadata (`nodes`, `links`, `env`, `num_suppliers`) with simulation results (`revenue`, `profit`, `shortage`). Separate the two — a `network.results` attribute filled only after `simulate()`.

### 6.2 `simulate_sc_net(..., logging=True)` overloads the `logging` parameter
`utilities.py:295` checks `isinstance(logging, tuple)` and unpacks `(start, stop)`. `logging=True|False` is a different semantic than `logging=(3, 50)`. Make the windowed case a separate parameter (`log_window=(3, 50)`). Name-shadowing the stdlib `logging` module as a kwarg is also unfortunate.

### 6.3 `print_node_wise_performance` prints to stdout
A library should return a `DataFrame` (or a `dict`) and let the caller print it. `pd.DataFrame.from_records(...)` reads cleanly from the per-node stats dicts.

### 6.4 Callable auto-wrapping hides type errors
Many constructors accept either a number or a zero-arg callable and auto-wrap:
```python
if not callable(node_recovery_time):
    node_recovery_time = lambda val=node_recovery_time: val
```
This is convenient, but it also means passing a class (which is `callable`) silently becomes a callable returning a class — never a number. Log what was received and fail fast when the wrapped value is not numeric.

### 6.5 `Demand.customer` is a SimPy process but uses both `yield from` and `env.process`
`core.py:2583–2590` — sometimes the customer yields from `_process_delivery`, sometimes it spawns `wait_for_order` as a new process, sometimes it updates stats inline. The three paths have different latencies and different correctness properties. Factor them into named helpers with uniform semantics (all three return a `simpy.Event`).

### 6.6 Stats key `orders_shortage` vs `shortage`
`Statistics.orders_shortage` at the node level, `supplychainnet["shortage"]` at the network level. Pick one vocabulary and stick with it across the stack. Same for `demand_placed` / `demand_by_customers` / `demand_by_site`.

### 6.7 Docstrings triple-state the same fields
Every class's docstring lists Parameters + Attributes + Functions. Then `__init__` lists Parameters + Attributes again. That is ~50% of the file. Choose one location (the class docstring) and let `__init__` be brief. It also reduces drift — today some docstrings are already out of sync with the signatures (e.g. `Product.__init__` docstring lists `buy_price` before `raw_materials`, signature lists them the other way).

---

## 7. Testing gaps

- `tests/test_core.py` instantiates `RawMaterial` and `Product` as **class attributes**. Their validation runs at import time, so an import-time regression surfaces as a collection error rather than a named test failure.
- Shared module-level `env = simpy.Environment()` and `inventory = simpy.Container(...)` leak state between tests; use fixtures with `scope="function"`.
- There are no integration tests for `create_sc_net` → `simulate_sc_net` → aggregated results. The examples in `examples/py/` are the closest, but they are not executed by pytest.
- No property-based tests for inventory invariants (`level + sum(perish_queue_qty) == container.level`, `on_hand >= container.level`, etc.) — which would have caught the `remove_expired` bug.
- `.github/workflows/ci.yml` falls through with `pytest || echo "No tests found, skipping."` — a failing test does not fail CI. Remove the fallback.

---

## 8. Minor issues and nits

- `core.py` imports `copy` solely for one `copy.deepcopy(product)` call in `InventoryNode.__init__`. That deep-copy is a surprise — it prevents sharing a `Product` across nodes from being a shared reference, but only sometimes (manufacturers don't deep-copy). Document or unify.
- `typing.Callable` should replace `callable` in annotations. `callable` is a builtin function, not a type; mypy will flag every usage.
- `SSReplenishment.run` checks `s > S` (line 616) after `super().__init__` already performed the same check at line 593 — duplicate guard.
- `Link.__init__` (line 1387) wraps `lead_time` into a callable, then one line later checks `lead_time == None`. After wrapping, it's a lambda — never None. The check is dead code.
- `Demand.__init__` validates `order_arrival_model()` by calling it once for validation (`core.py:2466`). For deterministic simulations this is benign, but for stateful iterators/generators it advances state before `t=0`.
- `Manufacturer.process_order` trailing `yield self.env.timeout(1)` (`core.py:2334`) is an arbitrary 1-unit tick for no documented reason.
- The CSV/ODS artifacts in `validation/` should live in a `data/` or be referenced from the README, not the repo root of a Python package.
- `visualize_sc_net` uses `nx.spectral_layout`, which often produces degenerate embeddings for small directed graphs. Consider `nx.multipartite_layout` keyed by tier (supplier → manufacturer → distributor → retailer → demand), which also reads more naturally for a supply chain.
- `Statistics.reset` only zeros numeric / list attributes (`isinstance(value, (int, float))`). `inventory_level` on `Statistics` is an `int`, but `node.inventory.carry_cost` and `node.inventory.waste` live on the Inventory — they are reset inline. Easy to forget when adding a new metric.
- `mkdocs.yml` references an `api-reference/api-intro.md` that doesn't appear to exist on disk (`docs/api-reference/` contents were not enumerated for this review). If that's right, the nav is broken.
- `pyproject.toml` advertises Python 3.6 support; the validation helpers use f-strings with `{x:.4f}` and pattern matching in several places — fine — but 3.6 has been EOL since 2021. Set `requires-python = ">=3.9"` and pin `networkx`, `matplotlib`, `numpy` (which `utilities.py` imports transitively via `matplotlib`) as explicit deps instead of relying on `simpy` alone.

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
