## SupplyNetPy API Reference

__SupplyNetPy__ includes a submodule called __Components__, which helps you create supply chain networks by providing their parts, such as nodes, links and customer demands, and assembling them into a network. The __Components__ module contains three submodules, __core__, __logger__ and __utilities__. The words used on these pages are explained in the [Glossary](../glossary.md).

The __core__ module creates the parts of a supply chain. It includes the classes _RawMaterial_, _Product_, _Inventory_, _Node_, _Link_, _Supplier_, _Manufacturer_, _InventoryNode_ and _Demand_, the statistics of a node (_Statistics_) and of a link (_LinkStatistics_), the replenishment policies (_SSReplenishment_, _RQReplenishment_, _PeriodicReplenishment_), and the supplier-selection policies (_SelectFirst_, _SelectAvailable_, _SelectCheapest_, _SelectFastest_). Every node created with these classes runs in a SimPy environment. The _Inventory_ class keeps the inventory of a node. By default, each inventory holds a single product. The _Inventory_ class keeps its units in a SimPy _Container_, and can also record how the inventory level changes. If you want a different kind of inventory with custom behavior, you can extend _Inventory_ or SimPy _Container_. The core module also exports `set_seed(seed)`, which seeds the random number generator the whole library uses for random disruptions, so runs can be repeated exactly.

The `node_type` argument of `Node`, `Supplier`, `InventoryNode` and `Demand` is checked against the `NodeType` enum (also exported from the core module). The accepted values are `infinite_supplier`, `supplier`, `manufacturer`, `factory`, `warehouse`, `distributor`, `retailer`, `store`, `shop` and `demand`. Some of them are different names for the same kind of node (`factory` is the same as `manufacturer`, and `warehouse`, `distributor`, `retailer`, `store` and `shop` all create an `InventoryNode`). You can pass either a string, in any letter case, or the enum member, which your editor can suggest as you type.

```python
scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier")
scm.Supplier(env=env, ID="S1", name="S1", node_type=scm.NodeType.SUPPLIER)
```

#### Writing a custom replenishment policy

The built in replenishment policies (_SSReplenishment_, _RQReplenishment_, _PeriodicReplenishment_) work with the node they belong to through a small set of helper methods on _Node_, rather than reading or changing the node's internal attributes directly. Your own `InventoryReplenishment` subclass should use the same helpers, so that it does not depend on how `Node` is built inside.

* `node.position()` returns the inventory position (the inventory level, plus the units in transit, minus the units the node still owes to other sites and to waiting customers). Use it instead of working the position out yourself from `node.inventory.on_hand` and `node.stats.backorder`.
* `node.place_order(quantity)` first checks that some supplier can take the order, then chooses a supplier with the node's supplier-selection policy and places the replenishment order. If every supplier, or the link to it, is disrupted, no order is placed. Use it instead of calling `selection_policy.select(...)` and `env.process(process_order(...))` yourself.
* `node.wait_for_drop()` waits until the node's inventory drops, or until one of its suppliers or the link to it recovers from a disruption, then gets ready for the next time. A policy that found no supplier to order from is woken this way, so it can check again. Use it as `yield from node.wait_for_drop()` in the policy's `run()` loop.

A built in policy warns when `policy_param` has a key it does not use, because the policy would otherwise ignore that key without telling anyone. To give your own policy the same check, list the keys it reads in a class attribute, for example `_param_keys = ("s", "S")`. A policy without such a list is not checked.

For supplier-selection policies, _Link_ offers `link.available_quantity()`, which gives the supplier's inventory level. A custom `SupplierSelectionPolicy` subclass can use it to compare suppliers without reaching past the link.

#### Modeling what a disruption does to stored inventory

A disruption in the real world can take many forms, such as a natural disaster, a power cut, contamination, theft or a strike, and each affects the units at a node differently. The disruption settings on `Node` (`failure_p` for random disruptions, `node_disrupt_time` for scheduled ones, and `node_recovery_time` for how long a disruption lasts) only mark the node as disrupted, so it receives no new orders, from other sites or from customers. A customer who arrives during a disruption is recorded as a lost sale in `disruption_lost_sales`. They do *not* describe what happens to the units already there.

