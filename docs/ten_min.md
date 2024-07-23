# SupplyNetPy in 10 Minutes

SupplyNetPy is a Python library designed for modeling, simulation, design exploration, and optimization of supply chains and inventory systems. It allows users to create and simulate supply chain networks with various inventory replenishment policies.

## Installation

You can install SupplyNetPy using pip:

```sh
pip install supplynetpy
```

## Dependencies

[SimPy](https://simpy.readthedocs.io/en/latest/)

Install SimPy:

```sh
pip install simpy
```

## Let's create a supply chain network

##### Importing the Library:
~~~
import SupplyNetPy.Components as scm
~~~

SupplyNetPy's __Components__ module provides fundamental constructs for creating supply chain components such as supply chain nodes, node demand, products, inventory, and linking them in a network.

##### Creating SimPy Environment
SupplyNetPy is built on top of SimPy and uses the SimPy environment to create and simulate the supply chain model. Therefore, we need to create a SimPy environment before creating a supply chain model.
~~~
import simpy
env = simpy.Environment()
~~~

##### Creating a Product
To create a supply chain network, let's begin by creating a product that moves through the supply chains and generates revenue. Afterward, we can create nodes and links.

~~~
product1 = scm.Product(sku="12325",name="Brush",description="Cleaning supplies",cost=400,profit=50,
                       product_type="Non-perishable",shelf_life=None)
~~~

##### Create Supply Chain Nodes
Let's create a node in the supply chain, such as a retailer, that manages the inventory of `product1` and directly sells to the end customer.

~~~
retailer1 = scm.Retailer(env=env,name=f"retailer1",node_id=125,location="Mumbai",products=[product1],
                         inv_capacity=300,inv_holding_cost=3,reorder_level=100)
~~~

Notice that _retailer1_ was created with inventory parameters, holding a `single_product_inventory` by default. It can be changed to `mixed_inventory` type when managing multiple products.

##### Creating Demand
We are now ready to run the simulation. However, we have forgotten to specify the demand that `retailer1` is facing. We need to create demand at `retailer1`.
~~~
demand_ret1 = scm.Demand(env=env, arr_dist="Poisson",arr_params=[6],
                         node=retailer1,demand_dist="Uniform",demand_params=[1,10])
~~~

##### Ready to Run
The single node supply chain has been set up with minimal requirements. At this point, we are ready to run the simulation using `env.run()`. It's important to note that the retailer is not currently linked to any warehouses. This means that once the retailer's inventory depletes, it won't be able to restock its products. Consequently, the simulation will continue, customers will keep arriving at `retailer1`, and they will leave without making a purchase. When we expand the network to include multiple nodes, we will be able to observe the supply chain in action. If you need a more detailed example, you can check out this link.

__A better way to simulate__

SupplyNetPy offers a convenient function `createSC` designed to help you create a supply chain network with nodes, links, products, and demand. This function adds metadata information to your supply chain, such as the number of nodes, retailers, manufacturers, and more, to keep everything organized. Once you've created the supply chain, you can access it using a single variable. Additionally, the `simulate_sc_net` function allows you to simulate the created supply chain over a specified period of time, and it calculates performance measures such as net profit, throughput, and more. Let's leverage these functions to create and simulate our supply chain.

~~~
scnet = scm.createSC(products=[product1],
                     nodes = [retailer1],
                     links = [],
                     demands = [demand_ret1])

scm.simulate_sc_net(env,scnet,sim_time=20)
~~~

##### Putting everything together
~~~
# import the library
import SupplyNetPy.Components as scm

# import simpy and create enviornment
import simpy
env = simpy.Environment()

# lets create a single product supply chain with just one retailer
# lets create a product
product1 = scm.Product(sku="12325",name="Brush",description="Cleaning supplies",cost=400,profit=50,product_type="Non-perishable",shelf_life=None)
# lets create a retailer 
retailer1 = scm.Retailer(env=env,name=f"retailer1",node_id=125,location="Mumbai",products=[product1],inv_capacity=300, inv_holding_cost=3,reorder_level=100,)

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