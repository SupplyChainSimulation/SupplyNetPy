# Release history

Changes to SupplyNetPy, newest first. The library was first published on PyPI
on 2025-08-21 (version 0.1.0).

Each entry is tagged: **[NEW]** a new feature, **[FIX]** a bug fix,
**[CHANGE]** a change in behavior, **[BREAKING]** a change that may need
action from you, and **[DOCS]** documentation only.

## Unreleased

* **[NEW]** A replenishment policy now warns about keys in `policy_param`
  that it does not use, and asks whether another policy was meant. For
  example, `'T'` is read only by the periodic policy, so passing it to the
  (s, S) policy now gives a warning instead of being silently ignored.
* **[CHANGE]** Problems in how a model is set up are now shown with Python's
  warnings, so they appear even when logging is off. They are still written to
  the trace log. This covers the unused policy parameters above, a manufacturer
  without a supplier for every raw material, an unknown statistic name passed
  to `update_stats`, and these `simulate_sc_net` calls: a `sim_time` that is not
  later than the current time, `logging=(start, stop)` (deprecated, now a
  `FutureWarning`), and `logging=(start, stop)` together with `log_window`.
  Events during a run, such as a delivery that does not fit in the inventory,
  are still only logged.

## 0.2.1 (2026-10-12)

Results change for networks with disruptions. Networks without disruptions,
such as the quickstart example, give the same results as before.

* **[FIX]** A site whose replenishment order was blocked by a disruption now
  orders as soon as its supplier, or the link to it, recovers. Before, a
  replenishment policy without a review period could stop ordering for good. If
  the site had no units left, nothing woke the policy again, even after the
  supplier recovered.
* **[FIX]** Supplier-selection policies now skip a supplier whose site is
  disrupted, not only one whose link is disrupted. Before, a site with two
  suppliers could send its order to the disrupted one and lose it, while the
  other supplier was working.
* **[CHANGE]** `place_order` now checks that some supplier can take the order
  before choosing one. If none can, no order is placed. New methods
  `Link.can_take_order`, `Node.can_place_order`, `Node.wake_replenishment` and
  `Node.add_buyer_link`, and a new list `Node.buyers` of the links to a node's
  buyers.
* **[FIX]** The performance table (`get_node_wise_performance`,
  `format_node_wise_performance`, `print_node_wise_performance`) now shows
  every metric that any node has. Before, it showed only the metrics of the
  first node in the list, so a raw-material supplier's mining figures were left
  out when another node came first. Two nodes with the same name now each get
  a column; the second is told apart by its ID.
* **[FIX]** `disable_logging` and `set_log_file` now close the log file they
  stop writing to. Before, the file stayed open until the program ended, which
  caused a `ResourceWarning` and, on Windows, kept the file locked.

## 0.2.0 (2026-10-11)

Most of these fixes come from
[issue #1](https://github.com/SupplyChainSimulation/SupplyNetPy/issues/1), reported by
[@ashwingaikwadiby](https://github.com/ashwingaikwadiby). Results
change for networks with manufacturers, raw-material suppliers with finite
inventory, perishable goods, customers who wait, or replenishment orders that
have to wait at a supplier. Simple networks, such as the quickstart example,
give the same results as before.

* **[FIX]** A replenishment order that has to wait at its supplier is now a
  backorder there only while it waits, and is no longer counted twice in the
  supplier's inventory position. Before, the supplier ordered too much, kept
  the extra units for the rest of the run, and its backorders were never
  cleared.
* **[FIX]** A manufacturer now keeps making production batches until every
  planned unit is made, orders raw material for every planned unit, and carries
  on when units leave its full inventory. Before, it could stop producing for
  good, with raw material left unused or with orders waiting forever.
* **[FIX]** A raw-material supplier with finite inventory starts mining again as
  soon as its inventory drops. Before, once its inventory had been full it never
  mined again, and manufacturers buying from it waited forever.
* **[FIX]** Perishable goods. An order now gets the batches that are really in
  inventory when it is filled, oldest first. Expired units are thrown away at
  once and are no longer shipped to an order that was waiting, and destroyed
  units are removed at once too. Before, an order that had to wait could lose
  units, and expired units could be shipped.
* **[FIX]** Customers who wait (`tolerance` above 0) now leave as soon as their
  tolerance runs out, and their backorders are cleared when they leave. All
  waiting customers are woken when units arrive, two waiting customers can no
  longer take the same units, and a partial delivery of 0 units no longer
  crashes.
* **[FIX]** A waiting customer's shortage is recorded once, when the order
  arrives. Before, it was recorded again at every check, so shortage figures
  were too high.
* **[FIX]** A supplier whose site is disrupted is no longer counted as short for
  orders it never receives.
* **[FIX]** `Inventory.destroy()` now wakes a raw-material supplier (to mine
  again) and a manufacturer (to make more). It still does not wake a
  replenishment policy.
* **[NEW]** `Inventory.get()` takes a `site_order` argument, and
  `Inventory.waiting_orders()` and `Inventory.waiting_site_orders()` report the
  units asked for by orders still waiting at an inventory.
* **[DOCS]** The (R, Q) policy (`RQReplenishment`) never used `safety_stock`, so
  passing it had no effect. The documentation no longer says that it does.
* **[DOCS]** A new Glossary page defines one word for each idea, and the
  documentation, docstrings and code comments now use those words. The API
  reference now lists every result of `simulate_sc_net`, and no longer shows
  raw markup from the docstrings.
* **[DOCS]** Several documentation pages described their examples wrongly, and
  are corrected. The complex network example now has the links shown in its
  picture, lead times that differ as intended, and a fixed seed.

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
