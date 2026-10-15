# About SupplyNetPy

**SupplyNetPy** is an open source Python library for building, running, and analyzing supply chain simulations. You describe a supply chain, with its raw-material suppliers, manufacturers, distributors, warehouses, retailers, customer demands and the links between them. SupplyNetPy then plays out the events in that chain (orders being placed, orders arriving, customers ordering, disruptions starting) and reports how the system behaves, such as the inventory level at each site, where shortages appear, what each part costs, and how profitable the chain is overall.

Under the hood it runs on top of [SimPy](https://simpy.readthedocs.io/), a Python framework for **event-driven simulation**. Instead of advancing the clock one fixed step at a time, the simulator jumps directly from one event to the next (the next customer order, the next delivery, the next disruption), which makes long simulations fast even when events are sparse. SupplyNetPy is intended for researchers, students, and practitioners working in operations, logistics, and supply chain management. The words used in these pages are explained in the [Glossary](glossary.md).

---

## Purpose

* Build detailed supply chain models, with raw-material suppliers, manufacturers, distributors, retailers and customer demands.

* Simulate how inventories change over time, with replenishment orders, lead times, supplier selection, costs and disruptions.

* Test and compare replenishment policies and supplier-selection policies.

* Analyze performance through the simulation log and results such as throughput, revenue, shortages, costs and profit.

---

## Features

* **Modular design.** Build supply chain networks of any size and with as many levels as you need (for example raw-material suppliers, manufacturers, distributors and retailers) by assembling the built in components.
* **Discrete event simulation.** Event-driven simulation powered by SimPy.
* **Replenishment policies.** Several built in *replenishment policies*, the rules that decide *when* to place a replenishment order and *how many units* to order.
    * **(s, S).** When the inventory position falls to *s* or below, order enough to bring it back up to *S*.
    * **(s, S) with safety stock.** The same rule, with the safety stock added to both *s* and *S*, so a sudden rise in demand does not immediately cause a shortage.
    * **(R, Q).** When the inventory position falls to *R* or below, order a fixed *Q* units.
    * **Periodic (T, Q).** Every *T* time units, order *Q* units, whatever the inventory position.
    * **Periodic (T, Q) with safety stock.** The same rule, and if the inventory level is below the safety stock, the order also includes the units needed to bring it back up.
* **Flexible lead times.** Lead times can be fixed or random, and each link has its own transportation cost.
* **Disruptions.** Both nodes (warehouses, manufacturers and so on) and links can be disrupted, either at scheduled times or at random with a given probability. While a site is disrupted it takes no new orders, from other sites or from customers. A customer who arrives then goes away, and the site records the lost sale in `disruption_lost_sales`, apart from its shortage. On top of that, the `disruption_impact` setting on a node describes what physically happens to the units at the node when a disruption starts.
    * With `"destroy_all"`, all units are lost (for example in a fire or flood at a warehouse).
    * With `"destroy_fraction"` and a loss fraction, part of the units is lost. The fraction can be a fixed number or drawn at random for each disruption (useful, say, for a power cut that spoils part of the refrigerated goods).
    * A custom function can describe any other effect you want to capture (contamination, theft, partial damage and so on).

    The units lost and their value are tracked automatically for each node, and the value is subtracted from profit, so the financial impact of disruptions shows up in the simulation results without extra bookkeeping.
* **Simple API.** Build and simulate supply chain models with clear Python code.
* **Performance tracking.** The simulation log and the results for each node and for the whole network are produced automatically.

---

## Architecture

SupplyNetPy provides these core components for supply chain modeling.

* **Node classes.** `Node`, `Supplier`, `Manufacturer`, `InventoryNode`, `Demand`.
* **Link.** The transport connection between two sites, with its own transportation cost and lead time.
* **Inventory.** Keeps the inventory level and the related records at each site.
* **Product and RawMaterial.** The product a manufacturer makes, and the raw materials it uses.
* **InventoryReplenishment.** The base class for replenishment policies.
    * **SSReplenishment.** The (s, S) policy.
    * **RQReplenishment.** The (R, Q) policy.
    * **PeriodicReplenishment.** The periodic policy, which places a replenishment order at fixed intervals.

* **SupplierSelectionPolicy.** The base class for supplier-selection policies. All built in policies skip suppliers whose site or link is disrupted. If no supplier can take a replenishment order, the order is not placed, and the replenishment policy checks again as soon as a supplier or a link recovers.
    * **SelectFirst.** Chooses the first supplier.
    * **SelectAvailable.** Chooses the first supplier whose inventory level can fill the whole order.
    * **SelectCheapest.** Chooses the supplier with the lowest transportation cost.
    * **SelectFastest.** Chooses the supplier with the shortest lead time.
* **Statistics and InfoMixin.** Built in tools for summarizing and reporting how each part of the network behaves.

---

## Why SupplyNetPy?

* **Open source and extensible.** Designed for researchers, students and professionals, and easy to extend or to build into larger systems.
* **Made for supply chains.** Designed and built specifically for supply chain simulation.
* **Reproducible and customizable.** Lets you experiment with fully configurable models, supplier behaviour and random elements.

---
## Authors


[![GitHub](img/github.png)](https://github.com/tusharlone) 
[![profile](img/profile-user.png)](https://tusharlone.github.io) &nbsp; Tushar Lone <br>
[![GitHub](img/github.png)](https://github.com/NehaKaranjkar) 
[![profile](img/profile-user.png)](https://nehakaranjkar.github.io) &nbsp; Neha Karanjkar <br>
[![GitHub](img/github.png)](https://github.com/LekshmiPremkumar)
[![profile](img/profile-user.png)](https://lekshmipremkumar.github.io) &nbsp; Lekshmi P<br>

---
## License

[License](license.md)
