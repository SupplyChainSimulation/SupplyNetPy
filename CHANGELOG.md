# Release history

Changes to SupplyNetPy, newest first. The library was first published on PyPI
on 2025-08-21 (version 0.1.0).

Each entry is tagged: **[NEW]** a new feature, **[FIX]** a bug fix,
**[CHANGE]** a change in behavior, **[BREAKING]** a change that may need
action from you, and **[DOCS]** documentation only.

## 0.1.12 (2026-05-31)

- **[FIX]** Replenishment orders that were bigger than the free space on the
  shelf no longer throw away the extra units. Previously, a node with waiting
  customers could order enough to refill the shelf and also cover them, and any
  units that did not fit were silently lost even though they had been paid for.
  In some cases this also pushed the node's inventory position below zero.
- **[CHANGE]** When arriving units are dropped because the shelf is full, a
  warning is now logged suggesting that the node's capacity may be too small.
- **[CHANGE]** A customer order that is bigger than the node's whole shelf,
  with no partial delivery accepted, is now recorded as lost demand right away.
  Before, it triggered a replenishment order that could never be served.
- **[DOCS]** Code comments and docstrings were rewritten in plainer language.

## 0.1.11 (2026-05-09)

- **[FIX]** Random node and link disruptions set with `failure_p` no longer
  happen almost immediately at time 0. The failure chance is now applied once
  per time unit, as documented.

## 0.1.10 (2026-05-06)

- **[NEW]** `Inventory.destroy()` removes stock (all of it, a fraction, or a
  custom amount) when a node is disrupted. Nodes accept a matching
  `disruption_impact` option. Destroyed units and their value appear in the
  node's statistics and count towards its cost.
- **[FIX]** Expiry of perishable stock (`Inventory.remove_expired`) now works
  correctly.
- **[DOCS]** Documentation wording was simplified throughout.

## 0.1.9 (2026-04-28)

- **[NEW]** `Network` wrapper around the supply-chain dictionary, with named
  access to nodes and results. The dictionary-based way of working still works.
- **[NEW]** `NodeType`, a list of the valid node types. Node types can be given
  either as text (`"retailer"`) or as a `NodeType` member.
- **[NEW]** `log_window=(start, stop)` option on `simulate_sc_net` to log only
  part of a run.
- **[BREAKING]** Python 3.9 or newer is now required. `networkx` and
  `matplotlib` are now declared as dependencies.
- **[CHANGE]** Logging is now opt-in. Creating nodes no longer opens (or
  overwrites) the trace file. `simulate_sc_net(logging=True)` turns it on for
  you.
- **[CHANGE]** The shortage statistic is now called `shortage`. The old name,
  `orders_shortage`, still works as an alias.
- **[CHANGE]** Expiry of perishable stock is now driven by the batches' expiry
  times instead of repeated checks, which makes large simulations faster.
- **[CHANGE]** The remaining items from the code review (see `REVIEW.md`) were
  resolved, and the test suite was expanded.

## 0.1.8 (2026-04-24)

- **[NEW]** `set_seed()` makes random disruptions repeatable.
- **[BREAKING]** `SupplyNetPy.Components` now exposes a fixed, documented list
  of names. Modules that used to be reachable by accident (such as
  `scm.simpy`) are no longer available through it.
- **[FIX]** A full code review fixed a set of correctness problems, including:
    - Expired perishable stock was not always removed correctly, so holding
      cost could keep being charged on stock that no longer existed.
    - A manufacturer could place duplicate orders for the same raw materials.
    - A customer's "demand fulfilled" figure was inflated when an order arrived
      in several partial shipments.
    - Cost totals could pick up unrelated values whose names happened to
      contain the word "cost".
    - Disrupted links were still used for new shipments, and
      supplier-selection policies did not take link status into account.
    - Adding stock to a full shelf could leave the inventory records out of
      step.
- **[CHANGE]** Misspelled node parameters (for example `shelf_live`) are now
  reported as an error instead of being silently ignored.
- **[CHANGE]** A much larger test suite was added.

## 0.1.7 (2026-03-13)

- **[NEW]** `record_inv_levels` option on `Inventory` to switch recording of
  inventory levels over time on or off (off by default).
- **[FIX]** Adding stock to an inventory that is already full is now handled
  safely.

## 0.1.6 (2025-11-19)

- **[FIX]** When adding stock would go over capacity, only the amount that fits
  is now added, instead of failing.

## 0.1.5 (2025-11-08)

- **[NEW]** `name` is now included in node statistics.
- **[CHANGE]** The minimum required Python version was relaxed.

## 0.1.2 to 0.1.4 (2025-09-15)

- **[FIX]** The wheel build target was added so the package builds correctly.
- **[CHANGE]** Package metadata (classifiers and author details) was corrected.

## 0.1.1 (2025-09-02)

- **[CHANGE]** Parameters that expect a "callable" (lead times, arrival
  intervals, and so on) now also accept a plain number such as `2` or `1.5`.

## 0.1.0 (2025-08-21)

First public release on PyPI. It included:

- Supply-chain building blocks: suppliers, manufacturers, inventory nodes
  (distributors and retailers), demand nodes, and links.
- Replenishment policies: (s, S), (R, Q), and periodic review (with or without
  safety stock).
- Supplier-selection policies: first, available, cheapest, and fastest.
- Perishable inventory, disruptions of nodes and links, and backorders with
  partial fulfilment.
- Node-level and network-level results (cost, revenue, profit, shortage), plus
  `create_sc_net` and `simulate_sc_net`.
- A documentation site, worked examples, and a unit-test suite.

## Before the first release

Development began in May 2024; the repository was moved from its earlier home
in July 2024. Internal versions 0.0.11 to 0.0.69 were used during development
and were never published on PyPI.
