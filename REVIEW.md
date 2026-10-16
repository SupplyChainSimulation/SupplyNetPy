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

*Updated in §3.17:* both clamps now call `self.position()`, which subtracts only the units owed to waiting customers (orders from other sites are already taken off `on_hand`).

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

   *Corrected in §3.17:* `level <= on_hand` is not true while orders from other sites wait at the shelf, and the cap is now `on_hand - level + inventory.waiting_orders()`.

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

*Updated in §3.18: `ongoing_order_raw` has been removed. It stayed set until the delivery arrived, so it also blocked raw orders for later plans, leaving their units with no raw material. A `break` after the first working supplier now does the job it was meant for. The "sufficient raw inventory" early return in `process_order_raw` is gone too.*

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
2. `Manufacturer.process_order_raw`: same gate, placed before the shortage check and the `node_status == "active"` branch. Clears the per-raw-material `ongoing_order_raw[raw_mat_id]` flag and yields a 1-tick timeout so the outer loop in `process_order` can retry on the next cycle. *Updated in §3.18: the check moved to `Manufacturer.process_order`, before the planned units are added to `on_hand`, and covers the supplier site as well as the link. Checking only in `process_order_raw` left the planned units with no raw material.*
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

### 3.16 Probabilistic disruption (`failure_p`) busy-spins instead of polling per tick ✅ Resolved
`core.py:~1842` (`Node.disruption`), `core.py:~2117` (`Link.disruption`)

**Original issue (2026-05-07):** both disruption loops had the shape

```python
while True:
    if status == "active":
        if disrupt_time:
            yield env.timeout(disrupt_time())
            ...set inactive...
        elif rng.random() < failure_p:
            ...set inactive...
            yield env.timeout(1)
        # ← no else branch, no yield on the miss path
    else:
        yield env.timeout(recovery_time())
        ...set active...
```

When only `failure_p` was set and the rng draw *missed* (the common case for any small `failure_p`), neither the `if` nor the `elif` body executed. Control fell through to the next iteration of `while True` with simulation time **not advanced**, drawing the rng again immediately. Because Python's `random()` returns from `[0, 1)`, a sufficiently long tight loop will eventually land below any positive `failure_p` — so the node/link disrupted "almost certainly at `t=0`" regardless of how small `failure_p` was. `failure_p` did not behave as a per-tick probability at all; it behaved as a guarantee, with the only randomness being the wall-clock wait for Python to draw a small enough number.

In the *hit* branch, the `yield env.timeout(1)` was a separate (and minor) bug: after going inactive, the next iteration falls through to `else` and yields `recovery_time` — the extra 1-tick wait there only delayed recovery start by one unit.

**Fix applied:** restructured both loops into `if disrupt_time / else: <draw>; yield timeout(1)`. The probabilistic poll now yields one tick per draw whether or not it hit:

```python
if status == "active":
    if disrupt_time:
        yield env.timeout(disrupt_time())
        ...set inactive...
    else:
        if rng.random() < failure_p:
            ...set inactive...
        yield env.timeout(1)   # unconditional — one draw per tick
else:
    yield env.timeout(recovery_time())
    ...set active...
```

Both call sites carry an inline comment explaining why the yield is on the *outer* path of the probabilistic branch and not gated by the rng draw. Behavior of `disrupt_time` (timed disruption) is unchanged — that branch was already correct, and `intro_simple.py` only exercises the `disrupt_time` path indirectly via no-disruption defaults, so its `profit: -4435.0` baseline is untouched.

**Verified:**

- Canonical `examples/py/intro_simple.py` unchanged (`profit: -4435.0`).
- `pytest` — 202/202 passing (198 prior + 4 new).
- Four new regression tests in `tests/test_core.py`:
  - `TestNodeDisruptionProbabilisticIsTimePaced::test_misses_do_not_busy_spin_and_node_stays_active`: stubs `rng.random()` to always return `0.99` (strictly above `failure_p=0.01`). Without the fix, `env.run(until=20)` would never return — the loop would tight-spin in real wall time. With the fix, the run completes and the rng is drawn exactly 20 times (once per tick).
  - `TestNodeDisruptionProbabilisticIsTimePaced::test_hit_after_misses_flips_status_at_the_hitting_tick`: stubs the rng with the sequence `[0.9, 0.9, 0.001]`. Asserts the node remains `active` after `env.run(until=2)` and flips to `inactive` after `env.run(until=3)` — pinning the per-tick scheduling deterministically.
  - `TestLinkDisruptionProbabilisticIsTimePaced::test_misses_do_not_busy_spin_and_link_stays_active`: same shape against `Link.link_failure_p`.
  - `TestLinkDisruptionProbabilisticIsTimePaced::test_hit_after_misses_flips_status_at_the_hitting_tick`: same shape against `Link.link_failure_p`.

**Behavioral note for downstream users:** small `failure_p` values now actually produce small per-tick probabilities. Any user simulation tuned around the broken behavior will see different (much rarer) disruption frequency. The `validation/` numbers were not generated with `failure_p`-driven disruption (the cross-check uses scheduled `disrupt_time`, which lives on the `if disrupt_time` branch and was unchanged), so those still hold.

### 3.17 Orders between sites counted twice as backorders and never cleared; factories stop making what they owe ✅ Resolved
Reported in GitHub issue #1 (defects 1 and 2). `InventoryNode.process_order`, `Manufacturer.process_order_raw`, `Node.position`, `Manufacturer.manufacture_product`.

**Original issue.** When a warehouse ordered from a site that could not fill the order right away:

1. `Inventory.get` took the full order off the supplying site's `on_hand` straight away (the order then waits in SimPy's queue of requests until stock arrives), **and** `process_order` also added it to the site's `backorder`. `position = on_hand - backorder[1]` therefore subtracted the same units twice.
2. Nothing ever removed that backorder, so the site behaved as if its rule were (s + B, S + B) for the rest of the run. Example: a distributor holding 10 that owed a warehouse 50 saw a position of −90 instead of −40, ordered 100 instead of 50, and kept 50 extra units forever.
3. `Manufacturer.process_order_raw` had the same "add but never remove" pattern for a raw-material supplier's backorders. Suppliers have no reorder rule, so there it only made the reported numbers wrong.
4. Both backorders were recorded before the check that the supplying node is active, so a disrupted supplier, which takes no order, still kept one forever.

The double count also hid a second bug (defect 2). `manufacture_product` capped production at `on_hand - level` ("units still to make", see §3.11). Orders waiting at the factory's shelf have already been taken off `on_hand`, so this number is too small by exactly the amount the factory owes. A factory holding 10 that received an order for 50 decided there was nothing to make, and the order waited forever. It only worked before because the stuck backorder made the factory over-order.

**Fix applied:**

- **Backorders are live.** In both order methods, an order counts as a backorder at the supplying node only while it really waits: right after `inventory.get(...)`, `not event.triggered` means SimPy could not hand it out on the spot (the shelf is short, or an earlier request is ahead of it in line). It is removed once `yield event` returns. The whole order counts, because the shelf never sends part of a request. The bookkeeping sits inside the `node_status == "active"` branch (*in `process_order_raw` that branch is gone since §3.18: `Manufacturer.process_order` checks the supplier before any raw order starts*). `shortage` is unchanged: it still records how short the node was when the order arrived and is never cleared.
- **New helpers `Inventory.waiting_orders()` and `Inventory.waiting_site_orders()`**, both reading the shelf's queue (`inventory.inventory.get_queue`). Reading the queue is always exact: SimPy removes a request once it is served, so there is no separate counter to keep in sync. Customers only take stock that is free for them, so they never wait in this queue, but other requests can: for perishable goods, `remove_expired` asks to take expired units away, and that request waits behind earlier ones like any other (in `examples/py/hybrid_big_sc.py`, the bakery had a 68-unit expiry request waiting between its site orders). So `Inventory.get` takes an optional `site_order` flag and labels every request it creates; the two order methods pass `site_order=True`. `waiting_site_orders()` sums only the labelled requests; `waiting_orders()` sums them all.
- **`Node.position()`** subtracts only the units owed to waiting customers: `on_hand - (backorder[1] - inventory.waiting_site_orders())`. Both capacity clamps (§3.10) now call `self.position()`, so the formula lives in one place.
- **`manufacture_product`** caps production at `on_hand - level + inventory.waiting_orders()`. This uses the full total, because every waiting request, expiry removals included, has been taken off `on_hand` but has not left the shelf.

**Correction to §3.11:** the invariant `level <= on_hand` does not hold while orders wait at the shelf (shelf 10, `on_hand` −40 in the example above). The quantity that is never negative is `on_hand - level + waiting_orders()`, the units still to be made.

**Behavioral note for downstream users:** a node's `backorder` now means "orders owed right now", so the network-wide `backorders` figure at the end of a run is what is still owed then, not every order that ever had to wait. Sites in multi-level networks stop carrying the extra stock the stuck backorder used to cause, so their holding costs and orders change. `intro_simple.py` has only an endless supplier, which never makes an order wait, so its result is unchanged.

**Verified:**

- Canonical `examples/py/intro_simple.py` unchanged (`profit: -4435.0`).
- `pytest` — 227/227 passing.
- New regression tests in `tests/test_core.py`: `TestSiteBackordersAreLive` (8 tests, including a waiting expiry removal that must not be mistaken for a site order), `TestFactoryMakesWhatItOwes` (the 10-on-the-shelf factory example: 50 received, 50 raw material bought, 50 made, nothing left over), and `TestSupplierRawMaterialBackordersAreLive` (2 tests).

### 3.18 Factories stop for good: one batch per delivery, and planned units with no raw material ✅ Resolved
Reported in GitHub issue #1 (defects 3, 4 and 5). `Manufacturer.behavior`, `Manufacturer.manufacture_product`, `Manufacturer.process_order`, `Manufacturer.process_order_raw`, `Inventory.get`.

**How a factory is meant to work (user, 2026-10-11).** `batch_size` is the factory's capacity: it can make at most `batch_size` units at once, and each batch takes `manufacturing_time`. When the replenishment policy asks for more stock, the factory plans those units (adds them to `on_hand`) and orders the raw materials for them. It then makes batch after batch until every planned unit is made. If stock drops below s again in the meantime, the policy plans more units and orders their raw material; the factory just has more to make. A batch may be smaller than `batch_size` when there is only raw material, shelf space or planned work left for fewer units.

**Original issue.**

1. **One batch per raw-material delivery (defect 3).** The production loop made one batch and then waited for the next delivery (`raw_material_arrived`). A factory that planned 25 units with `batch_size` 5 got the raw material for all 25 in one delivery, made 5, and sat with raw material for 20. If its position stayed above s, no new plan came, so no delivery came, and it never woke again. The example from the issue (batch size 5, 300 days) made 10 units in 300 days and stopped for good on day 14, holding raw material for 39 more; customers got 4% of what they asked for. This came in with §5.1: the old loop checked once per day, so it made one batch per day; the event-driven loop made one batch per *delivery*.
2. **Production paused at a full shelf never restarted (defect 5).** Same cause: freeing shelf space did not wake the loop.
3. **Planned units with no raw material behind them (defect 4, and the rest of defect 3).** `Manufacturer.process_order` added the planned units to `on_hand` first and then tried to order raw material, but the order could be skipped:
   - while an earlier order for that raw material was still on its way (`ongoing_order_raw`, see §3.12). It was meant only to stop one plan ordering the same raw material from several suppliers, but it stayed set until the delivery arrived;
   - when the factory already held "enough" raw material (`process_order_raw`). That raw material was already set aside for units planned earlier;
   - when the link or the supplier was disrupted (the early exits in `process_order_raw`). This case was not in the issue.

   Units planned this way can never be made, yet they count in the factory's position, so the policy does not plan again, and orders waiting for those units wait forever. In `examples/py/hybrid_big_sc.py` (seed 2) the bakery planned 667 loaves while a flour order was on its way (four plans: 210, 140, 172 and 145). By day 120 it had made all 6,640 loaves it had raw material for, then stopped for good: its position was 350 (41 on the shelf + 667 planned − 358 owed), above s = 300, with no raw material and no raw order on its way.

