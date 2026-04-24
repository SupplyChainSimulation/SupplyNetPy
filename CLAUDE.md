# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

SupplyNetPy is a Python library for discrete-event simulation of supply chains and inventory systems. It is a thin domain layer on top of [SimPy](https://simpy.readthedocs.io/): every node, link, replenishment policy, and demand generator is a SimPy process, and simulation time is advanced by `env.run()` (or the `simulate_sc_net` wrapper).

The public import surface is `SupplyNetPy.Components`, conventionally aliased as `scm`. `Components/__init__.py` re-exports an **explicit, curated** list of names from `core`, `logger`, and `utilities`, so users write `scm.Supplier`, `scm.SSReplenishment`, `scm.create_sc_net`, etc. Wildcard imports were removed in favor of `__all__` on every submodule — module-level imports (`simpy`, `random`, `copy`, `networkx`, `matplotlib.pyplot`, `logging`) and internal state (`global_logger`, `_rng`, `_LOGGER_KWARGS`, `_NODE_KWARGS`) are deliberately not reachable as `scm.*`.

## Common commands

```bash
# Install in editable mode for development
pip install -e .

# Run the test suite (CI runs this on push/PR to main, Python 3.11)
pytest

# Run a single test file / test class / test
pytest tests/test_core.py
pytest tests/test_core.py::TestRawMaterial
pytest tests/test_core.py::TestRawMaterial::test_raw_material_init

# Run the canonical quick-start example as a sanity check.
# Expected: profit = -4435.0. Any change that touches core semantics should preserve this.
python examples/py/intro_simple.py

# Build the distribution (hatchling)
python -m build

# Build and serve docs locally
pip install -r docs/requirements.txt
mkdocs serve
mkdocs build
```

CI (`.github/workflows/ci.yml`) pins Python 3.11 and installs both `requirements.txt` and `docs/requirements.txt` before running `pytest` — match that setup when reproducing CI locally.

There is no linter or formatter configured; don't add one unless asked.

### Examples as a reference

`examples/py/intro_simple.py` is the canonical quick-start: it shows the dict-netlist style and the direct-instantiation style side by side, and includes a sample `stats.get_statistics()` output. When changing public APIs or docs, sanity-check against this file — if it would break, the change needs a matching update there. Additional worked examples live under `examples/py/` and `examples/notebooks/`.

## Architecture

### Module layout

```
src/SupplyNetPy/
├── __init__.py           # empty; users import SupplyNetPy.Components
└── Components/
    ├── __init__.py       # explicit re-exports (no wildcards); top-level __all__ lists the 33 public names
    ├── core.py           # all domain classes (~2600 lines); __all__ = 25 names
    ├── utilities.py      # create_sc_net, simulate_sc_net, visualize_sc_net, info helpers; __all__ = 7 names
    └── logger.py         # GlobalLogger — file + screen logging, toggleable per-node; __all__ = ["GlobalLogger"]

tests/
├── conftest.py           # prepends src/ to sys.path so tests resolve in-tree source even without `pip install -e .`
├── test_core.py
└── test_utilities.py
```

### The two construction styles

Users can build a network in two interchangeable ways, and `create_sc_net` accepts either:

1. **Dict netlists** (the README / quick-start style): pass lists of plain `dict`s for `nodes`, `links`, `demands`. `create_sc_net` creates its own `simpy.Environment` and instantiates the right concrete class by looking at `node_type` (`supplier` / `infinite_supplier` → `Supplier`; `manufacturer` / `factory` → `Manufacturer`; `distributor` / `warehouse` / `retailer` / `store` / `shop` → `InventoryNode`).
2. **Direct instantiation**: construct a `simpy.Environment` yourself, build `Supplier` / `InventoryNode` / `Manufacturer` / `Link` / `Demand` objects directly, then either call `env.run(until=...)` or pass them to `create_sc_net(env=env, ...)` and `simulate_sc_net`.

Mixing the two in the same network is not supported — if any item in `nodes`/`links`/`demands` is an object (not a dict), `create_sc_net` requires you to pass `env` explicitly.

### Class hierarchy (all in `core.py`)

- `NamedEntity`, `InfoMixin` — base mixins providing `__str__`/`__repr__` and `get_info()`/`get_statistics()` driven by `_info_keys` / `_stats_keys`.
- `Node(NamedEntity, InfoMixin)` — common base for every supply-chain actor. Owns the per-node `GlobalLogger`, handles disruption/recovery (`failure_p`, `node_disrupt_time`, `node_recovery_time`). Subclasses: `Supplier`, `InventoryNode`, `Manufacturer`, `Demand`.
- `Link` — transportation edge with `cost`, `lead_time` (callable), and its own disruption model.
- `Inventory` — SimPy `Container` wrapper; tracks perishables (shelf life, FIFO expiry via `perish_queue`), carrying cost, and optionally instantaneous levels. `level` and `capacity` are read-only `@property`s that delegate to the underlying `simpy.Container` — the container is the single source of truth, don't shadow either attribute on the wrapper.
- `InventoryReplenishment` (base) → `SSReplenishment` (s, S), `RQReplenishment` (R, Q), `PeriodicReplenishment`. Instantiated **by** the node that owns them — the user passes the class and a `policy_param` dict, not an instance.
- `SupplierSelectionPolicy` (base) → `SelectFirst`, `SelectAvailable`, `SelectCheapest`, `SelectFastest`. Same pattern: pass the class to the node.
- `Statistics` — per-node KPI tracker attached as `node.stats`. Exposes `get_statistics()` and optional periodic updates.
- `RawMaterial`, `Product` — product BOM primitives used by `Manufacturer`; `Product.raw_materials` is a list of `(RawMaterial, quantity)` tuples.

### Simulation lifecycle

1. `create_sc_net` validates IDs for duplicates, instantiates nodes/links/demands, wires them into a `supplychainnet` dict (`nodes`, `links`, `demands`, `env`, counts).
2. Each node registers its SimPy processes in its own `__init__` (e.g. `env.process(self.disruption())`, replenishment policy's `run()`, `Demand` generator).
3. `simulate_sc_net(supplychainnet, sim_time, logging=True)` calls `env.run(until=sim_time)` and then aggregates network-wide KPIs (total demand, shortage, backorders, revenue, profit, transportation cost, etc.) back into the same dict.
4. Per-node stats are always available via the `stats` attribute, e.g. `supplychainnet["nodes"]["D1"].stats.get_statistics()`.

### Logging

`GlobalLogger` is a thin wrapper over `logging` with separate file and screen handlers. Each `Node` gets its own logger named after `node.ID` (override via `logger_name=` kwarg). The default log file is `simulation_trace.log` in the working directory (gitignored via `*.log`). Node-level logging can be switched off by passing `logging=False` to a node, or by calling `node.logger.disable_logging()`.

## Conventions to preserve

- **Public API comes from `SupplyNetPy.Components`**, not from `SupplyNetPy` directly. Don't add exports to the top-level `__init__.py` without a reason. Every new public symbol must be added to three places: its module's `__all__`, the matching `from ... import` block in `Components/__init__.py`, and that file's top-level `__all__`. Internal plumbing (`global_logger`, `_rng`, the kwarg-whitelist sets) stays out.
- **Replenishment and supplier-selection policies are passed as classes**, not instances (`replenishment_policy=scm.SSReplenishment, policy_param={'s':100,'S':150}`). The owning node constructs them internally.
- **Lead times, arrival intervals, order quantities, disruption times** are passed as zero-arg callables (often `lambda: 2` or `lambda: random.expovariate(...)`) so they can be resampled per event. Scalars get auto-wrapped in `Node.__init__`, but APIs generally assume callables.
- Validation helpers `validate_positive`, `validate_non_negative`, `validate_number` live at the top of `core.py`; use them rather than hand-rolling checks so errors go through `global_logger`. `Link.__init__` and `Demand.__init__` additionally call `validate_number(name=..., value=callable())` after the scalar-auto-wrap, to catch callables that don't return numbers.
- `_info_keys` and `_stats_keys` drive `get_info()` / `get_statistics()`. When you add a new attribute that should appear in info/stats output, extend the relevant list in `__init__` (see how subclasses `.extend()` the parent's list). New cost attributes also need to be appended to `self.stats._cost_components` so `Statistics.update_stats` picks them up — there is no substring-match fallback.
- **RNG control.** `core.py` owns a module-level `_rng = random.Random()` and exports `set_seed(seed)`. `Node.__init__` and `Link.__init__` accept an optional `rng: random.Random = None`; `None` falls back to `_rng`. Probabilistic disruption calls `self.rng.random()`, never the global `random.random()`. Seeding once (`scm.set_seed(42)`) before building the network is enough to make disruption deterministic. New probabilistic draws inside the library should resolve RNG the same way.
- **Kwarg filtering.** Node subclasses (`Supplier`, `InventoryNode`, `Manufacturer`, `Demand`) take `**kwargs` and forward them to both `Node` (via `super().__init__`) and `Inventory`. Two whitelist sets in `core.py` keep these clean: `_LOGGER_KWARGS` (`log_to_file`, `log_file`, `log_to_screen`) and `_NODE_KWARGS` (`failure_p`, `node_disrupt_time`, `node_recovery_time`, `logging`, `rng`, `logger_name`). Every call site that constructs `Inventory` must strip both sets out first — `Inventory.__init__` has a strict signature and will `TypeError` on unknowns (this is how typos like `shelf_live=` get caught instead of silently ignored).
- **`Inventory.put` returns the accepted amount.** The container's free-capacity clamp and the infinite/full/non-positive early-return paths make it possible for a `put(amount)` to accept less than `amount`. Callers that pre-increment `node.inventory.on_hand` before `yield`ing on `put` (`InventoryNode.process_order`, `Manufacturer.produce_product`) must reconcile by subtracting the shortfall (`requested - accepted`) from `on_hand`. Suppliers clamp upstream and don't need to reconcile.
- **Pending orders are counted, not flagged.** `InventoryNode` and `Manufacturer` expose `self.pending_orders: int` (starts at 0). `process_order` (resp. `process_order_raw`) increments it right after the capacity-clamp / early-return guards, at the real dispatch point, and decrements it on completion. Concurrent in-flight orders are intentional — a node may have more than one outstanding order if the replenishment policy keeps triggering. **Do not** reintroduce a boolean guard against re-entry.
- **Backorder-aware inventory position.** Everywhere replenishment quantity is computed or clamped, the formula is `position = on_hand - stats.backorder[1]`, where `on_hand` is inventory position (shelf + in-transit). The capacity pre-check in both `process_order` methods uses `gross = on_hand - backorder[1]` too, so the clamp can't strand backordered orders behind a saturated shelf.
- **Link disruption blocks new dispatches, not in-flight ones.** Both `InventoryNode.process_order` and `Manufacturer.process_order_raw` check `supplier.status == "inactive"` (the `Link` object's status) before dispatching and short-circuit with a log line if the link is down. Ongoing shipments already past the dispatch gate are intentionally not interrupted — interrupting them would require per-shipment process tracking on the `Link`, which is deferred. The gate runs *before* shortage bookkeeping and before `pending_orders` is incremented, so a blocked order does not create phantom backorders on the supplier or inflate the in-flight counter.
- **Supplier-selection policies filter disrupted links.** Two helpers on the base `SupplierSelectionPolicy` enforce this uniformly across `SelectFirst` / `SelectAvailable` / `SelectCheapest` / `SelectFastest`: `_active_suppliers()` returns suppliers whose link is active (falling back to the full list if every link is down, so the dispatch gate handles the terminal case), and `_apply_mode(selected)` centralises the fixed/dynamic behavior. In `"fixed"` mode, if the locked supplier's link is inactive, the policy temporarily returns a dynamically-chosen active alternative *without* changing the lock — routing resumes through the locked supplier once its link recovers. When adding a new selection policy, follow the same three-step pattern: `candidates = self._active_suppliers()`, apply the criterion to `candidates`, then `return self._apply_mode(selected)`.
- Docstrings use Google style and feed `mkdocstrings` (see `mkdocs.yml`). Keep the `Parameters` / `Attributes` / `Returns` sections intact on public classes and functions — the docs site is generated from them.

## Known limitations (from docs/known-issues.md)

- No loop detection in the network graph — cyclic supply chains are silently allowed.
- Simultaneous events are resolved in SimPy's internal order (deterministic per run, but not user-controllable).
- No parallelized or real-time simulation.
