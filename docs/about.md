# About SupplyNetPy

**SupplyNetPy** is an open-source Python library designed specifically for modeling, simulating, and analyzing supply chain networks and inventory systems. The library features supply chain-specific components to model arbitrary supply chain networks easily. It is built on Python’s SimPy discrete-event simulation framework and provides a flexible and extensible toolkit for researchers, engineers, and practitioners in operations, logistics, and supply chain management.

---

## Purpose

- Construct detailed supply chain models, including suppliers, manufacturers, distributors, retailers, and demand points.

- Simulate inventory dynamics by modeling stock levels, replenishment cycles, lead times, supplier selection, costs, and disruptions.

- Test and compare inventory replenishment policies and supplier selection strategies.

- Analyze performance through generated logs and computed metrics such as throughput, revenue, stockouts, costs, and profit.

---

## Features

- **Modular architecture**: Build arbitrarily complex, multi-echelon supply chain networks by assembling built-in components.
- **Discrete-event simulation**: High-fidelity event-driven simulation powered by SimPy.
- **Inventory models**: Support for multiple replenishment policies:
    - (s, S) replenishment
    - (s, S) with safety stock
    - Reorder point–quantity (RQ)
    - Reorder point–quantity (RQ) with safety stock
    - Periodic review (Q, T)
    - Periodic review (Q, T) with safety stock
- **Flexible lead times**: Define deterministic or stochastic lead times and transportation costs.
- **Simple API**: Build and simulate supply chain models using clear Python code.
- **Performance tracking**: Automatically generate logs and compute supply chain performance indicators.

---

## Architecture

SupplyNetPy provides core components for supply chain modeling:

- **Node classes**: `Node`, `Supplier`, `Manufacturer`, `InventoryNode`, `Demand`.
- **Link**: Represents transportation connections between nodes, with configurable cost and lead time
- **Inventory**: Tracks stock levels and related operations at each node.
- **Product and RawMaterial**: Define supply chain items.
- **InventoryReplenishment**: Abstract base for implementing replenishment policies:
    - **SSReplenishment**: order up to max when stock drops below s.
    - **RQReplenishment**: fixed quantity reorder when stock drops below a threshold.
    - **PeriodicReplenishment**: replenish at regular time intervals.

- **SupplierSelectionPolicy**: Abstract base for implementing supplier selection strategies:
    - **SelectFirst**: Selects the first supplier.
    - **SelectAvailable**: Selects the first available supplier.
    - **SelectCheapest**: Selects the supplier with the lowest transportation cost.
    - **SelectFastest**: Selects the supplier with the shortest lead time.
- **Statistics and InfoMixin**: Provide built-in tools for summarizing and reporting system behavior and object-specific metrics.

---

## Why SupplyNetPy?

- **Open-source and extensible**: Designed for researchers, students, and professionals; easy to extend or integrate into larger systems.
- **Specialized for supply chain dynamics**: Specifically designed and built for supply chain simulation.
- **Reproducible and customizable**: Enables experimentation with fully configurable models, suppliers behaviours and stochastic elements.

---
## Authors


[![GitHub](img/github.png)](https://github.com/tusharlone) 
[![profile](img/profile-user.png)](https:\\tusharlone.github.io) &nbsp; Tushar Lone <br>
[![GitHub](img/github.png)](https://github.com/NehaKaranjkar) 
[![profile](img/profile-user.png)](https:\\nehakaranjkar.github.io) &nbsp; Neha Karanjkar <br>
[![GitHub](img/github.png)](https://github.com/LekshmiPremkumar)
[![profile](img/profile-user.png)](https:\\lekshmipremkumar.github.io) &nbsp; Lekshmi P<br>

---
## License

[License](license.md)