**Fix applied:**

- **The production loop keeps going.** `manufacture_product` makes one batch and returns how many units it made. `behavior` starts the next batch straight away after a batch that made something. Only when nothing can be made (nothing planned, no raw material, or no free space) does it wait, on a new event `production_wake` (replacing `raw_material_arrived`).
- **`Manufacturer.wake_production()`** fires that event. It is called when raw material arrives (`process_order_raw`), when a new plan comes in (`process_order`), and whenever stock leaves a manufacturer's shelf (`Inventory.get`, which looks the method up with `getattr`, since only manufacturers have it). A wake-up never makes anything by itself: the loop just checks again and goes back to waiting if nothing can be made. So waking it more often than needed costs one quick check, and no case can be missed. Expiry removals also go through `Inventory.get` and free space too. `Inventory.destroy` does not wake the loop yet (see defect 7).
- **Every plan orders its own raw material.** The `ongoing_order_raw` flag is removed; `pending_orders` already counts raw orders on their way. Several raw orders on their way at once are fine, as for distributors (§3.12). The "already have enough raw material" check in `process_order_raw` is removed. There is no limit on raw-material storage yet, and every plan orders exactly what it needs, so raw material on hand always belongs to earlier plans.
- **Check the suppliers before planning.** `process_order` first picks, for every raw material, the first connected supplier whose link and site are both working, and only then adds the units to `on_hand` and starts the raw orders. If any raw material has no working supplier, it plans nothing and orders nothing (not even the other raw materials); the policy tries again when stock drops or at its next periodic check. This is how `InventoryNode.process_order` already treats a down link. `process_order_raw` no longer has its own disruption checks. It starts at the same moment, before the clock moves on (SimPy starts a new process before any timed event at that moment), so nothing can break down in between. Its shortage is therefore recorded only for an order that is really placed. Picking the first working supplier, rather than the first connected one, also means a second supplier of the same raw material is used while the first one's link is down.

**Verified:**

- Canonical `examples/py/intro_simple.py` unchanged (`profit: -4435.0`; it has no factory). `examples/py/sc_with_factory.py` output identical.
- The example from the issue: 889 units made instead of 10, no raw material left unused, customers get 99% instead of 4%.
- `examples/py/hybrid_big_sc.py`: the bakery no longer stops (seed 2: 70,358 loaves made, raw material ordered for 70,558, the last 200 still on their way). Customers there still get only about 3%, but the bread now runs out downstream: most of it expires at the distributors and shops (defect 7).
- `pytest` — 234/234 passing. New `TestFactoryKeepsProducing` (7 tests: one delivery made into every batch it covers; raw material ordered while an earlier order is on its way; leftover raw material does not cancel a new order; a full shelf restarts once space frees; a disrupted raw-material link plans nothing until it recovers; one working supplier per raw material; the example from the issue). `TestSupplierRawMaterialBackordersAreLive::test_disrupted_supplier_records_no_backorder` now places the order through `process_order`, where the check lives, and also checks that no shortage is recorded and nothing is planned.

### 3.19 A supplier with a limited shelf stops mining for good once its shelf has been full ✅ Resolved
Reported in GitHub issue #1 (defect 6). `Inventory.get`, `Supplier.behavior`, `InventoryNode.process_order`.

**How a supplier is meant to work (user, 2026-10-11).** A supplier with a limited shelf keeps mining (`extraction_quantity` units every `extraction_time`) until its shelf is full, and starts again as soon as stock is taken. This is a base-stock rule (keep the shelf at a target and replace whatever is taken) with the shelf capacity as the target. A supplier has no replenishment policy of its own. An optional mining policy, such as (s, S) campaign mining, may be added later as a feature, with this behaviour as the default.

**Original issue.** When its shelf is full, `Supplier.behavior` waits for the "stock went down" signal (`inventory_drop`). `Inventory.get` sent that signal only when the node had a replenishment policy, and suppliers never have one, so taking stock from a supplier never woke it. The only other wake-up was in `InventoryNode.process_order`, which signalled the supplier when a distributor ordered more than the supplier had on its shelf. Raw-material orders from factories never woke it. So:

- A factory buying from a limited supplier stopped for good once the supplier's first full shelf was used up: the supplier never mined again, and the raw-material orders waited forever.
- Distributors only got through because an order bigger than what was left on the shelf woke the supplier. Until then it did not refill, so the next orders found it partly empty and had to wait.

This came in with §5.1 Fix (1), which replaced the supplier's daily check with waiting on `inventory_drop`, on the belief that `Inventory.get` already signalled every node.

In `examples/notebooks/simple_supplier_n_factory.ipynb` (365 days) the supplier mined nothing at all: by the end, 3,500 units of raw-material orders were stuck waiting at the supplier, the factory had made 4,200 units, and customers got 7% of what they asked for.

**Fix applied:**

- `Inventory.get` signals `inventory_drop` for every node that has the event (looked up with `getattr`), not only for nodes with a replenishment policy. A supplier with a full shelf now starts mining as soon as a buyer takes stock. For a distributor with no policy nobody waits on the event, so the signal does nothing. Endless suppliers return from `get` before this point and do not have the event.
- The extra signal in `InventoryNode.process_order` (sent when the supplier was short) is removed. `Inventory.get` now signals whenever an order is really taken from the supplier's shelf. The extra signal also fired when the supplier site was down and the order was never placed, which woke the supplying site's own policy for no reason (an open item from §3.18).

**Not changed:** `InventoryNode.process_order` still records a shortage at the supplier before checking that the supplier site is working, so a down site gets a shortage for an order it never received. `Inventory.destroy` still does not signal anything (see the convention in `CLAUDE.md`), so a supplier whose shelf is destroyed while full waits for the next order before mining again. *The shortage part is fixed in §3.20, and the `destroy` part in §3.21.*

**Verified:**

- `examples/py/intro_simple.py` unchanged (`profit: -4435.0`; it has only an endless supplier). `examples/py/sc_with_factory.py` output identical. `examples/py/hybrid_big_sc.py` uses only endless suppliers and is not affected.
- `simple_supplier_n_factory.ipynb` (its simulation, run without the plots): the supplier now mines 79,050 units, no order is left waiting, the factory makes 82,700 units, and customers get 80% instead of 7%. The warehouse now throws away 62,795 expired units: stock reaches it already old (defect 7). The notebook's saved outputs are out of date.
- `pytest` — 238/238 passing. New `TestLimitedSupplierKeepsMining` (4 tests: the supplier refills its shelf after a sale; orders smaller than the shelf find it full again; a factory gets its raw material from a supplier that was full; a supplying site that is down is not told its stock went down). All four fail on the old code.

### 3.20 A supplier site that is down is counted as short for orders it never receives ✅ Resolved
Open item from §3.18 and §3.19. `InventoryNode.process_order`.

**Original issue.** `InventoryNode.process_order` recorded a shortage at the supplier (when its shelf held less than the order) *before* checking whether the supplier's site was working. When the site was down, the code then logged "Order not placed" and stopped, but the shortage stayed. The supplier's demand received did not go up, so its shortage counted orders it never received. While a site was down, the buyer's policy could try several times (for example each time its own stock dropped), and each attempt added another shortage. `simulate_sc_net` adds every node's shortage into the network total, so that was too high as well. A down *link* never had this problem: it is checked before anything is recorded. Factories did not have it either: since §3.18, `Manufacturer.process_order` checks the link and the supplier site before any raw-material order starts.

**Fix applied:** the shortage check moved inside the "supplier site is active" branch, just before the order is placed. A supplier is now counted as short only for an order it really receives. Nothing changes when the supplier site is up.

**Verified:**

- `examples/py/intro_simple.py` unchanged (`profit: -4435.0`).
- `pytest` — 240/240 passing. New `TestNoShortageAtASupplierSiteThatIsDown` (2 tests: three orders to a down site that is short record no shortage, demand or backorder anywhere; the same order to a working site is still counted as short, `[1, 15]`). The first fails on the old code.

### 3.21 Perishable goods: dated batches picked when an order is placed, and expired stock shipped ✅ Resolved
Reported in GitHub issue #1 (defect 7). `Inventory.get`, `Inventory.remove_expired`, `Inventory.destroy`, new `_Shelf` / `_ShelfRequest`.

**How perishable stock is meant to work (user, 2026-10-11).** Every order gets the units with the least shelf life left first; if the oldest batch is not enough, it takes from the next oldest, and so on ("clear the old stock first"). Selling fresh units first would leave the old ones to expire. `perish_queue` (a list of dated batches, oldest first) implements this rule, and the rule itself was right.

**Original issue.** A perishable inventory keeps two records of the same stock: the dated batches (`perish_queue`) and the plain unit count on the SimPy shelf. They changed at different moments. `Inventory.get` took batches off `perish_queue` at once, when the order was *placed*, but only *asked* the shelf for the units; an order the shelf could not fill waited in line and was served later. So, for an order that had to wait:

- It got dates for only the units on the shelf when it was placed. The buyer stocks only the units its dates cover, so the rest were lost, while the buyer's inventory position still counted them. Example: a warehouse with 5 units gets an order for 20; when it is served, the buyer receives 5.
- The fresh units that later filled the order stayed in `perish_queue`, so the list showed units that had left.
- The old units' dates were already off the list, so `remove_expired` never saw them expire, and they were shipped after they had expired. The buyer threw them away on arrival.

In addition, `remove_expired` and `Inventory.destroy` removed units with an ordinary shelf request, which waits in line behind an order the shelf cannot fill yet. Expired units stayed on the shelf until then (and the expiry helper was stuck, so later expiries waited too), and destroyed stock was really taken from the next delivery. `destroy` also did not wake a supplier or factory (open item from §3.19).

**Fix applied:**

- `Inventory.inventory` is now a `_Shelf`, a small `simpy.Container` subclass. Its `_do_get` (where SimPy hands units out) picks the dated batches, oldest first, at the same moment it takes the units off the shelf, and keeps them on the request (`_ShelfRequest.batches`, which also carries `site_order`). `Inventory.get` returns that list, so it is filled in when the order is served — at once if the shelf has the units, otherwise later. Callers already read it after `yield event`, so none had to change. The batch-picking loop moved to `Inventory._take_oldest_batches`. The two records now always agree: `perish_queue` adds up to the shelf's level.
- `_Shelf.take_now(amount)` removes units at once, ahead of any waiting requests. `remove_expired` pops each expired batch and takes the same units off with it; `destroy` does the same for the oldest batches. Every batch in the list is physically on the shelf, so the units are there to remove.
- After expired units are removed, the node is told stock went down (as before, when the removal went through `get`); the signalling moved to `Inventory._stock_went_down`. After `destroy`, a supplier is told (it has no replenishment policy, so this only restarts mining) and a factory's production is woken; nodes with a replenishment policy are still not told (§4.3).

