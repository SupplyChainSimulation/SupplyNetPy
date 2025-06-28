# About SupplyNetPy

**SupplyNetPy** is an open-source Python library designed for modeling, simulating, and analyzing multi-echelon supply chain networks and inventory systems.
Built on top of Python’s SimPy discrete-event simulation framework, SupplyNetPy provides a flexible and extensible toolkit for researchers, engineers, and practitioners working in operations, logistics, and supply chain management.

---

## Purpose

SupplyNetPy enables users to:

- Construct detailed supply chain models, including suppliers, manufacturers, distributors, retailers, and demand points.

- Simulate inventory dynamics by modeling stock levels, replenishment cycles, lead times, supplier selection, costs, and disruptions.

- Test and compare inventory replenishment policies and supplier selection strategies.

- Analyze performance through generated logs and computed metrics such as throughput, stockouts, costs, and net profit.

---

## Features

- **Modular architecture**: Build arbitrarily complex, multi-echelon supply chain networks by assembling built-in components.
- **Discrete-event simulation**: High-fidelity event-driven simulation powered by SimPy.
- **Inventory models**: Support for multiple replenishment policies:
    - (s, S) replenishment
    - (s, S) with safety stock
    - Reorder point–quantity (RQ)
    - Periodic review (Q, T)
- **Flexible lead times**: Define deterministic or stochastic lead times and transportation costs.
- **Simple API**: Build and simulate supply chain models using clear Python code.
- **Performance tracking**: Automatically generate logs and compute supply chain performance indicators.

---

## Architecture

SupplyNetPy provides core components for supply chain modeling:

- **Node classes**: `Supplier`, `Manufacturer`, `Distributor`, `Retailer`, `Demand`
- **Link**: Represents transportation connections between nodes, with configurable cost and lead time
- **Inventory**: Tracks stock levels and related operations at each node.
- **Product and RawMaterial**: Define supply chain items.
- **InventoryReplenishment**: Abstract base for implementing replenishment policies:
    - **SSReplenishment**: order up to max when stock drops below s.
    - **RQReplenishment**: Fixed quantity reorder when stock drops below a threshold.
    - **PeriodicReplenishment**: Replenish at regular time intervals.

- **SupplierSelectionPolicy**: Abstract base for implementing supplier selection strategies:
    - **SelectAvailable**: Selects the first available supplier.
    - **SelectCheapest**: Selects the supplier with the lowest transportation cost.
    - **SelectFastest**: Selects the supplier with the shortest lead time.
- **Statistics and InfoMixin**: Provide built-in tools for summarizing and reporting system behavior and object-specific metrics.

---

## Why SupplyNetPy?

- **Open-source and extensible**: Designed for researchers, students, and professionals; easy to extend or integrate into larger systems.
- **Specialized for supply chain dynamics**: Purpose-built for supply chain simulation, not generic discrete-event modeling.
- **Reproducible and customizable**: Enables experimentation with fully configurable models, suppliers behaviours and stochastic elements.

---
