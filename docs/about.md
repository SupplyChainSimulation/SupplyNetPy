# About SupplyNetPy

**SupplyNetPy** is an open source Python library for building, running, and analyzing supply chain simulations. You describe a supply chain, with its raw-material suppliers, manufacturers, distributors, warehouses, retailers, customer demands and the links between them. SupplyNetPy then plays out the events in that chain (orders being placed, orders arriving, customers ordering, disruptions starting) and reports how the system behaves, such as the inventory level at each site, where shortages appear, what each part costs, and how profitable the chain is overall.

It is built on [SimPy](https://simpy.readthedocs.io/), a Python framework for **event-driven simulation**. Instead of advancing the clock one fixed step at a time, the simulator jumps directly from one event to the next (the next customer order, the next delivery, the next disruption), so long runs stay fast when events are few. SupplyNetPy is intended for researchers, students, and practitioners working in operations, logistics, and supply chain management. The words used in these pages are explained in the [Glossary](glossary.md), and the [User Guide](guide/customer-demand.md) explains common tasks step by step.

---

## Purpose

* Build detailed supply chain models, with raw-material suppliers, manufacturers, distributors, retailers and customer demands.

* Simulate how inventories change over time, with replenishment orders, lead times, supplier selection, perishable products, costs and disruptions.

* Test and compare replenishment policies and supplier-selection policies.

* Analyze performance through the simulation log and the results for each node, each link and the whole network, such as orders fulfilled, revenue, shortages, lost sales, costs and profit.

* Run experiments with many replications, and compare settings fairly.

---

## Features

* **Modular design.** Build supply chain networks of any size and with as many levels as you need (for example raw-material suppliers, manufacturers, distributors and retailers) by assembling the built in components.
* **Customer demand.** Customer orders can arrive at fixed or random times, for fixed or random numbers of units, or follow recorded data. When a site is short of units, its customers can leave, take the units that are there, or wait for the rest, with partial deliveries if they accept them. See [Customer Demand](guide/customer-demand.md).
* **Replenishment policies.** Several built in *replenishment policies*, the rules that decide *when* to place a replenishment order and *how many units* to order. You can also write your own. See [Replenishment Policies](guide/replenishment-policies.md).
    * **(s, S).** When the inventory position falls to *s* or below, order enough to bring it back up to *S*.
    * **(s, S) with safety stock.** The same rule, with the safety stock added to both *s* and *S*, so a sudden rise in demand does not immediately cause a shortage.
    * **(R, Q).** When the inventory position falls to *R* or below, order a fixed *Q* units.
    * **Periodic (T, Q).** Every *T* time units, order *Q* units, whatever the inventory position.
    * **Periodic (T, Q) with safety stock.** The same rule, and if the inventory level is below the safety stock, the order also includes the units needed to bring it back up.
* **Supplier selection.** A site with several suppliers chooses one for each replenishment order with a *supplier-selection policy*. The built in policies choose the first supplier, the first that can fill the whole order, the cheapest or the fastest, and you can write your own. In fixed mode the site keeps its first choice, and in dynamic mode it chooses again for every order. See [Supplier Selection](guide/supplier-selection.md).
* **Lead times and costs.** Each link has its own lead time, fixed or random, and its own transportation cost.
* **Perishable products.** Units can have a shelf life. Each batch keeps its manufacturing date from site to site, orders take the oldest units first, and expired units are thrown away and counted. See [Perishable Products](guide/perishable-products.md).
* **Disruptions.** Both sites and links can be disrupted, either at scheduled times or at random with a given probability. While a site is disrupted it takes no new orders, from other sites or from customers, and the customers it turns away are counted apart from its shortage. The `disruption_impact` setting describes what happens to the units at a site when a disruption starts.
    * With `"destroy_all"`, all units are lost (for example in a fire or flood at a warehouse).
    * With `"destroy_fraction"` and a loss fraction, part of the units is lost. The fraction can be a fixed number or drawn at random for each disruption (useful, say, for a power cut that destroys part of the units kept cold).
    * A custom function can describe any other effect you want to capture (contamination, theft, partial damage and so on).

    The units lost and their value are recorded for each site, and the value is part of its costs, so the financial impact of disruptions shows up in the profit without extra bookkeeping. See [Disruptions](guide/disruptions.md).
* **Statistics and results.** Every node and every link keeps its own statistics, such as orders placed and fulfilled, shortages, lost sales, waiting times, lead times, the fill rate, the average inventory level, availability and costs. The results for the whole network are added up from them. A warm-up can leave the first stretch of a run out of the statistics. See [Statistics and Results](guide/statistics.md).
* **Reproducible experiments.** Seeded random numbers make every run repeatable, so settings can be compared over many replications with confidence intervals. See [Running Experiments](guide/running-experiments.md).
* **Simple API.** Build and simulate supply chain models with clear Python code, either from plain Python dictionaries or by creating each part as an object.

---

## Architecture

SupplyNetPy provides these core components for supply chain modeling. The [API Reference](api-reference/api-intro.md) describes each of them.

* **Node classes.** `Supplier` (a raw-material supplier), `Manufacturer`, `InventoryNode` (a distributor, warehouse or retailer), `Demand` (a customer demand), and their base class `Node`.
* **Link.** The connection between a site and one of its suppliers, with its own transportation cost and lead time.
* **Inventory.** Keeps the inventory level and the related records at each site, including the batches of a perishable product.
* **Product and RawMaterial.** The product a manufacturer makes, and the raw materials it uses.
* **InventoryReplenishment.** The base class for replenishment policies.
    * **SSReplenishment.** The (s, S) policy.
    * **RQReplenishment.** The (R, Q) policy.
    * **PeriodicReplenishment.** The periodic policy, which places a replenishment order at fixed intervals.

* **SupplierSelectionPolicy.** The base class for supplier-selection policies, each used in fixed or dynamic mode. All built in policies skip suppliers whose site or link is disrupted. If no supplier can take a replenishment order, the order is not placed, and the replenishment policy checks again as soon as a supplier or a link recovers.
    * **SelectFirst.** Chooses the first supplier.
    * **SelectAvailable.** Chooses the first supplier whose inventory level can fill the whole order.
    * **SelectCheapest.** Chooses the supplier with the lowest transportation cost.
    * **SelectFastest.** Chooses the supplier with the shortest lead time.
* **Statistics and LinkStatistics.** The statistics of each node and of each link.
* **Network and the utility functions.** `create_sc_net` builds a network, `simulate_sc_net` runs it and works out the results for the whole network, `reset_stats` starts the statistics again after a warm-up, and further functions print, return or draw the results. The `Network` class holds a network and its results.

---

## Why SupplyNetPy?

* **Made for supply chains.** Sites, links, replenishment and supplier-selection policies, disruptions and perishable products come ready to use, so a model takes a few lines of Python instead of a simulation written from scratch.
* **Open source and extensible.** Every part can be configured, and policies and disruption effects can be replaced by your own.
* **Validated.** SupplyNetPy was validated in four ways.
    * **Automated tests.** Tests check each part of the library, and run on every change to it.
    * **Textbook results.** The examples reproduce analytical results, such as the [economic order quantity](EOQ_est.md), the [safety stock](safety_inv_est.md) and the [newsvendor](example-newvendor.md) order quantity.
    * **A commercial tool.** In eight models, all 19 performance metrics agree exactly with those of [anyLogistix](https://www.anylogistix.com/). The models and results are in the [validation folder](https://github.com/SupplyChainSimulation/SupplyNetPy/tree/main/validation).
    * **A published study.** The [pharmacy case study](case_study_pharma.md) reproduces the results of a published paper.

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