**Not changed:** an order and an expiry due at exactly the same moment are resolved in SimPy's event order, so a unit can occasionally be shipped at exactly the end of its shelf life. Units shipped close to the end of their life can still expire in transit or soon after arrival; that depends on the network's settings (stock levels, lead times, shelf life), not on the code. A site that starts with no stock still holds an empty `(0, 0)` batch until its expiry check clears it (an existing test relies on it).

**Verified:**

- `examples/py/intro_simple.py` unchanged (`profit: -4435.0`). `sc_with_factory.py` and `newsvendor.py` outputs unchanged.
- `examples/py/hybrid_big_sc.py` (perishable): customers receive 11,823 units instead of 1,007; total expired waste falls from 66,230 to 37,653; network shortage from 46,624 to 16,345 units.
- `simple_supplier_n_factory.ipynb` (its simulation): no change in what customers get (about 80%). The warehouse still throws away 58,880 units (62,795 before): the factory holds up to 2,500 units of a product that lasts 10 days and ships the oldest first, so units reach the warehouse 1–11 days old. That comes from the example's settings, not from the code.
- `pytest` — 245/245 passing. New `TestPerishableBatchesPickedWhenShipped` (5 tests: a waiting order gets every unit with its real dates; stock that expires while an order waits is thrown away, not shipped; `destroy` empties the shelf at once while an order waits; `destroy` restarts a full supplier; the two records agree throughout a busy perishable network). `TestSiteBackordersAreLive::test_waiting_expiry_removal_not_mistaken_for_a_site_order` became `test_expired_goods_removed_at_once_not_behind_a_site_order`. All six fail on the old code.

*Renamed later, when the terminology was settled (`docs/glossary.md`): `_Shelf` → `_InventoryContainer`, `_ShelfRequest` → `_InventoryGet`, `_Shelf.take_now` → `_InventoryContainer.remove_now`, `Inventory._take_oldest_batches` → `Inventory._pick_oldest_batches`, `Inventory._stock_went_down` → `Inventory._signal_inventory_drop`.*

### 3.22 A waiting customer is counted as short several times ✅ Resolved
Found during the comment sweep. `Demand.wait_for_order`.

**Original issue.** A shortage records how many units a site was missing when an order arrived; it is a running total and is never reduced (see `CLAUDE.md`). For a customer who waits (`tolerance > 0`), `_enqueue_for_tolerance` records that shortage when the order arrives. `wait_for_order` then recorded it again on every check where it could not serve the customer: once straight away (its first check runs at the same moment), and once more after every delivery that was not enough. One customer short by 10 units showed a shortage of `[2, 20]` at once, and `[5, 34]` after three small deliveries; the expected value is `[1, 10]`. The node's and the network's shortage figures were too high in any model with waiting customers. Profit was not affected. The bug was already in 0.1.12; it was not caused by the issue #1 fixes.

**Fix applied:** the shortage line in `wait_for_order`'s "not enough yet" case is removed; a comment there says why. A waiting customer's shortage is now recorded once, when the order arrives.

**Verified:**

- `examples/py/intro_simple.py` unchanged (`profit: -4435.0`). No example or case study uses waiting customers (the only `tolerance=` in the examples is commented out), so none of their results change.
- `pytest` — 248/248 passing. New `TestWaitingCustomerShortageCountedOnce` (3 tests: deliveries too small to fill the order; partial deliveries; one shortage per waiting customer). All three fail on the old code.

### 3.23 A buyer never orders again after its supplier recovers; orders sent to a disrupted supplier site ✅ Resolved
Found while updating `examples/notebooks/case_study_pharma.ipynb`. `Node.place_order`, `Node.disruption`, `Link.disruption`, the supplier-selection policies, `InventoryNode.process_order`, `Manufacturer.process_order`.

**Original issue.** A replenishment policy without a review period checks its inventory position only when it is woken, and it was woken only by `inventory_drop` (units leaving the inventory, units expiring, or a waiting customer). An order it tried to place while its supplier, or the link to it, was disrupted was not placed (`process_order` logged "Order not placed" and stopped). If the site then had no units left, nothing could leave its inventory, so nothing woke the policy again, and the site never ordered again, even after the supplier recovered. In the pharma case study the pharmacy's units expired on day 180 while its only supplier was disrupted; the supplier recovered on day 215, and the pharmacy stayed empty for the rest of the run. Manufacturers had the same problem through `Manufacturer.process_order`, which plans nothing while a raw-material supplier is disrupted. The bug was already in 0.1.12; the pharma results are identical there.

A second, related gap: the supplier-selection policies skipped suppliers whose *link* was disrupted, but not suppliers whose *site* was disrupted. A buyer with two suppliers could choose the disrupted site and lose the order while the other supplier was working.

**Fix applied:**

- `Link.can_take_order()` says whether an order can be sent over a link: neither the link nor its supplier's site is disrupted. It is the one place this rule lives.
- `Node.place_order` checks `can_place_order()` first and places nothing if it is false. For `InventoryNode`, at least one supplier must be able to take the order; `Manufacturer` overrides it so every raw material needs one (otherwise the planned units could never be made). `InventoryNode.process_order` checks the chosen link again with `can_take_order()` when it starts, because that is when the order is really placed (recorded at the supplier and taken from its inventory); `place_order` only starts the process. The two can differ at time 0: processes queued before `process_order` run first, and these include the start of every disruption process, whose first random draw (`failure_p`, `link_failure_p`) can disrupt the chosen supplier or link. A link is always created after its buyer, so this happens whenever the buyer orders at time 0 and the link's first draw hits. A blocked order records nothing, and the recovery wake-up below makes the policy try again. `Manufacturer.process_order` picks a supplier per raw material (through the new `_raw_material_links`) when it starts, so it plans nothing in the same case.
- The selection policies choose only among links with `can_take_order()` (`_active_suppliers`, and `_apply_mode` in fixed mode). `_active_suppliers` still falls back to every link if none can take the order, but `place_order` never calls `select` in that case.
- Each node keeps `buyers`, the links to its buyers, registered by `Link.__init__` through the new `Node.add_buyer_link` (the mirror of `add_supplier_link`). When a node recovers, `Node.disruption` calls `wake_replenishment()` on every buyer; when a link recovers, `Link.disruption` calls it on its sink. `Node.wake_replenishment` fires `inventory_drop`, the event the policy already waits on, so the policy checks its position again and orders if needed. The order is sized from the position at the moment of recovery, not from before the disruption. An extra wake-up does no harm, and policies with a review period are not affected.

**Not changed:** if the chosen supplier is disrupted at time 0 after `place_order` chose it, the order is dropped, not sent to another supplier; the buyer orders again when a supplier or link recovers or when units leave its inventory.

**Verified:**

- `examples/py/intro_simple.py` unchanged (`profit: -4435.0`).
- Pharma case study (no review period, 200 runs, seed 7): mean cost 6.59 / 2.41 / 0.89 for (s, S) = (2000, 5000) / (100, 1000) / (1200, 2000), against 10.14 / 5.93 / 2.40 before and 6.75 / 2.61 / 0.89 with a daily review.
- `pytest` — 259/259 passing. New `TestPolicyWokenWhenSupplierRecovers` (4 tests: a distributor orders as soon as its supplier site recovers; the same for a link; a manufacturer plans once its raw-material supplier recovers; a link is registered with its source) and `TestOrdersSkipDisruptedSupplierSites` (4 tests: the order goes to the supplier whose site is not disrupted; fixed mode skips its supplier while the site is disrupted; no order when every supplier is disrupted; a manufacturer needs a supplier for every raw material). All eight fail on the old code. Four existing tests that started `process_order` directly against a disrupted supplier now go through `place_order`. Two more tests in `TestOrdersSkipDisruptedSupplierSites` cover the time-0 case (a link, then a supplier site, disrupted by its first random draw after `place_order` chose it); both fail without the check in `process_order`.

### 3.24 `Statistics.reset()` changes values that describe the present ✅ Resolved
Found while designing link statistics (§6.8). `Statistics.reset`.

**What a reset is for.** A run starts in an unusual state: nothing is in transit, no orders are waiting, and every inventory holds its `initial_level`. To measure long-run behaviour, users run a **warm-up** (an opening stretch left out of the statistics): run for the warm-up period, call `stats.reset()`, and carry on running. The pharma case study does this (`docs/case_study_pharma.md`, run to time 31, reset each node, run to `T + 1`). The simulation itself carries on unchanged; only the counting should start again.

**Original issue.** `reset()` sets every number and `[orders, units]` pair it finds to zero. Most of them are running totals, where that is right. Four are not:

1. **`backorder`** is what the site owes *right now*. Orders still waiting at the reset are still waiting afterwards. When each one is served it is taken off `backorder` as usual, so the count goes negative (two waiting customers for 20 units: `[2, 20]` becomes `[0, 0]` at the reset and `[-2, -20]` once they are served). Until then `position()`, which subtracts `backorder[1]`, sees too little owed, so the site orders too little.
2. **Holding cost.** `reset()` sets `inventory.carry_cost` to zero but leaves `inventory.last_update_t` where it was. The next update charges `level × (now − last_update_t)`, which includes time before the reset. This is harmless in the usual pattern, because `simulate_sc_net` calls `update_stats()` on every node when it stops, which moves `last_update_t` to the reset time. It is wrong after `env.run()` called directly, or a reset made from inside a SimPy process.
3. **`inventory_level`** is the inventory level at the last update. It reads 0 after a reset until the next `update_stats()` call.
4. **`inventory.instantaneous_levels`** (the once-per-time-unit record kept when `record_inv_levels=True`) is never cleared, so the network's `avg_available_inv` keeps averaging samples from before the reset.

**Fix applied:**

- A class-level `Statistics._live_keys = ["backorder", "inventory_level"]` lists the values that describe the present. Both passes of `reset()` skip them.
- Before zeroing, `reset()` brings the holding cost up to date with `inventory.update_carry_cost()`, under the same guard `update_stats` uses (skipped for an infinite inventory, whose level is `inf`). This moves `last_update_t` to the reset time.
- `inventory_level` is re-read from `inventory.level` (same guard).
- `inventory.instantaneous_levels` is cleared. Recording carries on from the reset (agreed with the user, 2026-10-15: a warm-up exists to drop that period from every average).
- `node_cost`, `revenue` and `profit` are zeroed with the totals they are made from, so they agree with them; the next `update_stats()` recomputes them as usual.
- Physical state is not touched and must stay that way: `inventory.on_hand`, `inventory.level`, `pending_orders`, `raw_inventory_counts`, perishable batches and waiting requests. Pass 2 only scans the `Statistics` object; a comment there says so.
- The `reset` docstring explains what a warm-up is and lists the edge effects below. **Warm-up** was added to `docs/glossary.md`.

**Known edge effects (documented in the `reset` docstring, not fixed).** Each event is counted when it happens, as everywhere else in `Statistics`. So for orders that span the reset:

- Arrivals of orders placed before the reset count after it: `fulfillment_received`, `inventory_spend_cost`, the supplier's `demand_fulfilled` and so `revenue`. A window can show slightly more received than placed.
- Units bought before the reset that expire after it count as waste after it. A production batch that starts before and finishes after counts in `total_products_manufactured` / `total_manufacturing_cost`.
- Partial deliveries to customers take 1 off the order count of `demand_fulfilled` (at the site) and `fulfillment_received` (at the customer demand) at once and add 1 back when the units arrive (`Demand.wait_for_order`, `Demand._process_delivery`), so one customer order is counted once. If a reset falls between those two moments, the −1 is wiped and the +1 still lands, so that order is counted twice in the new window. Units are not affected, only the order count.

