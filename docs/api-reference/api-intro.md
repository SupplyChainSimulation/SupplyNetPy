## SupplyNetPy API Reference

__SupplyNetPy__ includes a sub-module called __Components__, which facilitates the creation of supply chain networks by providing essential components such as nodes, links, and demand, and assembling them into a network. The __Components__ module contains three sub-modules: __core__, __logger__, and __utilities__.

The __core__ module is responsible for creating supply chain components. It includes classes such as _RawMaterial_, _Product_, _Inventory_, _Node_, _Link_, _Supplier_, _Manufacturer_, _InventoryNode_, and _Demand_, the replenishment policies (_SSReplenishment_, _RQReplenishment_, _PeriodicReplenishment_), and the supplier-selection policies (_SelectFirst_, _SelectAvailable_, _SelectCheapest_, _SelectFastest_). Any new node created using these classes will be instantiated within a SimPy environment. The _Inventory_ class is responsible for monitoring inventories. By default, the classes in the core module support single-product inventories. The _Inventory_ class wraps a SimPy _Container_ to implement the basic behavior of an inventory, including routines to record inventory level changes. If users wish to create a different inventory type with custom behavior, they can do so by extending either _Inventory_ or SimPy _Container_. The core module also exports `set_seed(seed)` for seeding the library-wide default RNG used for probabilistic disruption, so runs can be made reproducible.

The `node_type` argument on `Node` / `Supplier` / `InventoryNode` / `Demand` is validated against the `NodeType` str-enum (also exported from the core module). Accepted values are `infinite_supplier`, `supplier`, `manufacturer`, `factory`, `warehouse`, `distributor`, `retailer`, `store`, `shop`, and `demand`. You can pass either a string (case-insensitive) or the enum member for IDE autocomplete:

```python
scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier")
scm.Supplier(env=env, ID="S1", name="S1", node_type=scm.NodeType.SUPPLIER)
```

#### Writing a custom replenishment policy

The built-in replenishment policies (_SSReplenishment_, _RQReplenishment_, _PeriodicReplenishment_) talk to their owning node through a small contract on _Node_, rather than reaching into its internal attributes. A user-defined `InventoryReplenishment` subclass should use the same contract so it stays decoupled from the node's layout:

- `node.position()` — current backorder-aware inventory position (`on_hand - stats.backorder[1]`). Use this in place of reading `node.inventory.on_hand` and `node.stats.backorder[1]` separately.
- `node.place_order(quantity)` — picks a supplier via the node's supplier-selection policy and spawns the dispatch process. Use this in place of `selection_policy.select(...)` + `env.process(process_order(...))`.
- `node.wait_for_drop()` — generator that blocks until the inventory drops and rotates the drop event atomically. Use `yield from node.wait_for_drop()` in the policy's `run()` loop.

On the supplier-selection side, _Link_ exposes `link.available_quantity()` (returns `source.inventory.level`), so a custom `SupplierSelectionPolicy` subclass can compare candidate suppliers without reaching past the link.

#### Modeling what a disruption does to stored inventory

A real-world disruption can take many forms — a natural disaster, a power outage, contamination, theft, a strike — and each affects the goods sitting on the shelf differently. The disruption settings already on `Node` (`failure_p` for random failures, `node_disrupt_time` for scheduled ones, and `node_recovery_time` for how long the outage lasts) only switch the node off and stop it from accepting new orders. They do *not* describe what happens to the existing inventory.

If you want the simulation to also account for goods that are physically lost during a disruption, set the `disruption_impact` argument when you create the node (and, if you choose `"destroy_fraction"`, also `disruption_loss_fraction`). The available choices are:

| `disruption_impact` value | What happens the moment the disruption begins |
| --- | --- |
| `None` (the default) or `"none"` | The node goes offline but the inventory is left alone. |
| `"destroy_all"` | All stock at the node is lost. For a `Manufacturer`, the on-hand raw materials are also wiped, since the idea behind this preset is "every physical thing at this site is gone." Infinite suppliers (which never run out) are skipped, since "destroying" an infinite shelf has no meaning. |
| `"destroy_fraction"` | A share of the current stock is lost. The share is given by `disruption_loss_fraction`, which can be a fixed number between 0 and 1 (e.g., `0.3` to lose 30%) or a small function that returns a different number each time, if you want randomized losses. |
| A callable, i.e. `f(node) -> None` | For anything more specific. You write a short Python function describing the effect; the simulator calls it with the affected node when a disruption hits. Examples: a contamination that destroys only certain batches, damage that reduces capacity, a lead-time penalty that kicks in once the node recovers. |