If you want the simulation to also account for units that are physically lost in a disruption, set the `disruption_impact` argument when you create the node (and, if you choose `"destroy_fraction"`, also `disruption_loss_fraction`). The available choices are listed below.

| `disruption_impact` value | What happens the moment a disruption starts |
| --- | --- |
| `None` (the default) or `"none"` | The node is disrupted, but its units are left alone. |
| `"destroy_all"` | All units at the node are lost. For a `Manufacturer`, its raw materials are lost too, since the idea behind this choice is that every physical thing at the site is gone. Infinite suppliers (which never run out) are skipped, since destroying an unlimited supply has no meaning. |
| `"destroy_fraction"` | A share of the inventory level is lost. The share is given by `disruption_loss_fraction`, which can be a fixed number between 0 and 1 (for example `0.3` to lose 30%) or a small function that returns a different number each time, if you want random losses. |
| A function `f(node)` | For anything more specific. You write a short Python function describing the effect, and the simulator calls it with the node when a disruption starts. For example, a contamination that destroys only certain batches, damage that reduces capacity, or a lead time penalty that applies once the node recovers. |

The effect is applied **once**, exactly at the moment the node goes from active to inactive, both for scheduled (`node_disrupt_time`) and random (`failure_p`) disruptions. It is *not* applied again while the node stays disrupted. If you want a loss that grows over time during a disruption (slow spoilage from a long loss of cooling, ongoing theft), write that inside your own function, where you can start your own SimPy process and time it against `node_recovery_time`.

The two built in choices call `Inventory.destroy(amount, reason)`, a public method on `Inventory` that removes the units at once, even when orders are waiting at the node. For perishable goods, the oldest batches are destroyed first. One subtle but important detail is that `destroy` does **not** wake up the replenishment policy. New orders are not sent while the node is disrupted anyway, so waking the replenishment policy would only pile up replenishment orders that would all go out the moment the node recovers, flooding its supplier and distorting the simulation. It does wake a raw-material supplier, which then mines again to refill its inventory, and a manufacturer, which can then make more. If you write your own impact function that destroys units, call `Inventory.destroy(...)` for the same reasons, and do not change `level`, `on_hand` or `perish_queue` by hand.

The units destroyed (`destroyed_qty`) and their value (`destroyed_value`) are recorded in the node's `Statistics`. `destroyed_value` is one of the node's costs, so it is automatically included in `node_cost` and therefore in `profit`, and you do not need to subtract it yourself. In your own impact function, report losses the same way, with `node.stats.update_stats(destroyed_qty=qty, destroyed_value=qty * unit_cost)`, rather than inventing separate statistics that the simulator will not know about.

A short example.

```python
import random
import SupplyNetPy.Components as scm

# Destroy all units when a disruption starts, as in a natural disaster.
distributor = scm.InventoryNode(
    env=env, ID="D1", name="D1", node_type="warehouse",
    capacity=200, initial_level=120, inventory_holding_cost=0.2,
    replenishment_policy=scm.SSReplenishment, policy_param={'s': 100, 'S': 200},
    product_sell_price=10, product_buy_price=5,
    node_disrupt_time=lambda: 30, node_recovery_time=lambda: 5,
    disruption_impact="destroy_all",
)

# Like a power cut, each disruption spoils between 10% and 40% of the inventory level.
warehouse = scm.InventoryNode(
    ..., disruption_impact="destroy_fraction",
    disruption_loss_fraction=lambda: random.uniform(0.1, 0.4),
)
```

The __logger__ module keeps the simulation logs. It includes the _GlobalLogger_ class, a common logger for all the parts of the simulation. You can set it up to save logs to a file or to print them to the console. A `global_logger` instance for the whole package is also exported, so you can call `scm.global_logger.disable_logging()` or `scm.global_logger.enable_logging()` to switch all simulation logs off or on at once.

