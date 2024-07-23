## SupplyNetPy API Reference

__SupplyNetPy__ has a sub-module called __Components__ that facilitates the creation of supply chain networks by creating necessary components such as nodes, links, and demand, and assembling them into a network. The __Components__ module further contains four sub-modules: core, inventory, logger, and utilities.

The __core__ module is responsible for creating components of the supply chains. It is supported by classes such as _Supplier_, _Distributor_, _Manufacturer_, _Retailer_, _Demand_, and _Link_. Any new node created using these classes will be created in a SimPy environment.

The __inventory__ module is responsible for creating inventories. By default, the classes in the core module will hold a single product inventory. The classes in this module are _Inventory_, _Product_, and _MonitoredInventory_. The MonitoredInventory class extends the SimPy Container class to implement the basic behavior of an inventory. It has routines to save level changes in the inventory. The Inventory class extends _MonitoredInventory_ to implement a single product inventory. If a user wants to create a different inventory type with its own behavior, they can do so by extending _MonitoredInventory_ or _Inventory_.

The __logger__ module is solely created to maintain simulation logs. It includes the _GlobalLogger_ class, which serves as a common logger for all components created in the environment. Users can configure this logger to save the logs to a specific file or to print on the console.

The __utilities__ module is populated with handy Python routines to reduce manual work. It contains routines that can be used directly to create random supply chains, multiple nodes or links, and more. There are also routines for supply chain network visualization.


#### SupplyNetPy Library Hierarchy

    SupplyNetPy
    ├── Components
    │   ├── core.py
    │   ├──inventories.py
    │   ├──logger.py
    │   ├──utilities.py