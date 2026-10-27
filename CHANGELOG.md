# Release history

Changes to SupplyNetPy, newest first. The library was first published on PyPI
on 2025-08-21 (version 0.1.0).

Each entry is tagged: **[NEW]** a new feature, **[FIX]** a bug fix,
**[CHANGE]** a change in behavior, **[BREAKING]** a change that may need
action from you, and **[DOCS]** documentation only.

## 0.5.1 (2026-10-27)

Simulation results are the same as in 0.5.0, except for models in which a
disruption destroys units at a site whose replenishment policy has no
`period`. This release makes such a site order again when it recovers.

* **[FIX]** A site whose units were destroyed by a disruption
  (`disruption_impact`) now orders again when it recovers. Before, its
  replenishment policy was not woken, so a site with no units left waited
  until a buyer ordered from it or a customer waited for units. A site whose
  buyers had moved to other suppliers could stay empty for the rest of the
  run. A site now checks its inventory position whenever it recovers.
  Results change only for models where a disruption destroys units and the
  replenishment policy has no `period`.
* **[DOCS]** The Disruptions and Replenishment Policies guides say that a
  site checks its inventory position when it recovers, and why destroying
  units does not wake its replenishment policy. The Disruptions guide also
  lists the two cases in which a disrupted site can still order.

## 0.5.0 (2026-10-17)

Simulation results are the same as in 0.4.0. This release adds
probability-based supplier selection, and supplier-selection policies can now
take settings.

* **[NEW]** `SelectProbabilistic`, a supplier-selection policy that chooses
  the supplier of each replenishment order at random, with a probability for
  each supplier. The probabilities are given in the new site setting
  `supplier_selection_param`, keyed by supplier ID, and must sum to 1. When a
  supplier is disrupted, the others share its orders in their ratios
  (`on_disruption="rescale"`, the default), or the order is blocked
  (`"block"`). The policy draws one random number per order from its own
  random number generator (`seed` or `rng`), so its choices change no other
  random numbers. `create_sc_net` checks that every link to the site has a
  probability. See the Supplier Selection guide.
* **[CHANGE]** A site gives its supplier-selection policy a mode only when
  `supplier_selection_mode` is given, so each policy keeps its own default:
  "fixed" for the four existing policies, as before, and "dynamic" for
  `SelectProbabilistic`. Results are the same as in 0.4.0.
* **[BREAKING]** A custom supplier-selection policy whose own `__init__`
  takes `mode` without a default value now fails when the site is given no
  mode. Give `mode` a default, such as `mode="fixed"`. Policies that do not
  override `__init__` are not affected.
* **[CHANGE]** A built in supplier-selection policy given settings it does
  not use in `supplier_selection_param` warns about them, as replenishment
  policies do for `policy_param`. A manufacturer given a supplier-selection
  policy, a mode or settings warns that they are not used, since it does not
  use its policy yet.
* **[CHANGE]** `get_sc_net_info` shows the settings of each site's
  replenishment policy and supplier-selection policy, not only their names,
  for example `(s: 100, S: 150, first_review_delay: 0, period: 0)` or the
  probabilities of `SelectProbabilistic`. A distributor or retailer now
  reports its replenishment policy in `get_info()`, as a manufacturer already
  did.
* **[DOCS]** The Supplier Selection guide has two new sections. One shows how
  to choose suppliers at random with `SelectProbabilistic`, and the other how
  to give settings to a supplier-selection policy you write yourself
  (`self.params`, `_param_keys` and `check_links`). New glossary entries for probability-based supplier
  selection and selection probability. The Known Issues page says that a
  manufacturer does not use its supplier-selection policy yet.
* **[DOCS]** Level 3 headings in the guides and other pages are shown as plain
  headings. The grey box is kept for the classes and functions of the API
  reference.
* **[DOCS]** The source code shown in the API reference keeps its line breaks
  and indentation again.

## 0.4.0 (2026-10-16)

Simulation results are the same as in 0.3.0. This release adds statistics for
each link, and a User Guide with seven guides to common tasks.

* **[NEW]** Every link now keeps statistics, in `link.stats`. They count the
  replenishment orders the buyer placed over the link, what arrived, the
  shortage and backorders at the supplier, how long orders waited at the
  supplier, the lead time, the costs, and the disruptions of the link. From
  these they work out the average waiting time, lead time and order cycle
  time, the fill rate (the share of units the supplier sent without the
  order having to wait), the availability of the link, and two spreads of
  order sizes, one per order and one per time unit, for studying the
  bullwhip effect. Read them with `link.stats.get_statistics()`.
* **[NEW]** `get_link_wise_performance`, `format_link_wise_performance` and
  `print_link_wise_performance` give the statistics of several links as data,
  as text or printed, like the node versions. Pass `node.suppliers` to see what
  a site ordered and from whom, or `node.buyers` to see who ordered from it.
* **[NEW]** `reset_stats(supplychainnet)` and `Network.reset_stats()` start the
  statistics of every node, customer demand and link again in one call, for a
  warm-up.
* **[FIX]** A raw-material supplier given a perishable inventory
  (`inventory_type="perishable"`) now raises a clear error when it is created.
  SupplyNetPy does not model perishable raw materials yet. Before, the
  setting was accepted, and the run failed at the first mining with a message
  about a missing manufacturing date.
* **[CHANGE]** `SelectAvailable`, `SelectCheapest` and `SelectFastest` (and the
  base class `SupplierSelectionPolicy`) now default to fixed mode, as
  `SelectFirst` and every site already did. A site always passes its own
  `supplier_selection_mode`, so networks give the same results as before. Only
  a policy created directly, without a mode, behaves differently.