The __utilities__ module provides useful Python functions that save manual work. It contains functions for creating supply chains (`create_sc_net`), running simulations (`simulate_sc_net`), starting the statistics again after a warm-up (`reset_stats`), and inspecting or drawing the resulting network (`get_sc_net_info`, `print_node_wise_performance`, `print_link_wise_performance`, `visualize_sc_net`).

Note that `create_sc_net` accepts two interchangeable ways of building a network, plain `dict` descriptions or ready made `Node`, `Link` and `Demand` objects. But each of its `nodes`, `links` and `demands` lists must use only one of them. A list mixing dicts and ready made objects is rejected at once, because the dicts and the objects would otherwise run in two different SimPy environments. When any list contains ready made objects you must also pass `env` yourself, and each object's own `env` must be that same environment.

The public names of each submodule are listed explicitly in its `__all__`, and `SupplyNetPy.Components` exports exactly these names, with no wildcard imports. The modules the library itself imports (SimPy, NetworkX, Matplotlib and so on) and its internal constants are deliberately not reachable as `scm.<name>`.

#### Reading link statistics

Imagine a retailer that buys from two distributors. Its node statistics say how much it ordered and received in total, but not how much came from each distributor, how long each one made it wait, or how often each link was disrupted. Every link keeps its own statistics for this, in `link.stats`. They count the replenishment orders the buyer placed over the link, what arrived, the shortage and backorders at the supplier, the waiting time (how long orders waited at the supplier before they were sent), the lead time, the costs, and the disruptions of the link. From these totals they work out averages such as the fill rate (the share of the units ordered that the supplier sent at once, without the order having to wait), the order cycle time (waiting time plus lead time) and the availability of the link.

Nothing is printed unless you ask for it. Read one link with `link.stats.get_statistics()`, or several at once with `print_link_wise_performance(links)`, which prints the same kind of table as `print_node_wise_performance`. For the view of one site, pass its links. `node.suppliers` holds the links the site orders over, and `node.buyers` holds the links its buyers order over.

```python
retailer = sc["nodes"]["R1"]
scm.print_link_wise_performance(retailer.suppliers)           # what R1 ordered, and from whom
scm.print_link_wise_performance(sc["nodes"]["D1"].buyers)     # who ordered from D1
rows = scm.get_link_wise_performance(sc["links"].values())   # every link, as data
```

`get_link_wise_performance` returns the values as data, ready for a pandas DataFrame, and `format_link_wise_performance` returns the table as text. The full example is in `examples/py/link_statistics.py`.

Link statistics count replenishment orders only. Customers do not order over links, so customer demand is found in the statistics of each customer demand. The figures on the links of a site add up to the figures of the site itself, so the two can be checked against each other.

Two statistics describe how uneven the orders are, and they answer different questions. `order_size_std` is the standard deviation of the order sizes, and `units_per_time_unit_std` is the standard deviation of the units ordered in each time unit, where a time unit with no order counts as 0. A distributor that orders 60 units at time 3 and 60 units at time 7 has an `order_size_std` of 0, because every order is the same size, but a large `units_per_time_unit_std`, because its orders come in bursts. Compare `units_per_time_unit_std` along the supply chain to measure the bullwhip effect, the way orders become more uneven as they pass from the customers towards the raw-material suppliers.

For a warm-up, `reset_stats(sc)` starts the statistics of every node, customer demand and link again in one call, and `Network.reset_stats()` does the same for a `Network`.

```python
scm.simulate_sc_net(sc, sim_time=30)    # warm-up
scm.reset_stats(sc)
scm.simulate_sc_net(sc, sim_time=230)   # the measured period
```

#### SupplyNetPy Library Hierarchy

    SupplyNetPy
    ├── Components
    │   ├── core.py
    │   ├── logger.py
    │   ├── utilities.py
