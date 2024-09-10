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

SupplyNetPy's __Components__ module provides fundamental constructs for creating supply chain components such as supply chain nodes, demand, products, inventory, and linking them in a network.

##### Create Supply Chain Nodes
Let us define a supplier node in the supply chain that provides a raw material to the manufacturer for manufacturing a product. It takes arguments such as ID, name, and type. In this example, we define an infinite supplier by specifying the type as infinite_supplier; this supplier can supply whatever amount the manufacturer requests without fail. The supplier node is created using the `default_raw_material`. The default raw material is configured to have 1 unit cost per item; 30 units are mined per extraction cycle of 3 days. We can change the configuration of `default_raw_material` or create a new one according to our needs.

~~~python
sup1 = {'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier'}
~~~

The supplier's behavior is to mine or extract the raw material and make it available for the manufacturer by maintaining an inventory. By default, the supplier is assumed to be associated with mining a single raw material and has infinite access to it.

Let us define a manufacturing node and a distributor node in the supply chain network. These can be created with parameters quite similar to those above. These nodes take a `Product` as a parameter, which is produced by the `Manufacturer` and stored by `InventoryNode`. If no product object is passed, they will be initialized with a `default_product`. The `dafult_product` is configured to include manufacturing costs, time to manufacture, sell price, buy price, and number of units produced per cycle initialized to some values. We can check the parameter values by running `scm.default_product.get_info()` instruction. We can reconfigure the default product or create a new one.

~~~python

man1 = {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer',
      'capacity': 300, 'initial_level': 200, 'inventory_holding_cost': 0.5,
      'replenishment_policy': 'sS', 'policy_param': [150],'product_sell_price': 310}

dis1 = {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor',
      'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 1,
      'replenishment_policy': 'sS', 'policy_param': [40],'product_sell_price': 320},
~~~
[qt]: ## "(Q,T): Replenish inventory every T days with Q units."
[ss]: ## "Continuously monitor inventory; replenish it to capacity S when the level goes below s."

When creating a manufacturer, distributor, wholesaler, or retailer, we must specify the inventory replenishment policy and policy parameters. Currently, we have only two replenishment policies: [periodic][qt] replenishment and [reorder-level (s,S)][ss] replenishment.

##### Creating Links 
Let us link these nodes in a supply chain network. In this example, we are creating a simple supply chain of three nodes; let us link the manufacturer to get the raw material from the supplier and the distributor to get the product from the manufacturer. We need to specify the link's transportation cost and lead time when we create them.

~~~python
ln1 = {'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': lambda: 3}
ln2 = {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}
~~~

##### Creating Demand
We are now ready to run the simulation. However, we still need to specify the demand for this chain. Since we do not have any retailer in the network yet, let us create demand at the distributor. Consider it a direct demand faced by the distributors (for example, a distributor faces a demand for custom-made products). Demand takes the order arrival and quantity models as callable functions. These can be a constant number or distribution generation functions to model order arrival and quantity.

~~~python
d1 = {'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 
      'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10, 'demand_node': 'D1'}
~~~

##### Ready to Run

To create and simulate the supply chain, we must use the `create_sc_net` function to create instances of the above-defined supply chain nodes and assemble them in a network. This function adds metadata information to your supply chain, such as the number of nodes, retailers, and more, to keep everything organized. It returns a Python dictionary containing all supply chain components and meta-data. We use the `simulate_sc_net` function to simulate the supply chain network over a specific time and view the log of the simulation run. It also calculates performance measures such as net profit, throughput, and more. Let's leverage these functions to create and simulate our supply chain.

~~~python
scnet = scm.create_sc_net([sup1, man1, dis1], [ln1, ln2], [d1])
scnet = scm.simulate_sc_net(scnet, sim_time=10)
~~~

##### Putting everything together
~~~Python
# import the library
import SupplyNetPy.Components as scm

sup1 = {'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier'}

man1 = {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer',
      'capacity': 300, 'initial_level': 200, 'inventory_holding_cost': 0.5,
      'replenishment_policy': 'sS', 'policy_param': [150],'product_sell_price': 310}

dis1 = {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor',
      'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 1,
      'replenishment_policy': 'sS', 'policy_param': [40],'product_sell_price': 320},

ln1 = {'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': lambda: 3}
ln2 = {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}

d1 = {'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 
      'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10, 'demand_node': 'D1'}

scnet = scm.create_sc_net([sup1, man1, dis1], [ln1, ln2], [d1])
scnet = scm.simulate_sc_net(scnet, sim_time=10)
~~~

Visit detailed examples [here](example.md) for more.