# Customer Demand

Imagine a bakery. Customers come in through the day, one every few minutes, and each buys a few loaves. Some days are busy and some are quiet. A customer who finds too little bread may walk out, may take the loaves that are left, or may wait for the next batch from the oven. In SupplyNetPy, this stream of customers is a customer demand, and each customer places one customer order at a site.

This guide shows how to create a customer demand, how to set how often customers order and how many units, at random or from recorded data, what customers do when the site is short of units, and how their orders are delivered. The words used here are explained in the [Glossary](../glossary.md).

## Creating a customer demand

A customer demand needs an ID, a name, the site its customers order from (`demand_node`), the time units between one customer order and the next (`order_arrival_model`), and the units in each order (`order_quantity_model`). In a dict netlist, the site is given by its ID.

```python
demand = {'ID': 'd1', 'name': 'Bakery customers', 'demand_node': 'R1',
          'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10}
```

Created as an object, the customer demand takes the site itself.

```python
demand = scm.Demand(env=env, ID='d1', name='Bakery customers', demand_node=retailer,
                    order_arrival_model=lambda: 1, order_quantity_model=lambda: 10)
```

The site can be any site except a raw-material supplier, usually a retailer or a distributor. Every setting is listed under _Demand_ in the [API reference](../api-reference/api-ref-core.md).

## How often and how many units

Both settings can be a number or a function with no arguments that returns one. The function is called again for every customer order, so a random function gives every order its own time and size. The first customer order arrives at time 0, and each later one after the time units that `order_arrival_model` returns.

```python
import random

'order_arrival_model': lambda: random.expovariate(1 / 2),   # one order every 2 time units on average
'order_quantity_model': lambda: random.randint(1, 6),       # between 1 and 6 units
```

Every customer order must be for more than 0 units. If `order_quantity_model` returns 0, the run stops with an error, so a distribution that can give 0 must be kept at 1 or more.

These functions use Python's own random numbers, so to repeat the same demand in another run, seed them with `random.seed(n)`. `scm.set_seed(n)` seeds only the random numbers of the library itself, such as those of random disruptions.

## Demand from recorded data

To replay past sales, pick each value from a list by the simulation time, as below, rather than with a counter that moves on at every call. SupplyNetPy calls the function when the customer demand is created, to check that it returns a number, so a counter would skip values.

```python
sales = [4, 7, 2, 9, 5]                  # units sold on each day
env = simpy.Environment()
demand = {'ID': 'd1', 'name': 'Past sales', 'demand_node': 'R1',
          'order_arrival_model': lambda: 1,
          'order_quantity_model': lambda: sales[int(env.now) % len(sales)]}
sc = scm.create_sc_net(nodes, links, [demand], env=env)
```

The function reads the simulation time from `env`, so create the environment yourself and pass it to `create_sc_net`. The `% len(sales)` starts the list again when it runs out.

## When the site is short of units

When a customer order arrives and the site has enough units, the customer gets the whole order. When it does not, what the customer does depends on the settings below.

| Setting | What the customer does |
|---|---|
| None of them (the default) | Leaves at once without any units |
| `consume_available=True` | Takes the units that are there and leaves |
| `tolerance` above 0 | Waits up to `tolerance` time units for the units, then leaves without the rest |
| `tolerance`, and `order_min_split_ratio` below 1 | Waits, and accepts partial deliveries of at least that share of the order |

With both `consume_available` and a `tolerance`, the customer takes the units that are there, and waits only if there are none at all.

A waiting customer's order counts as a backorder at the site, and the site's [replenishment policy](replenishment-policies.md) checks at once whether to order. The customer checks again each time units arrive at the site. If the tolerance runs out first, the customer leaves, and the units still missing are lost sales. With a tolerance of `float('inf')`, the customer waits as long as it takes.

Say a customer orders 20 units when the site has 15, with `order_min_split_ratio=0.5`. The smallest partial delivery they accept is then 10 units, so they get the 15 at once and wait for the other 5. With `0.9`, the smallest partial delivery is 18 units, so the 15 are not enough and the customer waits for all 20. Either way, the order counts as fulfilled once, when its last units are delivered.

If even the smallest part a waiting customer accepts is more than the capacity of the site, the order can never be filled. The customer is not left waiting, and the whole order is recorded at once as a shortage and as lost sales.

How each case shows up in `shortage`, `backorder` and `lost_sales` is explained, with the same order of 20 units, in the [Statistics and Results](statistics.md) guide. A customer who arrives while the site is disrupted is turned away, as described in the [Disruptions](disruptions.md) guide.

## Delivering the order

By default, a customer gets the units at once. `lead_time` sets the time units from the site to the customer, and `delivery_cost` the cost of delivering each customer order. Both can be a number or a function.

The units leave the site's inventory when the order is served, but the order counts as fulfilled, at the site and for the customer demand, only when it reaches the customer. The site's revenue is counted then too. The delivery cost is recorded as the transportation cost of the customer demand, not of the site. So it is part of the total cost and profit of the network, but not of the site's node cost.

## Several customer demands

A site can have more than one customer demand, for example customers who come to the shop and customers who order online, with a lead time and a delivery cost. Each is its own customer demand with the same `demand_node`.

```python
demands = [{'ID': 'walk_in', 'name': 'Walk in', 'demand_node': 'R1',
            'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 4},
           {'ID': 'online', 'name': 'Online', 'demand_node': 'R1',
            'order_arrival_model': lambda: 2, 'order_quantity_model': lambda: 6,
            'lead_time': 3, 'delivery_cost': 2}]
```

The customer demands share the site's inventory. The site's statistics count the orders of all of them together, and each customer demand keeps its own. A distributor can also have its own customers while it supplies retailers.

## Statistics of a customer demand

A customer demand records the customer orders placed (`demand_placed`), those that reached the customers (`fulfillment_received`) and the delivery costs (`transportation_cost`), read with `demand.stats.get_statistics()`. Everything about shortages, backorders, lost sales and waiting is recorded at the site. See the [Statistics and Results](statistics.md) guide.