**Not changed:** the network results in the `supplychainnet` dictionary are not cleared by a reset; `simulate_sc_net` rebuilds them from the node statistics when it next stops.

**Verified:**

- `examples/py/intro_simple.py` unchanged (`profit: -4435.0`, run with `PYTHONPATH=src`; it never resets).
- `pytest` — 276/276 passing. New `TestStatisticsResetKeepsThePresent` (5 tests: a customer waiting at the reset keeps `backorder` and `position()` unchanged, and `backorder` returns to `[0, 0]`, not below, once they are served; holding cost after `env.run()` and a reset covers only the time since the reset (30, not 80); `inventory_level` equals `inventory.level` straight after a reset; `instantaneous_levels` is empty after a reset and holds only later samples afterwards; an infinite supplier can be reset). The first four fail on the old code; the fifth guards the infinite-inventory case of the new code.
- Pharma case study: 30 replications of `pharma_experiments.py`'s model ((s, S) = (2000, 5000), (100, 1000), (1200, 2000), NumPy seeds 0 to 9) give identical results before and after. In this model no order is waiting at time 31 (customers take what is there and leave, and the infinite supplier never makes an order wait), and `simulate_sc_net` had already brought the holding cost up to date before each reset. So the notebook and `docs/case_study_pharma.md` need no change.

### 3.25 A manufacturer's raw-material order counts as placed only once the supplier serves it ✅ Resolved
Found while designing link statistics (§6.8). `Manufacturer.process_order_raw`.

**Original issue.** `InventoryNode.process_order` records the buyer's `demand_placed` and `transportation_cost` when the order is placed. `Manufacturer.process_order_raw` recorded them only after `yield event`, that is once the supplier had the units and served the order. While a raw-material order waited at its supplier, the manufacturer's statistics did not show it as placed, although the supplier already counted it in `demand_received` and `backorder`. Totals at the end of a run differed only for orders still waiting then; the timing mattered for anything read during a run, for a warm-up reset (§3.24), and for the link statistics of §6.8, which copy their buyer's timing.

**Fix applied:** the `update_stats(demand_placed=..., transportation_cost=...)` call moved to just before `inventory.get(...)`, when the order is placed, as in `InventoryNode.process_order`. The user confirmed that `InventoryNode`'s timing is the right one.

**Verified:**

