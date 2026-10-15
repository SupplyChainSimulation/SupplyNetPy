# Glossary

SupplyNetPy uses **one word for each idea**. This page lists those words, says what each one means, and gives the name it has in the code. The same words are used in this documentation, in the code's comments and docstrings, and in the API reference, so that two words never stand for the same thing.

A few names in the code use a different word from the one chosen here (for example `inventory.on_hand`). They are kept so that existing programs keep working; the entry explains what they really hold.

---

## The network

| Term | Meaning | In the code |
|---|---|---|
| **Supply chain network** | The whole model: the sites, the links between them, and the customers. | `create_sc_net` returns it as a dictionary (often named `supplychainnet`); `Network` wraps the same dictionary. |
| **Node** | Any point in the network: a raw-material supplier, a manufacturer, a warehouse, distributor or retailer, **and** a customer demand. | `Node` (all of these classes are nodes, including `Demand`). |
| **Site** | A node that holds inventory: every node **except** a customer demand. Use "node" when customers are included, and "site" when they are not. | `site_order`, `waiting_site_orders()`, and the results `demand_by_site`, `fulfillment_received_by_site`. |
| **Link** | The transport connection that carries goods from one site to another. It has a cost per order and a lead time. | `Link` |
| **Supplier** (of a site) | The site at the sending end of a link, seen from the site that orders over it. A warehouse is the supplier of the retailers it serves. | `link.source`; chosen by a supplier-selection policy. Note: in `process_order(supplier, ...)` and `process_order_raw(..., supplier, ...)`, the parameter named `supplier` is the **link** to the supplier, not the supplier itself (the supplier is `supplier.source`). |
| **Buyer** | A site that buys from another site: the site at the receiving end of a link, which places orders over it. A buyer is always a site; someone who buys and takes the units out of the network is a customer. | `link.sink` |

---

## Kinds of node

| Term | Meaning | In the code |
|---|---|---|
| **Raw-material supplier** | A site at the start of the network that mines a raw material. It has no supplier of its own. | `Supplier`, `node_type="supplier"` |
| **Infinite supplier** | A raw-material supplier that never runs out. | `Supplier`, `node_type="infinite_supplier"` |
| **Manufacturer** | A site that turns raw materials into a product. | `Manufacturer`, `node_type="manufacturer"` (or `"factory"`, which means the same) |
| **Distributor, warehouse, retailer** | Sites that buy a product, hold it, and sell it on. They behave the same; the name only describes their place in the network. | `InventoryNode`, `node_type="distributor"`, `"warehouse"`, `"retailer"`, `"store"` or `"shop"` |
| **Customer** | Someone who orders units from a site and takes them out of the network (the end customer). | One order from a `Demand`. |
| **Customer demand** | A stream of customer orders arriving at one site, with a given time between orders and order size. | `Demand`, `node_type="demand"` |

---

## Inventory

| Term | Meaning | In the code |
|---|---|---|
| **Inventory** | The units a site holds, together with its records about them (costs, dated batches, and so on). | `Inventory`, reached as `node.inventory`. The units themselves sit in a SimPy container, `node.inventory.inventory`. |
| **Inventory level** | The number of units physically at the site right now. | `node.inventory.level` |
| **Capacity** | The largest inventory level a site can hold. | `capacity` |
| **In transit** | Units that have been sent to a site but have not arrived yet. | (counted inside `inventory.on_hand`) |
| **Inventory position** | What a site can count on: inventory level, plus units in transit to it, minus units it still owes (to other sites and to waiting customers). Replenishment policies decide using this number. | `node.position()` |
| **`on_hand`** | Despite its name, **not** the units physically at the site. It holds the inventory position before units owed to waiting customers are taken off: inventory level, plus units in transit, minus units promised to other sites. Use `node.position()` for the inventory position. | `node.inventory.on_hand` |
| **Units** | The way quantities are counted. | |
| **Product** | The thing a manufacturer makes and the other sites sell. | `Product` |
| **Raw material** | What a raw-material supplier mines and a manufacturer uses up. | `RawMaterial`; a product lists them in `raw_materials` as `(raw material, quantity per unit)` |

### Perishable goods

| Term | Meaning | In the code |
|---|---|---|
| **Perishable** | Goods that can only be sold for a limited time after they are made. | `inventory_type="perishable"` |
| **Shelf life** | How long a perishable unit can be sold after it is made. "Shelf life" is the standard industry term, so it is kept even though "shelf" is otherwise avoided. | `shelf_life` |
| **Manufacturing date** | When a unit was made. | `manufacturing_date` |
| **Batch** | Units of a perishable good that share a manufacturing date. Every order takes units from the oldest batch first, then from the next oldest, and so on. | entries `(manufacturing date, quantity)` in `inventory.perish_queue` |
| **Expired units** | Perishable units that reached the end of their shelf life and were thrown away. | `inventory.waste`; reported as `inventory_waste` |
| **Destroyed units** | Units lost in a disruption (fire, flood, theft, and so on). | `Inventory.destroy`; recorded as `destroyed_qty` and `destroyed_value` |

---

## Orders

