## SupplyNetPy API Reference

__SupplyNetPy__ includes a sub-module called __Components__, which facilitates the creation of supply chain networks by providing essential components such as nodes, links, and demand, and assembling them into a network. The __Components__ module contains four sub-modules: core, inventory, logger, and utilities.

The __core__ module is responsible for creating supply chain components. It includes classes such as _RawMaterial_, _Product_, _Inventory_, _Node_, _Link_, _Supplier_, _Manufacturer_, _InventoryNode_, and _Demand_. Any new node created using these classes will be instantiated within a SimPy environment. The _Inventory_ class is responsible for creating inventories. By default, the classes in the core module support single-product inventories. The _Inventory_ class extends the SimPy Container class to implement the basic behavior of an inventory, including routines to record inventory level changes. If users wish to create a different inventory type with custom behavior, they can do so by extending either _Inventory_ or SimPy _Container_.

The __logger__ module is designed to maintain simulation logs. It includes the _GlobalLogger_ class, which serves as a common logger for all components within the environment. Users can configure this logger to save logs to a specific file or print them to the console.

The __utilities__ module provides useful Python routines to reduce manual work. It contains functions for creating random supply chains, generating multiple nodes or links, and more. Additionally, it offers routines for supply chain network visualization.

#### SupplyNetPy Library Hierarchy

    SupplyNetPy
    ├── Components
    │   ├── core.py
    │   ├── logger.py
    │   ├── utilities.py
