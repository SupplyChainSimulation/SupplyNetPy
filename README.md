# SupplyNetPy

SupplyNetPy is a Python library designed for modeling, simulation, design exploration, and optimization of supply chains and inventory systems. It allows users to create and simulate supply chain networks with various inventory replenishment policies.

## Installation

You can install SupplyNetPy using pip:

```sh
pip install supplynetpy
```

## Dependencies

[SimPy](https://simpy.readthedocs.io/en/latest/)

## Authors

- Tushar Lone [GitHub](https://github.com/tusharlone)
- Lekshmi P [GitHub](https://github.com/LekshmiPremkumar)
- Neha Karanjkar [GitHub](https://github.com/NehaKaranjkar)

## Quick Start
#### Creating supply chain networks
~~~
import SupplyNetPy.Components as scm

supplier1 = {'ID': 'S1', 'name': 'Supplier1', 'node_type': 'infinite_supplier'}

distributor1 = {'ID': 'D1', 'name': 'Distributor1', 'node_type': 'distributor', 
                'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 0.2, 
                'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s':100,'S':150},
                'product_buy_price': 100,'product_sell_price': 105}

link1 = {'ID': 'L1', 'source': 'S1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}

demand1 = {'ID': 'd1', 'name': 'Demand1', 'order_arrival_model': lambda: 1,
            'order_quantity_model': lambda: 10, 'demand_node': 'D1'}

# create a supply chain network
supplychainnet = scm.create_sc_net(nodes=[supplier1, distributor1], links=[link1], demands=[demand1])

# simulate for 20 days
supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=20, logging=True)
~~~

#### Modeling what a disruption does to stored inventory

In real life, a disruption is rarely just a pause — a flood can ruin every box in a warehouse, a power outage can spoil refrigerated goods, contamination can force a partial recall, and theft can take a slice of the shelf. SupplyNetPy lets you describe these *physical* effects on inventory in addition to simply marking a node as offline.

The basic disruption settings (`failure_p`, `node_disrupt_time`) only switch the node off and stop it from accepting new orders; they leave the stored stock untouched. To say what actually *happens* to the goods on the shelf when the disruption begins, set the `disruption_impact` option:

~~~python
# Scenario 1: total loss (e.g., warehouse fire, flood). Wipes everything on the shelf.
scm.InventoryNode(..., disruption_impact="destroy_all")

# Scenario 2: partial loss (e.g., power outage spoils some refrigerated goods).
# Here, 30% of whatever is on the shelf is destroyed each time a disruption hits.
# You can also pass a function instead of 0.3 to randomize the loss each time.
scm.InventoryNode(..., disruption_impact="destroy_fraction",
                  disruption_loss_fraction=0.3)

# Scenario 3: anything more specific (e.g., contamination of half the stock).
# Write a small Python function that describes what to do, and pass it in.
def contaminate(node):
    node.inventory.destroy(amount=node.inventory.level * 0.5,
                           reason="contamination")
scm.InventoryNode(..., disruption_impact=contaminate)
~~~

The loss is applied once, at the moment the disruption begins (not repeatedly during the outage). The amount lost and its monetary value are saved on the node as `node.stats.destroyed_qty` and `node.stats.destroyed_value`, and the value is automatically subtracted when the simulation calculates the node's profit — so you don't need to do that bookkeeping yourself.


## Documentation
For detailed documentation and advanced usage, please refer to the [official documentation](https://supplychainsimulation.github.io/SupplyNetPy/).