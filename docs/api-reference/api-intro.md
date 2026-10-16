## SupplyNetPy API Reference

__SupplyNetPy__ includes a submodule called __Components__, which helps you create supply chain networks by providing their parts, such as nodes, links and customer demands, and assembling them into a network. The __Components__ module contains three submodules, __core__, __logger__ and __utilities__. The pages that follow describe each of them, module by module and class by class. The words used on these pages are explained in the [Glossary](../glossary.md).

The __core__ module creates the parts of a supply chain. It includes the classes _RawMaterial_, _Product_, _Inventory_, _Node_, _Link_, _Supplier_, _Manufacturer_, _InventoryNode_ and _Demand_, the statistics of a node (_Statistics_) and of a link (_LinkStatistics_), the replenishment policies (_SSReplenishment_, _RQReplenishment_, _PeriodicReplenishment_), and the supplier-selection policies (_SelectFirst_, _SelectAvailable_, _SelectCheapest_, _SelectFastest_). Every node created with these classes runs in a SimPy environment. The _Inventory_ class keeps the inventory of a site, one product per inventory, in a SimPy _Container_, and can also record how the inventory level changes. For a different kind of inventory with custom behavior, extend _Inventory_ or SimPy _Container_. The `node_type` of a node is checked against the `NodeType` enum, and can be given as a string in any letter case or as an enum member such as `scm.NodeType.SUPPLIER`. The core module also exports `set_seed(seed)`, which seeds the random numbers the whole library uses, so runs can be repeated exactly.

The __logger__ module keeps the simulation logs. It includes the _GlobalLogger_ class, a common logger for all the parts of the simulation. You can set it up to save logs to a file or to print them to the console. A `global_logger` instance for the whole package is also exported, so you can call `scm.global_logger.disable_logging()` or `scm.global_logger.enable_logging()` to switch all simulation logs off or on at once.

The __utilities__ module provides useful Python functions that save manual work. It contains functions for creating supply chains (`create_sc_net`), running simulations (`simulate_sc_net`), starting the statistics again after a warm-up (`reset_stats`), and inspecting or drawing the resulting network (`get_sc_net_info`, `print_node_wise_performance`, `print_link_wise_performance`, `visualize_sc_net`). It also contains the _Network_ class, which holds a network and its results. `create_sc_net` builds a network either from plain `dict` descriptions or from ready made `Node`, `Link` and `Demand` objects, but each of its lists must use only one of the two.

Each submodule lists its public names in `__all__`, and `SupplyNetPy.Components` exports exactly these names.

#### Guides

For tasks that use several parts together, the User Guide explains how to do them step by step.

* [Customer Demand](../guide/customer-demand.md). How often customers order and how many units, demand from recorded data, what customers do when the site is short, and delivering their orders.
* [Replenishment Policies](../guide/replenishment-policies.md). Choosing a built in policy, when it checks, safety stock, and writing your own policy.
* [Supplier Selection](../guide/supplier-selection.md). Choosing a supplier-selection policy, fixed and dynamic mode, and writing your own policy.
* [Disruptions](../guide/disruptions.md). Scheduled and random disruptions of sites and links, what happens to orders, and units lost in a disruption.
* [Perishable Products](../guide/perishable-products.md). Shelf life, batches and their manufacturing dates, when units expire, and expired units in the statistics.
* [Statistics and Results](../guide/statistics.md). Results for the whole network, statistics of nodes and links, and warm-ups.

#### SupplyNetPy Library Hierarchy

    SupplyNetPy
    ├── Components
    │   ├── core.py
    │   ├── logger.py
    │   ├── utilities.py
