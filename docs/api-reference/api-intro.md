## SupplyNetPy API Reference

__SupplyNetPy__ includes a sub-module called __Components__, which facilitates the creation of supply chain networks by providing essential components such as nodes, links, and demand, and assembling them into a network. The __Components__ module contains three sub-modules: __core__, __logger__, and __utilities__.

The __core__ module is responsible for creating supply chain components. It includes classes such as _RawMaterial_, _Product_, _Inventory_, _Node_, _Link_, _Supplier_, _Manufacturer_, _InventoryNode_, and _Demand_, the replenishment policies (_SSReplenishment_, _RQReplenishment_, _PeriodicReplenishment_), and the supplier-selection policies (_SelectFirst_, _SelectAvailable_, _SelectCheapest_, _SelectFastest_). Any new node created using these classes will be instantiated within a SimPy environment. The _Inventory_ class is responsible for monitoring inventories. By default, the classes in the core module support single-product inventories. The _Inventory_ class wraps a SimPy _Container_ to implement the basic behavior of an inventory, including routines to record inventory level changes. If users wish to create a different inventory type with custom behavior, they can do so by extending either _Inventory_ or SimPy _Container_. The core module also exports `set_seed(seed)` for seeding the library-wide default RNG used for probabilistic disruption, so runs can be made reproducible.

The __logger__ module is designed to maintain simulation logs. It includes the _GlobalLogger_ class, which serves as a common logger for all components within the environment. Users can configure this logger to save logs to a specific file or print them to the console. A package-level `global_logger` instance is also exported so users can call `scm.global_logger.disable_logging()` / `scm.global_logger.enable_logging()` to toggle all simulation logs at once.

The __utilities__ module provides useful Python routines to reduce manual work. It contains functions for creating supply chains (`create_sc_net`), running simulations (`simulate_sc_net`), and inspecting / visualizing the resulting network (`get_sc_net_info`, `print_node_wise_performance`, `visualize_sc_net`).

The public API of each sub-module is declared via an explicit `__all__` list, and `SupplyNetPy.Components` re-exports these names explicitly — no wildcard imports. Module-level imports (SimPy, NumPy, NetworkX, Matplotlib, etc.) and internal constants are deliberately not reachable as `scm.<name>`.

#### SupplyNetPy Library Hierarchy

    SupplyNetPy
    ├── Components
    │   ├── core.py
    │   ├── logger.py
    │   ├── utilities.py
