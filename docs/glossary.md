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
| **Link** | The transport connection that carries goods from one site to another. It has a cost per order and a lead time. | `Link`. Its statistics (the replenishment orders its buyer placed over it, what arrived, and its disruptions) are in `link.stats`. |
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
| **Average inventory level** | The inventory level averaged over time, so that each level counts for as long as it lasted. Holding 10 units for 3 time units and then 4 units for 2 time units gives (10 × 3 + 4 × 2) / 5 = 7.6. | `stats.avg_inventory_level`, worked out from `stats.inventory_level_time` (the sum of inventory level × time) |
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
| **Lead time** | How long an order takes to arrive after it is sent: over a link, or from a site to a customer. | `Link.lead_time`, `Demand.lead_time`. Over a link, the total and the average are `link.stats.lead_time` and `link.stats.avg_lead_time`. |
| **Backorder** | An order, or part of one, that a site owes right now: it has been accepted but is still waiting for units. It is removed once it is filled, or when a waiting customer gives up. | `stats.backorder`, as `[orders, units]` |
| **Shortage** | How many units a site was missing when an order arrived. It is a running total, never reduced, whether the order is later filled or not. Customers turned away by a disruption are not part of it (see disruption lost sales). | `stats.shortage`, as `[orders, units]` |
| **Disruption lost sales** | Customer orders a site lost because it was disrupted when they arrived. A disrupted site takes no new orders, so the customer goes away. Kept apart from shortage, which counts units the site did not have, because the cause and the remedy differ. | `stats.disruption_lost_sales`, as `[orders, units]` |
| **Lost sales** | Customer units a site never delivered, for any reason other than a disruption. A customer with no tolerance who finds too few units, the rest of an order when the customer takes only what is there, an order too big for the site ever to hold, and what a waiting customer was still owed when they gave up. Unlike shortage, it counts only units that were never delivered. Everything a site lost is lost sales plus disruption lost sales. | `stats.lost_sales`, as `[orders, units]` |
| **Blocked order** | A replenishment order a site could not place, because every supplier it has (or the link to it) was disrupted. It is not lost. The site orders again when a supplier or a link recovers. A site with no supplier at all has no blocked orders, because no recovery would ever let its orders through. That is a mistake in how the network is built, and a warning says so. | `stats.blocked`, as `[orders, units]` |
| **Waiting time** | How long an order waited at a site before its units left the inventory, for orders that could not be served at once. Orders served at once wait 0. | `stats.waited`, `stats.waiting_time`, `stats.avg_waiting_time`. For the replenishment orders a buyer placed over a link, the same names in `link.stats`. |
| **Order cycle time** | How long a replenishment order takes from the moment the buyer places it until it arrives. It is the waiting time at the supplier plus the lead time. | `link.stats.avg_order_cycle_time` |
| **Fill rate** | The share of the units ordered that the supplier sent at once, without the order having to wait. An order that had to wait counts as not sent at once, even if part of it was there. The **order fill rate** is the same share counted in orders instead of units. A fill rate of 1 means no order ever waited. | `link.stats.fill_rate`, `link.stats.order_fill_rate` |
| **Bullwhip effect** | Orders becoming more and more uneven as they pass from the customers towards the raw-material suppliers. Customers may buy about the same amount every day, while their retailer orders in large irregular amounts, and its supplier in even larger swings. It is measured per time unit. Compare the standard deviation of the units ordered over a link in each time unit with that of the customer demand in each time unit. | `link.stats.units_per_time_unit_std` |
| **Dropped units** | Units of a delivery that did not fit in the inventory of the site that ordered them, when no waiting customer could take them either. The site does not pay for them, and they are not stored. | `stats.dropped_qty` |
| **Tolerance** | How long a customer is willing to wait for units that are not there. A customer with no tolerance leaves at once. | `tolerance` |
| **Partial delivery** | Sending a customer part of an order now and the rest later. | `order_min_split_ratio` |
| **Deadlock** | Two parts of a model each waiting for the other, so neither ever moves again. For example, a buyer waits for an order larger than its supplier's capacity, and the supplier can never hold enough units to send it. SupplyNetPy warns about this when the link between them is created. | |

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
| **Fixed mode**, **dynamic mode** | How often a supplier-selection policy chooses. In dynamic mode it chooses again for every replenishment order. In fixed mode it keeps the first supplier it chose, and uses another only while that supplier or the link to it is disrupted. | `supplier_selection_mode`, `"fixed"` (the default) or `"dynamic"` |

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
| **Standard deviation** | How far values usually are from their average. SupplyNetPy uses the sample standard deviation, which divides by one less than the number of values. With fewer than two values it is not defined and is given as `None`. | `link.stats.order_size_std` (one value per order), `link.stats.units_per_time_unit_std` (one value per time unit) |

---

## Disruptions

| Term | Meaning | In the code |
|---|---|---|
| **Disruption** | A period when a node or a link is out of action. While disrupted, a site receives no new orders (from other sites or from customers) and a link carries no new shipments. Orders it had already taken are still served. | `node_status == "inactive"`, `link.status == "inactive"` |
| **Disruption probability** | The chance, each time unit, that a disruption starts. | `failure_p` |
| **Recovery** | The end of a disruption. | `node_recovery_time`, `link_recovery_time` |
| **Availability** | The share of time a node or a link was not disrupted. | `stats.availability`, worked out from `stats.disruptions` and `stats.disrupted_time`. For a link, the same names in `link.stats`. |
| **Disruption impact** | What a disruption does to the units at a site when it starts (for example, destroying all of them). | `disruption_impact` |

---

## Time

| Term | Meaning | In the code |
|---|---|---|
| **Time unit** | SupplyNetPy has no fixed unit of time. All times (lead times, shelf lives, run length) use the same unit; the examples usually read one time unit as one day. | `sim_time`, `env.now` |
| **Warm-up** | An opening stretch of a run that is left out of the statistics, because a run starts in an unusual state (nothing in transit, no orders waiting). Run for the warm-up period, reset the statistics, and carry on running. The simulation carries on unchanged. Only the counting starts again. | `stats.reset()` for one node, `link.stats.reset()` for one link, and `reset_stats(supplychainnet)` or `Network.reset_stats()` for every node, customer demand and link |
| **Event-driven** | How SupplyNetPy moves through time: it jumps from one event (an order, a delivery, an expiry) straight to the next, using SimPy. It does not step through time in fixed steps. | |
