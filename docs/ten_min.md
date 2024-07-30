# SupplyNetPy in 10 Minutes

SupplyNetPy is a Python library designed for modeling, simulation, design exploration, and optimization of supply chains and inventory systems. It allows users to create and simulate supply chain networks with various inventory replenishment policies.

## Installation

You can install SupplyNetPy using pip:

```sh
pip install -i https://test.pypi.org/simple/ supplynetpy
```

## Let's create a supply chain network

##### Importing the Library:
~~~python
import SupplyNetPy.Components as scm
~~~

SupplyNetPy's __Components__ module provides fundamental constructs for creating supply chain components such as supply chain nodes, node demand, products, inventory, and linking them in a network.

##### Create Supply Chain Nodes
Let us create a supplier node in the supply chain that provides some raw material to the manufacturer for manufacturing a product. It takes arguments such as ID, name, and inventory parameters. The supplier maintains inventory to make raw materials readily available. The supplier node is created using the `default_raw_material`. The default raw material is configured to have 1 unit cost per item; 30 units are mined per extraction cycle of 3 days. We can change the configuration of `default_raw_material` or create a new one according to our needs.

~~~python
supplier1 = scm.Supplier(ID="S1", name="Supplier 1", capacity=600, 
                         initial_level=600, inventory_holding_cost=1)
~~~

Let us create a manufacturing node and a distributor node in the supply chain network. These can be created with parameters quite similar to those above. These nodes take a `Product` as a parameter, which is produced by the `Manufacturer` and stored by `InventoryNode`. If no product object is passed, they will be initialized with a `default_product`. The `dafult_product` is configured to include manufacturing costs, time to manufacture, sell price, buy price, and number of units produced per cycle initialized to some values. We can check the parameter values by running `scm.default_product.get_info()` instruction. We can reconfigure the default product or create a new one.

~~~python
manufacturer1 = scm.Manufacturer(ID="M1", 
                                 name="Manufacturer 1",
                                 capacity=500, initial_level=300,
                                 inventoty_holding_cost=3,
                                 replenishment_policy="sS",
                                 policy_param=[200])

distributor1 = scm.InventoryNode(ID="D1",
                                 name="Distributor 1",
                                 node_type="distributor",
                                 capacity=300,
                                 initial_level=50,
                                 inventory_holding_cost=3,
                                 replenishment_policy="sS",
                                 policy_param=[30])
~~~

##### Creating Links 
Let us link these nodes in a supply chain network. In this example, we are creating a simple supply chain of three nodes; let us link the manufacturer to get the raw material from the supplier and the distributor to get the product from the manufacturer. We need to specify the link's transportation cost and lead time when we create them.

~~~python
link_sup1_man1 = scm.Link(ID="L1", source=supplier1, sink=manufacturer1, cost=5, lead_time=3)
link_man1_dis1 = scm.Link(ID="L3", source=manufacturer1, sink=distributor1, cost=50, lead_time=2)
~~~

##### Creating Demand
We are now ready to run the simulation. However, we still need to specify the demand for this chain. Since we do not have any retailer in the network yet, let us create demand at the distributor. Consider it a direct demand faced by the distributors (for example, a distributor faces a demand for custom-made products). Demand takes the order arrival and quantity models as callable functions. These can be a constant number or distribution generation functions to model order arrival and quantity.

~~~
demand_dis = scm.Demand(ID="demand_D1", name="Demand 1", order_arrival_model=lambda: 1,
                        order_quantity_model=lambda: 5, demand_node=distributor1)
~~~

##### Ready to Run
The supply chain has been set up with minimal requirements. At this point, we are ready to run the simulation using `scm.env.run()`. If you need a more detailed example, you can check out this [link](example.md).

__A better way to simulate__

SupplyNetPy offers a convenient function `create_sc` designed to help you create a supply chain network with nodes, links, products, and demand. This function adds metadata information to your supply chain, such as the number of nodes, retailers, manufacturers, and more, to keep everything organized. Once you've created the supply chain, you can access it using a single variable. Additionally, the `simulate_sc_net` function allows you to simulate the created supply chain over a specified period of time, and it calculates performance measures such as net profit, throughput, and more. Let's leverage these functions to create and simulate our supply chain.

~~~python
scnet = scm.create_sc_net(nodes=[supplier1, manufacturer1, distributor1], 
                          links=[link_sup1_man1, link_man1_dis1], 
                          demands=[demand_dis])

scm.simulate_sc_net(scnet, sim_time=30)
~~~

##### Putting everything together
~~~Python
# import the library
import SupplyNetPy.Components as scm

# Create a supply chain nodes
supplier1 = scm.Supplier(ID="S1", name="Supplier 1",
                         capacity=600, initial_level=600, inventory_holding_cost=1)

manufacturer1 = scm.Manufacturer(ID="M1", name="Manufacturer 1",
                                 capacity=500, initial_level=300, inventoty_holding_cost=3,
                                 replenishment_policy="sS", policy_param=[200])

distributor1 = scm.InventoryNode(ID="D1", name="Distributor 1", node_type="distributor",
                                 capacity=300, initial_level=50, inventory_holding_cost=3,
                                 replenishment_policy="sS", policy_param=[30])

# Create links between the nodes
link_sup1_man1 = scm.Link(ID="L1", source=supplier1, sink=manufacturer1, cost=5, lead_time=3)
link_man1_dis1 = scm.Link(ID="L3", source=manufacturer1, sink=distributor1, cost=50, lead_time=2)

# Create a demand
demand_dis = scm.Demand(ID="demand_D1", name="Demand 1", 
                        order_arrival_model=lambda: 1, order_quantity_model=lambda: 5,
                        demand_node=distributor1)

# Create a supply chain network
scnet = scm.create_sc_net(nodes=[supplier1, manufacturer1, distributor1],
                          links=[link_sup1_man1, link_man1_dis1],
                          demands=[demand_dis])

# Simulate the supply chain network
scm.simulate_sc_net(scnet, sim_time=30)
~~~