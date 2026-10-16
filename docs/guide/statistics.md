# Statistics and Results

Imagine you have just simulated a year of a supply chain with one distributor and three retailers. Now come the questions. Did the network make a profit? Did the retailers serve their customers, or did they run short? Which retailer held too much inventory? And which supplier, or which link, kept the others waiting? SupplyNetPy answers these at three levels, the whole network, each node, and each link.

This guide shows where each answer is found, how to read it, and how to leave the first part of a run out of the statistics with a warm-up. The words used here are explained in the [Glossary](../glossary.md).

## Results for the whole network

`simulate_sc_net` adds the results for the whole network to the dictionary it is given. They are added up from every node, and include the total cost, the revenue and the profit, the orders placed and received, the shortage, the lost sales and the backorders.

```python
scm.simulate_sc_net(sc, sim_time=365)
print(sc["profit"], sc["total_cost"], sc["shortage"])
```

With a `Network`, the same results are in `net.results`. What each result means is listed under `simulate_sc_net` in the [API reference](../api-reference/api-ref-utilities.md).

## Statistics of a node

Every node keeps its own statistics in `node.stats`. Read them with `node.stats.get_statistics()`, or print a table of several nodes side by side with `print_node_wise_performance`.

```python
print(sc["nodes"]["R1"].stats.get_statistics())                        # one node
scm.print_node_wise_performance(sc["nodes"].values())                 # every node, as a table
rows = scm.get_node_wise_performance(sc["nodes"].values())            # every node, as data
```

`get_node_wise_performance` returns the values as data, ready for a pandas DataFrame, and `format_node_wise_performance` returns the table as text.

The statistics answer a few kinds of question. Counts of orders are given as `[number of orders, units]`.

| Question | Statistics |
|---|---|
| How many orders went in and out? | `demand_placed` and `fulfillment_received` for the orders the site placed and what arrived, `demand_received` and `demand_fulfilled` for the orders placed with it and those it fulfilled |
| Did the site serve its orders? | `shortage`, `backorder`, `lost_sales`, `waited`, `avg_waiting_time` |
| How much inventory did it hold? | `inventory_level` at the end, `avg_inventory_level`, `zero_inventory_share` (the share of time it had no units), `inventory_waste` (expired units), `dropped_qty` (delivered units that did not fit) |
| How did disruptions affect it? | `disruptions`, `disrupted_time`, `availability`, `blocked`, `disruption_lost_sales`, explained in the [Disruptions](disruptions.md) guide |
| What did it cost and earn? | `inventory_carry_cost` (the holding cost), `inventory_spend_cost` (what it paid for the units it received), `transportation_cost`, `destroyed_value`, then `node_cost` (all of them added up), `revenue` and `profit` |

A raw-material supplier also records what it mined and what mining cost, and a manufacturer what it made and what making it cost. Both costs are part of its `node_cost`.

Three of these are easy to mix up.

* `shortage` counts the units a site was missing when an order arrived. It is a running total and is never reduced, even if the order is filled later.
* `backorder` is what the site owes right now, the orders still waiting for units.
* `lost_sales` counts the customer units the site never delivered, for example because the customer would not wait.

So a customer who orders 20 units when the site has 15 adds 5 to `shortage`, whatever happens next. The rest depends on the customer.

* A customer who does not wait (the default) leaves without any units, so all 20 are lost sales. With `consume_available`, the customer takes the 15 units, and only the missing 5 are lost sales.
* A customer who waits (a customer demand with a `tolerance`) puts the whole order of 20 in `backorder` until the units are there. If the wait runs past the tolerance, the customer gives up and the 20 units are lost sales.

Averages and shares are worked out when they are read, from the totals. When there is nothing to divide by yet, for example `avg_waiting_time` before any order has been fulfilled, the value is `None`. The inventory values are also `None` for an infinite supplier and for a customer demand, which have no inventory to measure.

A customer demand has statistics too. `demand_placed` and `fulfillment_received` show what its customers ordered and what reached them.

## Statistics of a link

Imagine a retailer that buys from two distributors. Its node statistics say how much it ordered and received in total, but not how much came from each distributor, how long each one made it wait, or how often each link was disrupted. Every link keeps its own statistics for this, in `link.stats`. They count the replenishment orders the buyer placed over the link, what arrived, the shortage and backorders at the supplier, the waiting time (how long orders waited at the supplier before they were sent), the lead time, the costs, and the disruptions of the link. From these totals they work out averages such as the fill rate (the share of the units ordered that the supplier sent at once, without the order having to wait), the order cycle time (waiting time plus lead time) and the availability of the link.

Read one link with `link.stats.get_statistics()`, or several at once with `print_link_wise_performance(links)`, which prints the same kind of table as `print_node_wise_performance`. For the view of one site, pass its links. `node.suppliers` holds the links the site orders over, and `node.buyers` holds the links its buyers order over.

```python
retailer = sc["nodes"]["R1"]
scm.print_link_wise_performance(retailer.suppliers)           # what R1 ordered, and from whom
scm.print_link_wise_performance(sc["nodes"]["D1"].buyers)     # who ordered from D1
rows = scm.get_link_wise_performance(sc["links"].values())   # every link, as data
```

`get_link_wise_performance` returns the values as data, and `format_link_wise_performance` returns the table as text. The full example is in `examples/py/link_statistics.py`.

Link statistics count replenishment orders only. Customers do not order over links, so customer demand is found in the statistics of each customer demand. The figures on the links of a site add up to the figures of the site itself, so the two can be checked against each other. One exception is `blocked`. An order that no supplier can take is never sent over any link, so it is counted only at the buyer.

Two statistics describe how uneven the orders are, and they answer different questions. `order_size_std` is the standard deviation of the order sizes, and `units_per_time_unit_std` is the standard deviation of the units ordered in each time unit, where a time unit with no order counts as 0. A distributor that orders 60 units at time 3 and 60 units at time 7 has an `order_size_std` of 0, because every order is the same size, but a large `units_per_time_unit_std`, because its orders come in bursts. Compare `units_per_time_unit_std` along the supply chain to measure the bullwhip effect, the way orders become more uneven as they pass from the customers towards the raw-material suppliers.

## Warm-ups

A run starts in an unusual state. Every site starts with its initial inventory level, nothing is in transit, and no orders are waiting. If you are interested in how the network behaves once it has settled, leave this first stretch out of the statistics with a warm-up. Run for the warm-up period, reset the statistics, and carry on running.

```python
scm.simulate_sc_net(sc, sim_time=30)    # warm-up
scm.reset_stats(sc)
scm.simulate_sc_net(sc, sim_time=230)   # the measured period
```

`reset_stats(sc)` starts the statistics of every node, customer demand and link again in one call, and the results of the second `simulate_sc_net` cover only the measured period, from 30 to 230. With a `Network`, the same is `net.simulate(30).reset_stats().simulate(230)`. To reset only one node or one link, call `node.stats.reset()` or `link.stats.reset()`.

A reset changes only the counting, not the simulation. The running totals go back to zero and the clock of each statistic starts at the moment of the reset, so the averages cover the measured period only. What describes the present is kept, such as the orders still waiting in `backorder` and the current inventory level, and so are the inventory, the orders in transit and any disruption still going on.