- `examples/py/intro_simple.py` unchanged (`profit: -4435.0`). `sc_with_factory.py` (`profit: 49419.6`, `demand_by_site: [2, 1440]`) and `hybrid_big_sc.py` give output identical to the last commit's code.
- `pytest` — 277/277 passing. New `TestSupplierRawMaterialBackordersAreLive::test_raw_material_order_recorded_when_placed` (an order that waits at its supplier from day 0.5 to day 2 shows in the manufacturer's `demand_placed` and `transportation_cost` at day 1.5, and is counted once). It fails on the old code.

### 3.26 Customers can order from a disrupted site ✅ Resolved
Found while listing missing node statistics. `Demand.customer`, `Statistics`.

**Original issue.** Since §3.23 a disrupted site takes no new replenishment orders (`Node.place_order`, `Link.can_take_order`). `Demand.customer` did not look at `demand_node.node_status`, so customers kept ordering from a disrupted site and were served from its inventory as usual. The glossary already described a disrupted site as one that "receives no new orders".

**Decision (user, 2026-10-16).** A disrupted site takes no new orders from customers either. A customer who arrives then goes away: a sale the site loses because of the disruption. It is recorded as a new statistic, `disruption_lost_sales` (`[orders, units]`), at the site, and kept apart from `shortage`. A shortage is units the site did not have; a disruption lost sale is an order it could not take, whatever its inventory level. The cause and the remedy differ (more inventory against a better replenishment policy; backup sites or shorter recoveries against disruption), so mixing them would hide which problem a site has. Some disruptions might in reality still let a site take orders it cannot ship; that could become an option later, with today's behaviour as the default.

**Fix applied:**

- `Demand.customer` checks `demand_node.node_status` first. If the site is disrupted, it records `disruption_lost_sales=[1, order_quantity]` at the site, writes one log line, and stops. Nothing else is recorded: no `demand_received`, `shortage` or `backorder` at the site, and the customer demand's own `demand_placed` does not count the order, as for a replenishment order that is not placed. A site's total customer demand is therefore `demand_received + disruption_lost_sales`.
- Only new orders are turned away. Customers already waiting when the disruption starts keep waiting and are served when units arrive (or leave when their tolerance runs out), and deliveries already on their way still arrive, as for links and replenishment orders.
- `disruption_lost_sales` is in `Statistics._stats_keys`, so every node reports it and `reset()` zeroes it. `simulate_sc_net`'s network results do not add it up yet.
- Docs: glossary (new **Disruption lost sales** entry; the **Disruption** and **Shortage** entries say how the two differ), `about.md`, `api-intro.md`, and the sample output in `examples/py/intro_simple.py` (one new key). The pasted tables in `examples/py/hybrid_big_sc.py` and the saved notebook outputs are left as they are: they would only gain a row of zeros.

**Verified:**

- `examples/py/intro_simple.py` unchanged (`profit: -4435.0`).
- Pharma case study: the same 30 replications as in §3.24 give identical results (only the raw-material supplier is disrupted, and it has no customers). Milk case study: only distributors are disrupted, and they have no customer demands (user, 2026-10-16), so no change.
- `pytest` — 282/282 passing. New `TestCustomersCannotOrderFromADisruptedSite` (5 tests: a customer at a disrupted site is a lost sale and nothing else is recorded; customers are served again after recovery; a customer already waiting is still served; customers with no tolerance, with a tolerance, and taking what is there are all turned away; the statistic is reported and reset). Four fail on the old code; the waiting-customer test guards the "only new orders" rule.

### 3.27 A replenishment order larger than its supplier's capacity waits for ever ⏸️ Deferred (user, 2026-10-16)
Found while verifying §6.9. `InventoryNode.process_order`, `Manufacturer.process_order_raw`, `Inventory.get`.

**The issue.** A supplier fills a replenishment order only when it holds the whole order at once ("ship complete"): the order waits in the supplier's queue of requests until the inventory level reaches it. An order larger than the supplier's capacity can never be filled, so it waits for ever, and nothing says so (no warning, no log line). The buyer's inventory position already counts the units, so its replenishment policy may never order again. Example from the §6.9 test network: a manufacturer planned 146 units of a product that needs 2 units of raw material each, and ordered 292 units from a raw-material supplier that holds at most 200. The manufacturer never produced again.

It happens whenever a buyer can order more than its supplier can hold: a distributor with capacity 100 selling to a retailer with capacity 200, a raw-material supplier with capacity 200 selling to a factory with capacity 500, or an (s, S) policy that adds a large backorder to its order. For a manufacturer, "supplier capacity ≥ buyer capacity" is not enough, because raw material is ordered in raw-material units: units planned × quantity per product unit.

**How real supply chains handle it.** Supplier and buyer agree on a rule for filling orders:

1. **Ship complete:** wait until the whole order is there and send it in one shipment (what SupplyNetPy does today).
2. **Partial shipments, rest backordered:** send what is there now (often only above a minimum amount) and send the rest as units arrive. The customer equivalent is `order_min_split_ratio`.
3. **Ship what is there, cancel the rest** ("fill or kill"): the buyer gets what the supplier has and orders again from its new inventory position. The customer equivalent is `consume_available` (for customers the rest is a lost sale; for a site it is re-ordered).

**Decided so far (user, 2026-10-16):** support both rule 2 and rule 3 for replenishment orders, and keep rule 1 as the default, so every existing result stays the same.

**Open questions for when this is picked up:**

- Where the setting lives: on the buyer (like `Demand`), on the supplier, or on the link. A fill rule is usually agreed per supplier and buyer pair, which points to the link; the link statistics (§6.8) could then count shipments per order.
- Whether each partial shipment pays the link's transportation cost again and draws its own lead time (real shipments do, which makes splitting a cost trade-off).
- What the default rule does with an order larger than the supplier's capacity, which ship complete can never fill. Suggested: ship it in parts and log that it was split, so a model never waits for ever without saying so.
- Bookkeeping when one order becomes several shipments: the inventory position, the supplier's `backorder`, the queue of waiting requests that `position()` reads (`waiting_site_orders()`), perishable batches, `pending_orders`, and counting `demand_fulfilled` once per order (as for customer partial deliveries). A change of about the size of §3.21.

**Warnings added meanwhile (user, 2026-10-16).** Two warnings make the assumption below visible; neither changes any result.

- **When a link is created** (`Link._warn_if_buyer_can_order_more_than_supplier_holds`, called from `Link.__init__`, so both construction styles get it). Capacities are fixed when the sites are created, so a pair whose buyer can order more than its supplier can hold can be found before anything runs. The most a buyer orders is taken as its capacity; for a manufacturer, its capacity × the quantity of that raw material per product unit. A buyer with no capacity limit counts as able to order any amount. The warning names both sites (one warning per pair, on purpose, so the user sees every pair), explains the deadlock (the buyer waits for the order for ever, and the supplier can never hold enough to send it), says how to fix the model, and mentions the planned feature. It is also written to the log.
- **When such an order is placed** (`Node._warn_if_supplier_cannot_hold`, from `InventoryNode.process_order` and `Manufacturer.process_order_raw`), with a short text without the sites (Python shows it once) and a log line naming the site, the supplier and the quantity. It stays, because a buyer that owes backorders can order a little more than its own capacity, which the link check cannot foresee.

Tests: `TestLinkWarnsWhenBuyerCanOrderMoreThanSupplierHolds` (4: a larger buyer, a buyer with no capacity limit, a manufacturer counted per product unit, and pairs that fit, including an infinite supplier, do not warn) and `TestOrderLargerThanSupplierCapacityWarns` (3). The three tests of `TestLimitedSupplierKeepsMining` use buyers with no capacity limit on purpose and ignore the link warning. `pytest` 312/312, also with `-W error::UserWarning`. Among the examples, only `hybrid_big_sc.py` warns (its raw-material supplier `bakery` holds 500, and `dist1` and `dist2` have no capacity limit; the orders it places fit, so its results do not change). The pharma model and the seven §6.9 comparison networks give unchanged results; only the manufacturer network warns.

**Assumption until then:** models are built so that no buyer orders more than its supplier can hold: each supplier's capacity is at least what any of its buyers can order (for a manufacturer, its capacity × the quantity of that raw material per product unit). Revisit after the planned work (§6.8 link statistics, §6.10 probability-based supplier selection).

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

*Corrected in §3.19: `Inventory.get` did not signal suppliers. It signalled only nodes with a replenishment policy, so a limited supplier whose shelf had been full never mined again. It now signals every node that has `inventory_drop`.*

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

*Corrected in §3.18: waiting for the next delivery after every batch was a bug. The old polling loop made one batch per day; this one made one batch per delivery, so raw material for the rest of a plan sat unused and the factory could stop for good. `behavior` now goes straight on to the next batch after a batch that made something, and waits on `production_wake` (raw material arrives, a new plan comes in, or stock leaves the shelf) only when nothing can be made.*

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

### 6.8 Link statistics ✅ Resolved (designed 2026-10-15, implemented 2026-10-16)
Requested by the user. New `LinkStatistics` in `core.py`; recording calls in `InventoryNode.process_order`, `Manufacturer.process_order_raw` and `Link.disruption`; new functions in `utilities.py`. Builds on §3.24 (`reset_stats` below calls `Statistics.reset()` on every node) and §3.25, and is done after §6.9, reusing its clock, disruption timer and reset handling of worked-out values.

**Purpose.** Node statistics say how much a site ordered and received in total, but not from whom. Since §3.23 every site keeps `buyers` as well as `suppliers`, so each link can record the flow between its two ends: how many replenishment orders the buyer placed over it, what it received, how long it waited, what it cost. This shows how orders split across suppliers, and serves as a target for research that studies flows (for example a learned model of the network).

**Where the statistics live.** A new class `LinkStatistics(InfoMixin)`, one per link, stored as `link.stats` (created in `Link.__init__`). Not in the node's `Statistics`, because:

- The numbers belong to a pair of sites, and the link is that pair. Storing them on nodes would mean a dict keyed by buyer on the supplier and a matching dict keyed by supplier on the buyer: the same facts twice.
- One record serves both ends: a supplier reads its buyers' links (`node.buyers`), a buyer reads its suppliers' links (`node.suppliers`).
- It follows the node pattern: `link.stats.get_statistics()` mirrors `node.stats.get_statistics()`. `link.get_statistics()` stays as it is (`{"status": ...}`).

Nothing is removed from or changed in `Statistics`. The link values repeat, per link, what the node statistics already record, so the node totals and the link totals can be checked against each other.

**Stored statistics.** Running totals, not lists: no record of each order is kept. Pairs are `[orders, units]`. Where a link statistic means the same as a node statistic it has the same name.

| Statistic | Meaning | Recorded in `InventoryNode.process_order` | Recorded in `Manufacturer.process_order_raw` |
|---|---|---|---|
| `demand_placed` `[orders, units]` | Replenishment orders the buyer placed over the link | With the buyer's `demand_placed`, when the order is placed | With the buyer's `demand_placed`, when the order is placed (since §3.25) |
| `fulfillment_received` `[orders, units]` | Orders that arrived at the buyer: units actually accepted | On arrival, `[1, accepted]` | On arrival, `[1, reorder_quantity]` |
| `shortage` `[orders, units]` | How many units the supplier was missing when this buyer's order arrived. Running total | With the supplier's `shortage` | With the supplier's `shortage` |
| `backorder` `[orders, units]` | This buyer's orders waiting at the supplier right now. Live value | With the supplier's `backorder`, +1 when the order has to wait and −1 once served | Same |
| `waited` `[orders, units]` | Orders that had to wait at the supplier at all. Running total (needed for fill rate, because `backorder` returns to zero) | Where `order_waits` is true | Same |
| `blocked` `[orders, units]` | Orders not placed because the link or the supplier's site was disrupted | In the `not supplier.can_take_order()` branch | Never: `process_order_raw` has no check (see what is not covered) |
| `transportation_cost` | Transportation cost of orders over the link | With the buyer's `transportation_cost` | With the buyer's `transportation_cost` |
| `inventory_spend_cost` | Value of the units the buyer received over the link | On arrival, `accepted × self.buy_price` | On arrival, `reorder_quantity × supplier.source.sell_price` |
| `waiting_time` | Total time orders waited at the supplier: from `inventory.get(...)` until the request is served, before the lead time starts | On arrival (the placement time is kept in a local variable of the process) | Same |
| `lead_time` | Total lead time actually drawn | On arrival | On arrival |
| `disruptions` | Number of disruptions of the link | `Link.disruption`, when the status becomes `"inactive"` | |
| `disrupted_time` | Time units the link spent disrupted | `Link.disruption`, on recovery | |

`waiting_time` and `lead_time` are recorded on arrival, together with `fulfillment_received`, so their averages divide by a count from the same moment (see reset below).

**Spread of order sizes: two different statistics.** Both are kept with Welford's method (three numbers: count, running mean, running sum of squared differences), so no list of values is kept. Each is a sample standard deviation (divides by n − 1), and is `None` with fewer than two values.

- `order_size_mean`, `order_size_std`: **per order.** Each order's size is one value, recorded together with `demand_placed`.
- `units_per_time_unit_std`: **per time unit.** The units ordered in each time unit form one value. Time units in which nothing was ordered count as zeros. This needs no process ticking every time unit: one number holds the current time unit's running total, and when the next order comes (or when the statistics are read), the finished time unit and every empty one since are folded in, the empty ones in one step. The time unit still in progress is not included. Reading works on a copy and does not change the stored values. Time units are counted from `start_time` (the start of the run, or the last reset), with a fixed length of 1 time unit for now.

The two can disagree completely, and the docstrings say so with this example. A distributor that orders 60 units at time 3 and 60 units at time 7, and nothing in between, has an `order_size_std` of 0 (every order is the same size) but a large `units_per_time_unit_std` (the orders come in bursts). The **bullwhip effect** (orders becoming more variable as they move up the chain) is measured per time unit: compare a link's `units_per_time_unit_std` with the spread of customer demand per time unit.

**Values worked out when read.** Properties listed in `_stats_keys`, so `get_statistics()` includes them, and nothing has to be finalized after a run. Elapsed time is `env.now − start_time`. A value whose denominator is zero is `None`, not 0 (a fill rate of 0 would look like a very bad link).

| Value | Formula |
|---|---|
| `elapsed_time` | `env.now − start_time` |
| `orders_per_time_unit`, `units_per_time_unit` | `demand_placed / elapsed_time` |
| `avg_waiting_time` | `waiting_time / fulfillment_received[0]` |
| `avg_lead_time` | `lead_time / fulfillment_received[0]` |
| `avg_order_cycle_time` | `avg_waiting_time + avg_lead_time` (from placing the order until it arrives) |
| `fill_rate` | `1 − waited[1] / demand_placed[1]`: share of units ordered that were served without waiting |
| `order_fill_rate` | `1 − waited[0] / demand_placed[0]`: the same, by orders |
| `availability` | `1 − disrupted_time / elapsed_time`, where `disrupted_time` includes a disruption still going on when read |

Left out on purpose: link utilization (links have no capacity, so it is not defined), and the time-weighted average of units in transit (a real statistic, easy to add later).

**Methods.** `update_stats(**kwargs)` adds to the totals, like `Statistics.update_stats`, and warns about an unknown name in the same way (it does not do the node-only work at the end of `Statistics.update_stats`). `record_order(quantity)` updates the two order-size spreads. `disruption_started()` and `disruption_ended()` are called by `Link.disruption`. `reset()` is below.

**Reading and printing (nothing is printed by default).** `simulate_sc_net` does not change, and its results dictionary gets no new keys: `supplychainnet["links"]` (and `Network.links`) already hold every link, and each link carries its `stats`.

- One link: `link.stats.get_statistics()`.
- Many links, mirroring `get_node_wise_performance` / `format_node_wise_performance` / `print_node_wise_performance`: `get_link_wise_performance(links)` returns one dict per link, `format_link_wise_performance(links)` returns the table as a string (same layout as the node table; each column headed by `link.name`, with the ID added if two names repeat), and `print_link_wise_performance(links)` prints it. An empty list prints the same kind of message as the node version.
- One site's view, with no new method: `print_link_wise_performance(node.buyers)` (who ordered from this site, and what they got) and `print_link_wise_performance(node.suppliers)` (what this site ordered, and from whom).

**Reset and warm-up.** `link.stats.reset()` follows the rules of §3.24:

- Running totals go to zero: everything in the stored table except `backorder`, plus both order-size spreads.
- `backorder` is kept: orders waiting at the reset are still waiting afterwards.
- `start_time` becomes `env.now`, so every average and the per-time-unit count start again from the reset.
- A disruption going on at the reset counts from the reset onward, and does not add to `disruptions` (it started before).
- Events are counted when they happen, as in `Statistics`. An order placed before the reset and received after it counts as received but not placed in the new window. The averages stay correct, because each divides by a count recorded at the same moment as its total.

A new `reset_stats(supplychainnet)` resets every node, customer demand and link in one call, with `Network.reset_stats()` as its wrapper. A warm-up becomes `simulate_sc_net(sc, sim_time=31)`, `reset_stats(sc)`, `simulate_sc_net(sc, sim_time=T + 1)`. Existing code that resets nodes one by one keeps working. No `warm_up=` option on `simulate_sc_net`: it would hide where the reset happens.

**What link statistics do not cover.**

- Customers: they do not order over links (`Demand` holds `demand_node` directly), so customer demand is not in any link. Each `Demand`'s own statistics already record it.
- Orders blocked before a link is chosen: when `place_order` finds no supplier that can take the order, no link was chosen, so the order is not counted on any link. Only orders blocked by the second check in `InventoryNode.process_order` land in `blocked`. Raw-material links never record `blocked`: `Manufacturer.process_order` plans nothing when a raw material has no supplier that can take the order, and `process_order_raw` has no check.
- Units dropped on arrival: `InventoryNode.process_order` records only the units accepted, at both ends, so a separate "fulfilled by the supplier" figure would equal `fulfillment_received`. A per-link count of dropped units can be added later.
- A link set to `"inactive"` by hand (as some tests do) rather than by `Link.disruption`: its disrupted time is not counted.

**New public names.** `LinkStatistics` (in `core.__all__`), and `get_link_wise_performance`, `format_link_wise_performance`, `print_link_wise_performance` and `reset_stats` (in `utilities.__all__`), each also added to the import block and `__all__` of `Components/__init__.py`. `Network.reset_stats()` is a method.

**Docs.**

- `docs/glossary.md` first, before any code uses the words: **warm-up**, **waiting time**, **order cycle time**, **fill rate** (and order fill rate), **availability**, **bullwhip effect**.
- Google-style docstrings in plain language for every new class, method and function; the module pages of the API reference pick them up.
- `docs/api-reference/api-intro.md`: a short section on reading link statistics, and `LinkStatistics` in the library hierarchy.
- A new example `examples/py/link_statistics.py` (a buyer with two suppliers), with label-only comments. `intro_simple.py` and its sample output stay as they are.

**Tests.**

1. Nothing else changes. Before writing any code, take every node's `get_statistics()` from a few fixed-seed networks (intro_simple, a buyer with two suppliers, a manufacturer with raw-material suppliers) from the current code and store them as expected values; after the change they must match exactly. `intro_simple.py` still gives `-4435.0`, and the anyLogistix validation figures do not move.
2. Links add up to nodes, at sites with no customer demands: each site's `demand_placed`, `fulfillment_received`, `transportation_cost` and `inventory_spend_cost` equal the sums over its supplier links. On the supplier side, the sums of `demand_placed` and `shortage` over its buyer links equal its `demand_received` and `shortage`. Checked for both `InventoryNode.process_order` and `Manufacturer.process_order_raw`.
3. Each statistic in a small network with fixed lead times, so every number can be worked out by hand: a supplier with too little stock (`waited` and `shortage` go up; `backorder` is `[1, q]` during the wait and `[0, 0]` after; `waiting_time` is the exact wait); `lead_time` and `avg_lead_time`; `blocked` (the link disrupted when the order is placed: `blocked` goes up, `demand_placed` and `backorder` do not); `disruptions`, `disrupted_time` and `availability` with fixed disruption and recovery times, including a read during a disruption; `orders_per_time_unit`, `fill_rate` and `order_fill_rate`; `order_size_std` and `units_per_time_unit_std` on a known order sequence, including empty time units and the time unit still in progress.
4. Reset: totals to zero, `backorder` kept, `start_time` moved, an ongoing disruption counted only from the reset. `reset_stats(sc)` and `Network.reset_stats()` reset every node, customer demand and link.
5. Reading and printing: `link.stats.get_statistics()` has every key; `get_link_wise_performance` returns one dict per link; `format_link_wise_performance` returns the table; `print_link_wise_performance` works with `node.buyers` and `node.suppliers`, and with an empty list. `link.get_statistics()` still returns only `status`.
6. The existing test suite passes.

**Settled during review (2026-10-15).**

- `Manufacturer.process_order_raw` recorded the buyer's `demand_placed` and `transportation_cost` only once the supplier had served the order. Fixed first, in §3.25, so both kinds of site record them when the order is placed and every link statistic recorded at placement uses the same moment.
- Values that are undefined (a denominator of zero) are `None`, decided when the value is read; nothing is stored for them.
- Spreads use the sample standard deviation (divides by n − 1, as pandas and Excel's `STDEV.S` do), decided 2026-10-16.

**Follow-up.** The probability-based supplier-selection policy gets its own entry (§6.10). It will use these statistics in its tests (share of orders per link).

**Implemented as designed (2026-10-16)**, in the six steps of the plan (baseline, glossary, `LinkStatistics` and its recording calls, utilities, tests, docs). Details settled in the code:

- `LinkStatistics` sits next to `Statistics` in `core.py` and is created in `Link.__init__` before the link registers with its sites. Its `_stats_keys` and `_live_keys` (`["backorder"]`) are class level; no subclass extends them, so they are not cloned.
- Recording sits next to each matching node call, so the two cannot drift apart: `blocked` in the second check of `InventoryNode.process_order`; `shortage`, `demand_placed`, `transportation_cost` and `record_order` at placement; `backorder` and `waited` where `order_waits` is true; on arrival, `fulfillment_received`, `inventory_spend_cost`, `waiting_time` and `lead_time`. The wait is kept in a local `waited_for` (0 for an order served at once). The node's own `waiting_time` is still added when the supplier serves the order, as before.
- `LinkStatistics.update_stats` accepts only the stored totals. An unknown name, or a value worked out when read (`fill_rate`, say), gets the unknown-name warning, rather than the error `Statistics.update_stats` would raise on a property.
- Spreads: Welford's method, three numbers each. Empty time units are added in one step by combining the values so far with a group of zeros; a reading works on a copy. Time units are `floor(env.now − start_time + 1e-9)`, so rounding cannot put a moment in the time unit before.
- The node and link tables share `_collect_stats`, `_performance_rows` and `_format_performance` in `utilities.py`. The three link functions accept any collection of links (`node.suppliers`, `node.buyers`, `sc["links"].values()`).
- `reset_stats(supplychainnet)` resets `nodes`, `demands` and `links`; `Network.reset_stats()` returns the network, so calls chain.
- Docs: glossary entries **order cycle time**, **fill rate** (with order fill rate), **bullwhip effect** and **standard deviation**, and link names added to **Link**, **Lead time**, **Waiting time**, **Availability** and **Warm-up**; a "Reading link statistics" section in `docs/api-reference/api-intro.md`; the four new functions on the utilities API page; the example `examples/py/link_statistics.py` (a retailer with two distributors, one link disrupted at random, the other distributor restocking slowly, a warm-up with `reset_stats`).

**Verified:**

- Nothing else changes. Before any code was written, every node's and customer demand's `get_statistics()`, each site's `on_hand`, inventory level and `pending_orders`, each link's `get_statistics()` and the network results were stored for 19 networks with fixed seeds (intro_simple; five seeds of a distributor with two suppliers and random site and link disruptions; three warm-ups saved at the reset and at the end; a manufacturer whose raw-material supplier is too small (§3.27); three seeds of a manufacturer with two raw materials and three raw-material suppliers; three seeds of retailers with three suppliers each, chosen by cost (fixed) and by lead time (dynamic)). After the change all are identical, as are the outputs of `intro_simple.py` (`profit: -4435.0`), `sc_with_factory.py`, `hybrid_big_sc.py` (including its node table, now built by the shared code) and `newsvendor.py`, and the 30 pharma replications.
- `pytest` — 337/337 passing, also with `-W error::UserWarning`. New `TestLinkStatistics` (19 tests) and `TestLinkStatisticsAddUpToNodes` (2 tests, 3 seeds each) in `tests/test_core.py`, and 6 tests in `tests/test_utilities.py`, covering items 2 to 5 of the list above. Seven deliberate mistakes (waiting time added when served, link backorder never reduced, reset clearing the backorder, disruption end not recorded, raw-material orders not recorded, empty time units left out, fill rate by orders instead of units) each make a test fail.
- Both spreads match `statistics.stdev` on a list of the same values in 300 random cases (largest difference 4e-15).

### 6.9 More node statistics: disruptions, inventory over time, orders that end badly, a clock ✅ Resolved
Requested by the user while §6.8 was being designed. `Statistics`, `Inventory.update_carry_cost`, `Node.disruption`, `Node.place_order`, both `process_order` methods, `Manufacturer.process_order`, `Demand`, `simulate_sc_net`. To be done **before** §6.8 (user, 2026-10-16): it builds the shared tools (a clock that `reset()` restarts, a disruption timer, a running sum of value × time), and §6.8 then reuses them for links. Two separate changes, so each stays easy to review.

**Purpose.** Node statistics count orders, units and costs, but say nothing about disruptions apart from destroyed units, cannot give an exact average inventory level, have no record of customer units that were never delivered or of delivered units that had to be dropped, and have no clock, so nothing can be expressed per time unit.

**Kinds of value.** *Stored* values are running totals updated by the code where the event happens. *Worked-out* values are properties listed in `_stats_keys`, so `get_statistics()` includes them; they are computed when read, from the totals up to that moment, and are `None` when there is nothing to divide by (or, for the inventory values, for an infinite inventory and for a customer demand, which has none). Every node has all of them, because all nodes share `Statistics`.

**Group 1: disruptions.**

| Statistic | Kind | Meaning | Recorded in |
|---|---|---|---|
| `disruptions` | stored, count | Number of disruptions of the node | `Node.disruption`, when `node_status` becomes `"inactive"` (both the timed and the random path) |
| `disrupted_time` | stored, time units | Time spent disrupted. When read during a disruption, the time so far is included | `Node.disruption`, on recovery |
| `blocked` | stored, `[orders, units]` | Replenishment orders this site could not place because every supplier it has (or the link to it) was disrupted. Not counted for a site with no supplier at all (see below). Not lost: the site orders again once a supplier or a link recovers (§3.23), sizing the new order from its inventory position then | `Node.place_order` (the `not can_place_order()` branch, units = `quantity`); the second check in `InventoryNode.process_order` (units after the capacity clamp); `Manufacturer.process_order` when a raw material has no supplier (units = product units). The three paths are exclusive, so each order is counted once |
| `availability` | worked out | Share of time the node was working: `1 − disrupted_time / elapsed_time` | |

**Group 2: inventory over time.** `Inventory.update_carry_cost` already runs before every change of the inventory level (`put`, `get`, expiry, `destroy`) and works out `level × time since the last update` before multiplying by the holding cost. It now also keeps that product without the holding cost, and the time spent at level 0, on the `Inventory` (next to `carry_cost`). The level only changes at events, so these sums are exact.

| Statistic | Kind | Meaning |
|---|---|---|
| `inventory_level_time` | stored (on the inventory, read up to now) | Running sum of inventory level × time, in unit time units. 10 units for 3 time units and 4 units for 2 more give 38. The holding cost is this sum times the holding cost per unit per time unit |
| `zero_inventory_time` | stored (same) | Time the inventory level was 0 (within a rounding tolerance of 1e-9) |
| `avg_inventory_level` | worked out | `inventory_level_time / elapsed_time` (38 / 5 = 7.6 in the example). Exact, unlike an average of once-per-time-unit samples, and works when the holding cost is 0 |
| `zero_inventory_share` | worked out | `zero_inventory_time / elapsed_time` |

`inventory_level_time` is public, not only its average, because totals can be added across sites and across periods and averages cannot. Reading either value includes the stretch since the last update without changing anything stored. The glossary tells us to avoid "stockout", hence the `zero_inventory_` names.

**Group 3: orders that end badly.**

| Statistic | Kind | Meaning | Recorded in |
|---|---|---|---|
| `lost_sales` | stored, `[orders, units]` | Customer units the site never delivered, recorded at the site. A customer with no tolerance who finds too few units gets none, so the whole order is lost (`shortage` records only the missing units); the rest of a "take what is there" order (`consume_available`); an order too big for the site ever to hold; what a waiting customer was still owed when their tolerance ran out. An order counts once, however many of its units were lost | `_serve_no_tolerance` (`[1, order_quantity]`), `_serve_partial_consume` (`[1, order_quantity − available]`), `_discard_unservable` (`[1, order_quantity]`), the "customer leaves" branch of `wait_for_order` (`[1, units still owed]`) |
| `dropped_qty` | stored, units | Units of a delivery that did not fit in the inventory and that no waiting customer could take. The buyer pays only for the units it accepts, and the supplier is credited only for those, so these units carry no cost in the statistics; this makes them visible | The safety stop in `InventoryNode.process_order` (today a log warning only) |
| `waited` | stored, `[orders, units]` | Orders that had to wait at this site, from customers and from other sites, as with `backorder` | `_enqueue_for_tolerance` (customers); where `order_waits` is true in `InventoryNode.process_order` and `Manufacturer.process_order_raw`, at the supplier site |
| `waiting_time` | stored, time units | Total time those orders waited until their units left the inventory | `wait_for_order` when a waiting customer is served in full (the time the order arrived is kept in the process); after `yield event` in both `process_order` methods |
| `avg_waiting_time` | worked out | `waiting_time / demand_fulfilled[0]`: average wait per order served, with orders served at once counting as 0 (the same rule as for links). Customers who gave up are not in it | |

Everything a site lost is `lost_sales + disruption_lost_sales` (§3.26). A supplier's waiting time for orders from other sites equals the sum of `waiting_time` over its buyer links (§6.8) once every order has arrived: the supplier adds an order's wait when it serves it, the link when the order arrives.

**Group 4: a clock.**

| Statistic | Kind | Meaning |
|---|---|---|
| `start_time` | stored, a time | When counting began: the time the statistics were created, or the last `reset()` |
| `elapsed_time` | worked out | `env.now − start_time`; every average above divides by it |

**Not added (decided 2026-10-16):** a node-level fill rate (units served at once ÷ units ordered). It would need a further "units served at once" counter, because `shortage` cannot give it exactly; `lost_sales` and `shortage` already describe service. Holding cost for raw materials at a manufacturer, production busy time, and the time a raw-material supplier's mining is paused are left for later.

**Reset (§3.24 rules).** `reset()` zeroes the new totals (including `inventory_level_time` and `zero_inventory_time` on the inventory, next to `carry_cost` and `waste`), moves `start_time` to `env.now`, and, if the node is disrupted at the reset, counts that disruption's time from the reset onward without adding to `disruptions`. Worked-out values are properties, so both passes of `reset()` must skip them (setting a property without a setter raises an error); they follow from the totals.

**Network results.** `simulate_sc_net` adds up `lost_sales` and `disruption_lost_sales` over all sites, next to `shortage` and `backorders`, as `supplychainnet["lost_sales"]` and `supplychainnet["disruption_lost_sales"]`, and both join `Network._RESULT_KEYS`. The other new statistics stay per node. The run log gains two lines, so the pasted sample log in `examples/py/intro_simple.py` is updated.

**Docs.** `docs/glossary.md` first: **lost sales** (and how it differs from shortage and from disruption lost sales), **blocked order**, **availability**, **waiting time**, **average inventory level**, **dropped units**; the CLAUDE.md "words to avoid" mapping for lost demand points to lost sales. Plain-language docstrings for every new statistic, in the `Statistics` class and `__init__` docstrings. The `get_statistics()` sample output in `examples/py/intro_simple.py` (shown in `docs/ten_min.md`) gains the new keys. Notebooks and the pasted tables in `hybrid_big_sc.py` are left as they are.

**Tests.**

1. Nothing else changes: every existing node statistic of intro_simple, a network with a manufacturer, and the pharma model (30 replications) is identical before and after; `intro_simple.py` still gives `-4435.0`; the anyLogistix validation figures do not move.
2. Disruptions, with fixed disruption and recovery times: `disruptions`, `disrupted_time` and `availability`, including a read during a disruption and a reset during one.
3. `blocked` on each of the three paths, counted once per order; a blocked order adds nothing to `demand_placed`.
4. The 10-then-4 example: `inventory_level_time == 38`, `avg_inventory_level == 7.6` at time 5, with a holding cost of 0; `zero_inventory_time` for a site that runs empty; both `None` for an infinite supplier and a customer demand; a read between events includes the time since the last change.
5. `lost_sales` on each of the four paths (no tolerance, take what is there, too big to hold, gave up waiting after a partial delivery); a waiting customer who is served in full adds nothing.
6. `dropped_qty` for a delivery larger than the free capacity with no waiting customer.
7. `waited`, `waiting_time` and `avg_waiting_time` for a waiting customer and for an order from another site, with known waits.
8. Reset: all new totals zero, `start_time` moved, averages cover only the time since the reset.
9. Network results: `lost_sales` and `disruption_lost_sales` add up over sites and appear in `Network.results`.
10. The existing test suite passes.

**`blocked` counts disruptions only (user, 2026-10-16).** `can_place_order` is also false for a site with no supplier at all, or a manufacturer with no raw-material supplier for some raw material. That is a mistake in how the network is built, not a disruption: no recovery would ever let the order through, and it would be counted again at every check. So `Node.has_suppliers()` (overridden by `Manufacturer`: every raw material has a connected raw-material supplier, disrupted or not) tells the cases apart. `blocked` is recorded only when it is true. Otherwise `place_order` logs that the site has no supplier and, once per site, calls `warnings.warn` (text without the site's ID, so Python shows it once) and writes it to the log; `Manufacturer.process_order` records nothing. New `TestBlockedMeansDisruptedSuppliers` (3 tests; all fail without the change).

**Implemented as designed**, with two details settled in the code: the four inventory values are properties on `Statistics` that read `inventory.level_time` / `inventory.zero_level_time` (kept by `Inventory.update_carry_cost`) and add the stretch since the last update; `disrupted_time` is a property too (completed disruptions plus the one going on), with `Statistics.disruption_started()` / `disruption_ended()` called from `Node.disruption`.

**Verified:**

- `pytest` — 305/305 passing. New `TestMoreNodeStatistics` (20 tests covering every item in the list above) and `TestBlockedMeansDisruptedSuppliers` (3 tests); all fail on the old code.
- Nothing else changes: every existing statistic of every node and customer demand is identical before and after in seven networks (intro_simple; five seeds of a network with random node and link disruptions, two suppliers, waiting customers with partial deliveries, customers who take what is there, and customers with no tolerance; a manufacturer with a limited raw-material supplier). The 30 pharma replications of §3.24 are identical. `intro_simple.py`, `sc_with_factory.py` and `hybrid_big_sc.py` print the same output apart from the new statistics (and the environment's memory address).
- `examples/py/intro_simple.py` still gives `profit: -4435.0`; its two pasted samples (the `get_statistics()` output shown in `docs/ten_min.md`, and the run log) were updated, and the first was checked against a real run. In it, `inventory_level_time` is 2050 and the holding cost 410.0 = 0.2 × 2050, as expected.

**Found while verifying (not changed here).** In the manufacturer test network, a raw-material order larger than the raw-material supplier's capacity (292 units ordered from a supplier that holds at most 200) waits at the supplier for ever, so the manufacturer never produces again. The same happens with the old code. Customers have a guard for this case (`_discard_unservable`); replenishment orders do not. Recorded as §3.27 (deferred).

### 6.10 Probability-based supplier selection ✅ Resolved (designed and implemented 2026-10-16)
Requested by the user. A new supplier-selection policy, `SelectProbabilistic`, in `core.py`, with small changes to `SupplierSelectionPolicy`, `InventoryNode`, `Manufacturer` and `create_sc_net`. Builds on §6.8 (the link statistics show how the orders really split).

**Purpose.** The built in policies always choose a supplier by a fixed rule (the first, the first that can fill the order, the cheapest, the fastest). Many buyers in reality split their orders among suppliers in set shares, for example half to one distributor and the rest to two others. This policy chooses the supplier of each replenishment order at random, with a probability for each supplier. It is a general feature of the library. Its first user is the GNN optimization study (`GNN-optimization/STUDY_LOG.md`, Stage 1), where the probabilities are inputs that a gradient-based optimizer adjusts, so the expected results must change smoothly with them and runs must be repeatable with common random numbers. The study's simulations have no disruptions.

**How a supplier is chosen.** For every call to `select`, the policy draws exactly one number *u* from its own random number generator, uniform in [0, 1). The probabilities of the site's suppliers are stacked in the order of `node.suppliers` (the order the links were created in), and *u* picks the supplier whose stretch it falls in. With 0.5, 0.3 and 0.2, *u* < 0.5 picks the first supplier, 0.5 ≤ *u* < 0.8 the second, and 0.8 ≤ *u* < 1 the third. A supplier with probability 0 has a stretch of no length and is never chosen. If rounding leaves *u* past the end of the stack (the probabilities sum to 0.9999999, say), the last supplier with a probability above 0 is chosen. One draw per call, never more and never fewer, keeps the draws of two settings in line: with the same seed, changing a probability slightly changes only the orders whose *u* falls near a boundary.

**Where the probabilities come from.** A new site parameter `supplier_selection_param` (a dict, default `None`), on `InventoryNode` and as a key of the node dict in `create_sc_net`, in the same way `policy_param` serves the replenishment policy:

```python
{"ID": "R1", ..., "supplier_selection_policy": scm.SelectProbabilistic,
 "supplier_selection_param": {"probabilities": {"D1": 0.5, "D2": 0.3, "D3": 0.2},
                              "on_disruption": "rescale", "seed": 7}}
```

- `probabilities`: a dict from supplier ID (`link.source.ID`) to its probability. The policy finds each link's probability from `link.source.ID`, so the probabilities can be given before the links exist. A program that builds random networks picks the links first and writes the probabilities into each site's dict in the same loop. In a full grid (every distributor linked to every retailer), suppliers that are not to be used are listed with 0.
- `on_disruption` (optional, `"rescale"` by default, or `"block"`), see below.
- `seed` or `rng` (optional), see below.
- `SelectProbabilistic.set_probabilities(probabilities)` sets or replaces the probabilities later, for networks built from objects (a program may create a site before it knows its links). So `probabilities` may be left out at creation. It applies the same checks as at creation, and the link check below runs again at the next order (not at once, because more links may still be added).
- Not on `Link`: a setting used by only one policy is kept out of every link (decided by the user).

**How the parameter reaches the policy.** `SupplierSelectionPolicy.__init__(node, mode="fixed", params=None)`. The site passes `mode` only when `supplier_selection_mode` is given and `params` only when `supplier_selection_param` is given (see Mode below), so custom policies written as `__init__(self, node, mode="fixed")` keep working. Each policy declares `_param_keys`, as replenishment policies do. The four existing policies declare an empty tuple, `SelectProbabilistic` declares `probabilities`, `on_disruption`, `seed` and `rng`. Any other key gets the same warning as an unknown `policy_param` key (`warnings.warn` plus a log line, the text without the site's ID). `supplier_selection_param` must be a named parameter of `InventoryNode`, not left in `**kwargs`, because `**kwargs` goes on to `Inventory`, which rejects unknown names.

**Checks.** Errors are `ValueError`, raised through `global_logger` like the other setting checks.

- At creation and in `set_probabilities`: `probabilities` is a dict of numbers, none negative, at least one above 0, summing to 1 within a small tolerance (so 0.1 + 0.2 + 0.7 passes).
- Once the links are known: the probabilities have been given (at creation or with `set_probabilities`), every link in `node.suppliers` has a probability, every supplier ID in `probabilities` has a link, and no supplier has two links to this site (the ID would not say which link is meant). A link or ID left over is most likely a typo, so it is an error, not a probability of 0. This check runs in `create_sc_net` after all links are created, and again at the policy's first `select`, so models run with `env.run` are covered too. The base class gets a method for it that does nothing (name left to the builder), `SelectProbabilistic` overrides it, and `create_sc_net` calls it for every site.

**Disruptions.** Two choices, set by `on_disruption`. The candidates are the suppliers with a probability above 0.

- `"rescale"` (default): the draw is made over the candidates that can take an order (`can_take_order()`), with their probabilities scaled up to sum to 1, so their ratios are kept. With 0.5, 0.3, 0.2 and the first supplier disrupted, the other two get 0.6 and 0.4 for that order. The stored probabilities never change. If no candidate can take an order (only suppliers with probability 0 are working), the policy draws over all candidates and returns the chosen link although it is disrupted.
- `"block"`: the draw is made over all candidates with the given probabilities, and the chosen link is returned even if it is disrupted.

A disrupted link returned by `select` needs no new code: the second check in `InventoryNode.process_order` (`not supplier.can_take_order()`) already records `blocked` at the site and on that link and places nothing, and the site orders again when a supplier or link recovers (`wake_replenishment`) or when its inventory drops. When no supplier at all can take the order, `place_order` blocks it before `select` is called, as today, and no number is drawn.

The docs must say plainly that the probabilities are the shares while every supplier can take orders, and that with disruptions the shares of orders at the end of a run differ from them. Example for the docs: the first supplier is disrupted for 40% of the orders and the others never are. With `"rescale"` it gets about 30% of the orders sent (0.5 × 0.6), and the site never goes without. With `"block"` it still gets 50% of the draws, but about 37.5% of the orders sent (0.3 / 0.8), and the site goes without for the blocked orders. Only waiting for the drawn supplier to recover would keep 50% of the orders sent, and `place_order` must not wait (§3.23). The link statistics record the real shares.

**Random numbers.** `seed` (a number or a string, as in the Running Experiments guide) makes the policy create its own `random.Random(seed)`. `rng` uses a `random.Random` the user made. Giving both is an error. With neither, the policy draws one seed from the site's generator (`node.rng`, which is the library's `_rng` unless the site was given its own `rng`) when it is created, following the library's rule for random numbers (CLAUDE.md, RNG control). So `scm.set_seed`, or a seeded `rng` on the site, still makes the run repeatable. After that its draws come only from its own generator and disturb no other random numbers. Drawing that seed moves the later numbers of the site's generator by one, but only in models that use this policy, so no existing result changes.

**Mode.** "Fixed" makes no sense here (the first random choice would be kept for ever), and "dynamic" is what the policy does. Each policy keeps its own default (decided by the user, 2026-10-16), so the sites do not set one.

- `InventoryNode` and `Manufacturer` change `supplier_selection_mode="fixed"` to `None`, and pass the mode to the policy only when it is given (for example `policy(self, **kwargs)`, with `mode` and `params` in `kwargs` only when given). Left out, the policy's own default applies: `"fixed"` for the four existing policies (the default of `SupplierSelectionPolicy.__init__` and of `SelectFirst.__init__`, already today), `"dynamic"` for `SelectProbabilistic`. No `_default_mode` attribute is needed.
- `SelectProbabilistic.__init__` has `mode="dynamic"` and raises an error if it is given `"fixed"`.
- No result changes: the sites passed `"fixed"` until now, and every existing policy defaults to `"fixed"`. The examples that use `"dynamic"` (the milk case study, `examples/notebooks/performance_ana.ipynb`, one test) pass it explicitly. One effect for the CHANGELOG: a custom policy whose own `__init__(self, node, mode)` has no default for `mode` fails when the mode is left out. The guide's example does not override `__init__`.
- `SelectProbabilistic` does not use `_apply_mode` or `_active_suppliers`. The three-step pattern for new policies (CLAUDE.md) gets a note that a policy with its own disruption rule may skip them.

**Info.** `_info_keys` adds `probabilities` and `on_disruption`, so they appear in `get_info()` and saved network records. The generator is not included.

**Manufacturers: out of scope.** A `Manufacturer` takes `supplier_selection_policy` and stores it, but never uses it: for each raw material it orders from the first raw-material supplier of that raw material that can take the order (`_raw_material_links`). The built in policies also choose among all of a site's suppliers, while a manufacturer needs one choice per raw material. Here, `Manufacturer` takes the same `supplier_selection_mode` and `supplier_selection_param` as `InventoryNode` and builds its policy the same way (so a `supplier_selection_param` key in the dict style does not end in an unclear `TypeError` from `Inventory`). Given a policy other than `SelectFirst`, it warns once that the policy is not used (`warnings.warn` plus a log line, the text without the site's ID), and `docs/known-issues.md` gets an entry. The link check of `SelectProbabilistic` is not run for a manufacturer, since its policy is never used.

**Also out of scope.**

- The quota method of the study log (each order goes to the supplier furthest behind its share). It would send several orders in a row to a supplier that has just recovered, which may cause shortages there. The user will write it as a custom policy in the study if needed, and update decision D3 in STUDY_LOG.md.
- Probabilities that change during a run (given as functions).

**Docs.** A section in `docs/guide/supplier-selection.md` (scenario first, the dict example, building probabilities for a random network, both disruption choices with the example above, the seed). The sentence there saying fixed is the default stays true for the four existing policies, but should say so. Glossary entries for the new terms before they are used. `docs/known-issues.md`: drop the "Probability-based supplier selection" bullet from Next updates, and add the manufacturer limitation. Also `docs/about.md` (Features and Architecture lists), `docs/api-reference/api-intro.md` if it lists the policies, CHANGELOG, and the CLAUDE.md bullets on supplier-selection policies.

**Tests.**

- Nothing else changes: every existing test passes, `intro_simple.py` gives −4435.0, and the existing four policies behave the same with the mode left out, given as `"fixed"` and given as `"dynamic"`.
- Shares: over many orders without disruptions, the shares of orders over each link are close to the probabilities (statistical tolerance), checked with the link statistics.
- A supplier with probability 0 is never chosen, including when it is the only one working (the order is blocked).
- Same seed, same sequence of chosen suppliers; different seed, a different sequence; `scm.set_seed` without `seed` repeats a run.
- The policy's draws do not disturb other random numbers: with a given `seed`, a seeded disruption sequence is the same whatever the probabilities.
- Exactly one draw per `select`, also when only one candidate can take the order.
- Rescale: with one supplier disrupted, the others share its orders in their ratio. Block: a draw that lands on a disrupted supplier records `blocked` at the site and on that link, and the site orders again after the recovery.
- Errors: probabilities that do not sum to 1, a negative one, all zero, not a dict; a link without a probability and a probability without a link (in `create_sc_net`, and at the first order with `env.run`); two links from the same supplier; `seed` and `rng` together; `"fixed"` mode; an unknown `on_disruption` value. An unknown key warns.
- `set_probabilities` replaces the probabilities and applies the checks.
- Mode default: a custom policy without its own `__init__`, and one with `__init__(self, node, mode="fixed")`, still work with the mode left out and given.
- Probabilities never given (neither at creation nor with `set_probabilities`): a clear error in `create_sc_net` and at the first order.
- With neither `seed` nor `rng`, a site given its own seeded `rng` repeats its run.
- A `Manufacturer` given another policy, including `SelectProbabilistic` with `supplier_selection_param`, warns and does not fail.

**Settled by Claude after the design review (2026-10-16), for the user to check:** `probabilities` may be left out at creation; `Manufacturer` takes the same two settings and only warns; the seed comes from `node.rng` when neither `seed` nor `rng` is given.

**Left to the builder.** Names of helper methods, the tolerance, log and error texts, where in `core.py` the class goes (after `SelectFastest`), and the exact text of the docs.

**Implemented as designed.** Details settled in the code: the site builds its policy through `Node._make_selection_policy(policy, mode, params)`; the base class's link check is `check_links()`, and `create_sc_net` calls it only when the policy has it (for custom policies that do not derive from `SupplierSelectionPolicy`); the tolerance on the sum is 1e-6; with neither `seed` nor `rng`, the seed is `node.rng.getrandbits(64)`; a policy without settings words its warning "It takes no parameters."; `rng` must be a `random.Random`; the probabilities are copied, so later changes to the user's dict have no effect. The Supplier Selection guide has a new section "Choosing suppliers at random", with the 40% example checked by simulation (D1 got 30.2% of the orders sent with `"rescale"`, 37.6% with `"block"`).

**Fixed after the final review (2026-10-16).** A `seed` or `rng` of `None` now counts as not given (before, `seed=None` seeded from the operating system, so `scm.set_seed` no longer repeated the run). A numpy integer seed is turned into a Python `int`, and a seed that is not a number or a string raises a clear error. A manufacturer warns that its policy is not used before the policy checks its settings, so the warning is shown even when the settings are wrong.

**Verified:**

- `pytest`: 388/388 passing (48 new tests in `TestSelectionPolicySettings`, `TestSelectProbabilistic`, `TestSelectProbabilisticInNetworks`). `intro_simple.py` gives `profit: -4435.0`.
- Nothing else changes: against 0.4.0 (`ac1b97a`), the printed output of the five scripts in `examples/py/`, the text output of every cell of the notebooks `EOQ_est`, `case_study_pharma`, `different_replenish_policies_anylogistix` (the anyLogistix validation), `newsvendor`, `safety_inv_est` and `simple_supplier_n_factory`, and 30 pharmacy replications are identical (after removing file paths and memory addresses). `performance_ana` reached the 1200 second limit per cell in its timing benchmark in both versions, with the same output up to there.
- `mkdocs build` gives no new warnings.

**Deferred (minor, from the final review):** a link added after the first check gives a bare `KeyError` instead of the clear message; an unused `SelectProbabilistic` on a manufacturer without a seed still draws one number from the manufacturer's generator; `get_sc_net_info` prints the policy's name, not its probabilities; the guide's section on writing your own policy does not mention `self.params`, `_param_keys` or `check_links`; a few tests listed above are not written (a probability without a link and probabilities never given, both found by `create_sc_net`; block mode ordering again after the recovery; the four original policies with `"fixed"` and `"dynamic"` given explicitly); the word "pool" in a comment of `SelectProbabilistic.select`.

### 6.11 Check that the whole network is valid ⏸️ Planned (user, 2026-10-16)
To be discussed and designed after §6.8 (link statistics) and §6.10 (probability-based supplier selection).

**The idea.** Each class already checks its own settings when it is created (`Node`, `Link`, the replenishment and supplier-selection policies, `Demand`), but nothing checks the network as a whole once the user has given its nodes and links. A whole-network check would look at things no single class can see:

- **Every node is connected:** each site can order from someone (or is a raw-material supplier) and supplies someone (or serves customers); each customer demand is attached to a site that can be replenished; no site is left on its own.
- **Valid settings, together:** replenishment and supplier-selection policies and their parameters, and combinations that only make sense together (for example a manufacturer with a raw-material supplier for every raw material, or capacities along each link as in §3.27).
- **Units flow towards the customers:** no cycle such as distributor D1 ordering from D2 while D2 orders from D1, and from every raw-material supplier the units can reach some customer.

**Assessment (2026-10-16): a good idea.** Mistakes are found before a long run, in one report that lists every problem rather than the first one met, and checks that need the whole network (cycles, whether units can reach customers) cannot be done by any single class.

**Questions for the design:**

- When it runs (in `create_sc_net`, at the start of `simulate_sc_net`, or as `Network.validate()` that users can also call), and which problems are errors that stop the run and which are warnings.
- Cycles: `docs/known-issues.md` says the library does not check for loops and gives the example of two distributors linked to each other to cover shortages. Moving units sideways between sites at the same level (lateral transshipment) is a real practice, so the check may need to tell such links apart from cycles that keep units from ever reaching a customer.
- Whether the existing checks spread over the classes, and the §3.27 capacity warning, move into it, and how direct instantiation (no `create_sc_net`) gets the same checks.

**Deferred to this work: call each `Demand` function only once when it is created (user, 2026-10-16).** `Demand.__init__` calls each of its four functions (`order_arrival_model`, `order_quantity_model`, `delivery_cost`, `lead_time`) twice: once in `ensure_numeric_callable`, which already checks that it returns a number, and again in four leftover `validate_number(..., value=f())` lines. The second call is redundant, and a function that returns the next value of a list skips two values instead of one. Removing the four lines was tried for 0.4.0 and undone, because it changes results. A seeded run whose demand functions use random numbers then draws one random number fewer per customer demand, so every later draw shifts. The Estimating Safety Stock example gave a safety stock level of 1279.48 instead of the published 1260.80 (average inventory level 6145.63 instead of 6115.08). The newsvendor example and the pharmacy case study seed random demand too. Do it together with §6.11, which reworks the checks made at creation anyway, then rerun those examples and update their pages. Two tests change with it: `_scripted_seq` callers pad with one value instead of two, and `TestLinkStatisticsAddUpToNodes.test_manufacturer_with_two_raw_materials` must require orders from S2 over its three seeds together, not in each one (with one draw fewer, seed 1 sends S2 no order).

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
5. **§3.27 replenishment orders larger than the supplier's capacity.** Ship complete stays the default; partial shipments and "ship what is there, cancel the rest" are to be added next (§6.8 and §6.10 are done). Until then, models assume each supplier can hold what its buyers order.
6. **§6.11 check that the whole network is valid** (connections, settings, units flowing towards customers, no cycles). To be designed after §3.27 (§6.8 and §6.10 are done). Calling each `Demand` function only once at creation is deferred to the same work, because it shifts the random numbers of seeded examples (see §6.11).

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