* **[DOCS]** A new User Guide with seven guides, on customer demand,
  replenishment policies, supplier selection, disruptions, perishable
  products, statistics and results (including link statistics and
  warm-ups), and running experiments. The longer sections of the API introduction moved
  into them, and the introduction is now a short overview of the modules.
* **[DOCS]** New glossary entries for order cycle time, fill rate, bullwhip
  effect, standard deviation, fixed and dynamic mode, and, in a new
  Experiments section, replication, seed, confidence interval and common
  random numbers. Also a new example,
  `examples/py/link_statistics.py`.
* **[DOCS]** The About page describes the newer features (customer demand
  options, supplier selection modes, perishable products, link statistics
  and reproducible experiments), links to the guides, and mentions the
  validation against anyLogistix. The home page lists the case studies, the
  User Guide, the known issues and the release history.
* **[DOCS]** The planned work on the known issues page is split into next
  updates (probability-based supplier selection, orders in smaller parts,
  checking the whole network, and the new entry for perishable raw
  materials) and long-term goals.

## 0.3.0 (2026-10-16)

This release adds new node statistics, fixes how statistics are reset for a
warm-up, and adds warnings for two mistakes in how a network is built.
Results stay the same for networks that are not reset during a run and have
no disrupted site with customers, such as the quickstart example. The three
fixes below say which results change.

* **[FIX]** Customers can no longer order from a disrupted site. Before, they
  were served from its inventory as usual, although a disrupted site takes no
  new replenishment orders. A customer who arrives while the site is
  disrupted now goes away, and the order is recorded in the new statistic
  `disruption_lost_sales`. It is kept apart from `shortage`, because a
  shortage is units the site did not have, and a disruption lost sale is an
  order the site could not take. Customers already waiting when the
  disruption starts are still served. Results change for networks in which a
  site with customers can be disrupted.
* **[FIX]** `stats.reset()`, used for a warm-up, now starts the counting again
  without changing the present. Before, it also set `backorder` and
  `inventory_level` to zero. A site with orders waiting at the reset then
  ordered too little, and its backorders went below zero once those orders
  were served. The holding cost is now brought up to date before the reset,
  so afterwards it covers only the time since the reset, also when the run
  was advanced with `env.run()`. The record of inventory levels
  (`inventory.instantaneous_levels`) also starts again. Results after a
  warm-up change when orders are waiting at the reset, or when the run was
  advanced with `env.run()`.
* **[FIX]** A manufacturer's raw-material order now counts in its
  `demand_placed` and `transportation_cost` when it is placed, as for every
  other site. Before, it counted only once the supplier served it. Totals at
  the end of a run change only for raw-material orders still waiting then.
* **[NEW]** Statistics about disruptions. `disruptions` and `disrupted_time`
  (including a disruption still going on when read), `availability` (the
  share of time the node was not disrupted), and `blocked` (replenishment
  orders a site could not place because every supplier it has, or the link
  to it, was disrupted).
* **[NEW]** Statistics about inventory over time. `avg_inventory_level` and
  `inventory_level_time` (inventory level times time), worked out exactly and
  apart from the holding cost, and `zero_inventory_time` and
  `zero_inventory_share` (how long the inventory level was zero).
* **[NEW]** Statistics about orders that end badly or wait. `lost_sales` (the
  customer units a site never delivered), `dropped_qty` (delivered units that
  did not fit in the inventory), and `waited`, `waiting_time` and
  `avg_waiting_time`, for customers and for orders from other sites.
* **[NEW]** Each node's statistics keep a clock. `start_time` is when counting
  began, and `elapsed_time` is the time since then. A reset moves
  `start_time`, so averages after a warm-up cover only the measured period.
  Averages are worked out when they are read and are `None` when there is
  nothing to divide by.
* **[NEW]** `simulate_sc_net` and `Network.results` add up `lost_sales` and
  `disruption_lost_sales` for the whole network.
* **[NEW]** `Node.has_suppliers()` tells whether a site has any supplier at
  all. For a manufacturer it checks that every raw material has one.
* **[CHANGE]** `get_statistics()` and the performance tables show the new
  statistics, so they have more rows.
* **[CHANGE]** Two new warnings for mistakes in how a network is built. A site
  with no supplier at all that tries to order is warned about once, and is
  not counted as `blocked`. A buyer that can order more than its supplier can
  hold is warned about when the link between them is created, and again when
  such an order is placed. A supplier sends an order only when it has all of
  it, so such an order can never be filled, and the buyer would wait for it
  for ever. The warning names both sites.
* **[DOCS]** New glossary entries for warm-up, disruption lost sales, lost
  sales, blocked order, waiting time, dropped units, average inventory level,
  availability and deadlock. The known issues page explains the deadlock
  above and lists two planned features, receiving such orders in smaller
  parts, and checking the whole network.

## 0.2.2 (2026-10-13)

Simulation results are the same as in 0.2.1. This release adds warnings for
mistakes in how a model is set up, and makes the source package smaller.

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
* **[CHANGE]** The source archive on PyPI now carries only the library, its
  tests, README, LICENSE and CHANGELOG, so it is about 115 KB instead of over
  4 MB. The docs and examples stay in the repository. The wheel is unchanged.
* **[DOCS]** The docs now say that a run stops just before its end time, so
  events due at exactly `sim_time` do not happen. This is how SimPy works. To
  include them, run to a slightly later time, such as `sim_time + 1`.

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
