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