| Term | Meaning | In the code |
|---|---|---|
| **Order** | A request for a number of units. There are two kinds: replenishment orders and customer orders. | |
| **Replenishment order** | An order a site places with its supplier, to refill its inventory (or, for a manufacturer, to get raw material). Seen from the supplier, it is an order from a site rather than from a customer, which is why the code labels it a "site order". | Placed by `place_order` / `process_order` (and `process_order_raw` for raw material). At the supplier it is marked `site_order=True`, and `waiting_site_orders()` counts the ones still waiting. In the results it is counted under `demand_by_site`. |
| **Customer order** | An order placed by a customer. | Created by `Demand`; counted under `demand_by_customers` in the results. |
| **Request** | Only in the code's internals: the SimPy object that waits at an inventory until enough units are there to fill an order. | `inventory.get(...)` returns one |
| **Demand** | In the statistics, the orders a node placed or received, counted as `[number of orders, number of units]`. Includes both customer orders and site orders. | `demand_placed`, `demand_received` |
| **Fulfilled** | An order the supplier has sent out in full. | `demand_fulfilled` (at the supplier) |
| **Received** | An order that has arrived at the site that placed it. | `fulfillment_received` (at the buyer) |
| **Lead time** | How long an order takes to arrive after it is sent: over a link, or from a site to a customer. | `Link.lead_time`, `Demand.lead_time` |
| **Backorder** | An order, or part of one, that a site owes right now: it has been accepted but is still waiting for units. It is removed once it is filled, or when a waiting customer gives up. | `stats.backorder`, as `[orders, units]` |
| **Shortage** | How many units a site was missing when an order arrived. It is a running total, never reduced, whether the order is later filled or not. Customers turned away by a disruption are not part of it (see disruption lost sales). | `stats.shortage`, as `[orders, units]` |
| **Disruption lost sales** | Customer orders a site lost because it was disrupted when they arrived. A disrupted site takes no new orders, so the customer goes away. Kept apart from shortage, which counts units the site did not have, because the cause and the remedy differ. | `stats.disruption_lost_sales`, as `[orders, units]` |
| **Tolerance** | How long a customer is willing to wait for units that are not there. A customer with no tolerance leaves at once. | `tolerance` |
| **Partial delivery** | Sending a customer part of an order now and the rest later. | `order_min_split_ratio` |

---

## Replenishment policies

| Term | Meaning | In the code |
|---|---|---|
| **Replenishment policy** | The rule a site follows to decide when to place a replenishment order and how many units to order. | `InventoryReplenishment` and its subclasses, passed as `replenishment_policy` |
| **(s, S) policy** | When the inventory position falls to `s` or below, order enough to bring it back up to `S`. | `SSReplenishment` |
| **(R, Q) policy** | When the inventory position falls to `R` or below, order a fixed `Q` units. | `RQReplenishment` |
| **Periodic policy** | Every `T` time units, order a fixed `Q` units. | `PeriodicReplenishment` |
| **Reorder point** | The inventory position at which a policy places an order (`s` or `R`). | |
| **Safety stock** | Extra units a policy keeps as a buffer against uncertain demand or lead times. A standard industry term, so "stock" is kept here. | `safety_stock` |
| **Supplier-selection policy** | The rule a site follows to choose which of its suppliers receives an order. | `SupplierSelectionPolicy`, `SelectFirst`, `SelectAvailable`, `SelectCheapest`, `SelectFastest` |

---

## Production and mining

| Term | Meaning | In the code |
|---|---|---|
| **Mining** | How a raw-material supplier produces raw material: a fixed number of units every fixed amount of time, as long as its inventory is not full. | `extraction_quantity`, `extraction_time`, `mining_cost`, `total_raw_materials_mined` |
| **Production batch** | The units a manufacturer makes in one go: at most `batch_size` units, taking `manufacturing_time`. Always say "production batch", never just "batch" (which means units with the same manufacturing date). | `batch_size`, `manufacturing_time` |

---

## Costs and results

| Term | Meaning | In the code |
|---|---|---|
| **Holding cost** | The cost of keeping one unit in inventory for one time unit, and the total of that cost over the run. | `inventory_holding_cost` (rate); `inventory_carry_cost` (total) |
| **Buy price, sell price** | What a site pays per unit, and what it charges per unit. | `product_buy_price`, `product_sell_price` |
| **Transportation cost** | The cost of sending one order over a link. | `Link.cost`; total in `transportation_cost` |
| **Revenue** | Sell price times the units the site fulfilled. | `revenue` |
| **Node cost** | Everything a site spent: holding, purchases, transportation, manufacturing, destroyed units, and so on. | `node_cost` |
| **Profit** | Revenue minus node cost. | `profit` |

---

## Disruptions

| Term | Meaning | In the code |
|---|---|---|
| **Disruption** | A period when a node or a link is out of action. While disrupted, a site receives no new orders (from other sites or from customers) and a link carries no new shipments. Orders it had already taken are still served. | `node_status == "inactive"`, `link.status == "inactive"` |
| **Disruption probability** | The chance, each time unit, that a disruption starts. | `failure_p` |
| **Recovery** | The end of a disruption. | `node_recovery_time`, `link_recovery_time` |
| **Disruption impact** | What a disruption does to the units at a site when it starts (for example, destroying all of them). | `disruption_impact` |

---

## Time

| Term | Meaning | In the code |
|---|---|---|
| **Time unit** | SupplyNetPy has no fixed unit of time. All times (lead times, shelf lives, run length) use the same unit; the examples usually read one time unit as one day. | `sim_time`, `env.now` |
| **Warm-up** | An opening stretch of a run that is left out of the statistics, because a run starts in an unusual state (nothing in transit, no orders waiting). Run for the warm-up period, reset the statistics, and carry on running. The simulation carries on unchanged. Only the counting starts again. | `stats.reset()` |
| **Event-driven** | How SupplyNetPy moves through time: it jumps from one event (an order, a delivery, an expiry) straight to the next, using SimPy. It does not step through time in fixed steps. | |