The effect is applied **once**, exactly at the moment the node goes from active to inactive — both for scheduled (`node_disrupt_time`) and random (`failure_p`) disruptions. Importantly, it is *not* re-applied at every step while the node is offline. If you want a loss that grows over time during an outage (slow spoilage from prolonged loss of cooling, ongoing pilferage), implement that inside your own callable, where you can spawn a parallel SimPy process and time it against `node_recovery_time`.

The two built-in presets ultimately call `Inventory.destroy(amount, reason)`, a public method on `Inventory` that immediately removes the requested quantity from the underlying `simpy.Container`. If the node holds perishable batches, the oldest batches are removed first (FIFO). One subtle but important detail: `destroy` does **not** wake up the replenishment policy. The reason is that while the node is offline, new orders are blocked at the dispatch gate anyway; if `destroy` were to wake the replenishment policy, it would simply queue up a backlog of orders that all fire the instant the node recovers — flooding the supplier and distorting the simulation. If you write a custom impact callable that destroys stock, call `Inventory.destroy(...)` for the same reason; avoid editing `level`, `on_hand`, or `perish_queue` by hand.

The amount destroyed (`destroyed_qty`) and its monetary value (`destroyed_value`) are recorded on the node's `Statistics`. `destroyed_value` is registered as a cost component, so it is automatically included in `node_cost` and therefore in `profit` — you don't need to subtract it manually. When writing a custom impact callable, follow the same convention by reporting losses through `node.stats.update_stats(destroyed_qty=qty, destroyed_value=qty * unit_cost)`, rather than inventing parallel statistics that the simulator won't know about.

A short example:

```python
import random
import SupplyNetPy.Components as scm

# Wipe everything when disruption hits — common for natural-disaster scenarios.
distributor = scm.InventoryNode(
    env=env, ID="D1", name="D1", node_type="warehouse",
    capacity=200, initial_level=120, inventory_holding_cost=0.2,
    replenishment_policy=scm.SSReplenishment, policy_param={'s': 100, 'S': 200},
    product_sell_price=10, product_buy_price=5,
    node_disrupt_time=lambda: 30, node_recovery_time=lambda: 5,
    disruption_impact="destroy_all",
)

# Power-outage style: each disruption spoils 10–40% of the current shelf.
warehouse = scm.InventoryNode(
    ..., disruption_impact="destroy_fraction",
    disruption_loss_fraction=lambda: random.uniform(0.1, 0.4),
)
```

The __logger__ module is designed to maintain simulation logs. It includes the _GlobalLogger_ class, which serves as a common logger for all components within the environment. Users can configure this logger to save logs to a specific file or print them to the console. A package-level `global_logger` instance is also exported so users can call `scm.global_logger.disable_logging()` / `scm.global_logger.enable_logging()` to toggle all simulation logs at once.

The __utilities__ module provides useful Python routines to reduce manual work. It contains functions for creating supply chains (`create_sc_net`), running simulations (`simulate_sc_net`), and inspecting / visualizing the resulting network (`get_sc_net_info`, `print_node_wise_performance`, `visualize_sc_net`).

Note that `create_sc_net` accepts two interchangeable construction styles — plain `dict` netlists, or pre-built `Node` / `Link` / `Demand` objects — but each of its `nodes`, `links`, and `demands` arguments must be homogeneous: a list mixing dicts and pre-built objects is rejected up-front (the mixed case would cause dicts and objects to run against two different `simpy.Environment` instances). When any list contains pre-built objects you must also pass `env` explicitly, and each object's own `env` must match it.

The public API of each sub-module is declared via an explicit `__all__` list, and `SupplyNetPy.Components` re-exports these names explicitly — no wildcard imports. Module-level imports (SimPy, NumPy, NetworkX, Matplotlib, etc.) and internal constants are deliberately not reachable as `scm.<name>`.

#### SupplyNetPy Library Hierarchy

    SupplyNetPy
    ├── Components
    │   ├── core.py
    │   ├── logger.py
    │   ├── utilities.py
