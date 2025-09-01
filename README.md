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
# import the library
import SupplyNetPy.Components as scm

# import simpy and create enviornment
import simpy
env = simpy.Environment()

# let us define a supplier with infinite supply
supplier1 = {'ID': 'S1', 'name': 'Supplier1', 'node_type': 'infinite_supplier'}

# a distributor with inventory
distributor1 = {'ID': 'D1', 'name': 'Distributor1', 'node_type': 'distributor', 
                'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 0.2,  # inventory params
                'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s':100,'S':150}, # inventory params
                'product_buy_price': 100,'product_sell_price': 105}

# linking supplier1 with distributor1
link1 = {'ID': 'L1', 'source': 'S1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}

# define demand at the distributor
demand1 = {'ID': 'd1', 'name': 'Demand1', 'order_arrival_model': lambda: 1,
            'order_quantity_model': lambda: 10, 'demand_node': 'D1'}

# create a supply chain network
supplychainnet = scm.create_sc_net(nodes=[supplier1, distributor1], links=[link1], demands=[demand1])

# simulate and see results
supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=20, logging=True)
~~~


## Documentation
For detailed documentation and advanced usage, please refer to the [official documentation](https://supplychainsimulation.github.io/SupplyNetPy/).