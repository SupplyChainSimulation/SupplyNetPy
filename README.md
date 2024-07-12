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

# lets create a single product supply chain with just one retailer
# lets create a product
product1 = scm.Product(sku="12325",name="Brush",description="Cleaning supplies",cost=200,profit=100,product_type="Non-perishable",shelf_life=None)

# lets create a retailer 
retailer1 = scm.Retailer(env=env,name=f"retailer1",node_id=125,location="Mumbai",products=[product1],inv_capacity=300,
                         inv_holding_cost=3,reorder_level=100,)

# lets create some random demand at this retailer using Poisson distribution
demand_ret1 = scm.Demand(env=env, arr_dist="Poisson",arr_params=[6],node=retailer1,demand_dist="Uniform",demand_params=[1,10])

# lets assemble all nodes into a supply chain network
scnet = scm.createSC(products=[product1],
                     nodes = [retailer1],
                     links = [],
                     demands = [demand_ret1])

# lets simulate it and see the log on screen
# by deafult the logging is set to appear on screen,
# and also written in a file called simulation.log under directory 'simlog'

# lets change it to appear on the screen for now
scm.global_logger.enable_logging(log_to_file=False,log_to_screen=True)
scm.simulate_sc_net(env,scnet,sim_time=20)
~~~


## Documentation
For detailed documentation and advanced usage, please refer to the [official documentation](#).