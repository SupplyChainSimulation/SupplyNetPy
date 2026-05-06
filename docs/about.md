# About SupplyNetPy

**SupplyNetPy** is an open-source Python library for building, running, and analyzing supply-chain simulations. You describe a supply chain — its suppliers, factories, warehouses, retailers, demand, and the links between them — and SupplyNetPy plays out the events in that chain (orders being placed, shipments arriving, demand showing up, nodes failing) and reports how the system behaves: how much stock sits where, where shortages appear, what each part costs, and how profitable the chain is overall.

Under the hood it runs on top of [SimPy](https://simpy.readthedocs.io/), a Python framework for **event-driven simulation** — instead of advancing the clock one fixed step at a time, the simulator jumps directly from one event to the next (the next order arrival, the next delivery, the next failure), which makes long simulations fast even when events are sparse. SupplyNetPy is intended for researchers, students, and practitioners working in operations, logistics, and supply-chain management.

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
- **Inventory models**: Several built-in *replenishment policies* — the rules that decide *when* to reorder and *how much* to order:
    - **(s, S)** — when stock falls below the level *s*, place an order large enough to bring it up to *S*.
    - **(s, S) with safety stock** — same rule as above, but also keep a buffer of safety stock on top of *s*, so a sudden surge in demand doesn't immediately cause a shortage.
    - **Reorder point–quantity (RQ)** — when stock falls below the reorder point *R*, order a fixed quantity *Q*.
    - **Reorder point–quantity (RQ) with safety stock** — same rule, with an extra safety-stock buffer.
    - **Periodic review (Q, T)** — every *T* days, order *Q* units (regardless of the current level).
    - **Periodic review (Q, T) with safety stock** — same rule, with an extra safety-stock buffer to guard against demand spikes between reviews.
- **Flexible lead times**: Define deterministic or stochastic lead times and transportation costs.
- **Disruption modeling**: Both nodes (warehouses, factories, etc.) and links (transport routes) can be made to fail — either at scheduled times or randomly with a given probability. On top of that, the `disruption_impact` setting on a node describes what physically happens to the goods on the shelf when a disruption hits:
    - `"destroy_all"` — everything is lost (e.g., a fire or flood at a warehouse).
    - `"destroy_fraction"` paired with a loss fraction — a portion of the stock is lost; the fraction can be a fixed number or randomized for each event (useful for, say, a power outage that spoils part of the refrigerated stock).
    - A custom function — for any other rule you want to capture (contamination, theft, partial damage, …).

    The amount lost and its monetary value are tracked automatically per node and the value is subtracted from profit, so the financial impact of disruptions shows up in the simulation results without extra bookkeeping.
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

- **SupplierSelectionPolicy**: Abstract base for implementing supplier selection strategies. All built-in policies filter out disrupted links by default; if every link is down they still return a supplier and the dispatch gate handles the block.
    - **SelectFirst**: Selects the first supplier (skipping disrupted links).
    - **SelectAvailable**: Selects the first supplier with sufficient inventory, preferring active links.
    - **SelectCheapest**: Selects the active supplier with the lowest transportation cost.
    - **SelectFastest**: Selects the active supplier with the shortest lead time.
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