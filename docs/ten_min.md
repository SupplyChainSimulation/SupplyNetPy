# SupplyNetPy in 10 Minutes

## Installation

You can install SupplyNetPy using pip:

```sh
pip install -i https://test.pypi.org/simple/ supplynetpy
```

## Quick Start: Building a Simple Three-Node Supply Chain

Follow these steps to create and simulate a basic supply chain with a supplier and a manufacturer:

![alt text](img_two_node_sc.png)

### 1. Import the Library

```python
import SupplyNetPy.Components as scm
```

The `Components` module in SupplyNetPy offers essential building blocks for constructing supply chain networks. It enables you to define supply chain nodes, products, inventory, demand, and the links that connect them. Using these constructs, you can easily assemble and customize supply chain models to suit your requirements.

### 2. Define the Nodes

Let's define a supplier node in the supply chain that provides raw materials to the manufacturer for product assembly. The supplier node requires arguments such as `ID`, `name`, and `node_type`. In this example, we specify the type as `infinite_supplier`, meaning the supplier can fulfill any quantity requested by the manufacturer without limitation. The supplier node is created using the `default_raw_material`, which is configured with a unit cost of 1 per item, mining 30 units per extraction cycle of 3 days. You can modify the configuration of `default_raw_material` or create a new one to suit your requirements.

```python
supplier = {'ID': 'S1', 'name': 'Supplier', 'node_type': 'infinite_supplier'}
```

The supplier's behavior is to mine or extract raw materials and make them available to the manufacturer by maintaining an inventory. By default, the supplier is assumed to be associated with mining a single raw material and has infinite access to it.

Next, let's define a manufacturing node and a distributor node in the supply chain network. These can be created with parameters similar to those used above. These nodes take a `Product` as a parameter, which is produced by the `Manufacturer` and stored by the `InventoryNode`. If no product object is provided, they will be initialized with a `default_product`. The `default_product` is configured with manufacturing costs, manufacturing time, sell price, buy price, and the number of units produced per cycle, all set to default values. You can check these parameter values by running the `scm.default_product.get_info()` instruction. You may also reconfigure the default product or create a new one as needed.

```python
manufacturer = {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 300, 'initial_level': 200,
                'inventory_holding_cost': 0.5, 'replenishment_policy': scm.SSReplenishment,
                'policy_param': {'s':200,'S':300},'product_sell_price': 100}

distributor = {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 150, 'initial_level': 50,
                'inventory_holding_cost': 1, 'replenishment_policy': scm.SSReplenishment,
                'policy_param': {'s':100,'S':150},'product_buy_price': 100,'product_sell_price': 105}
```

[qt]: ## "(Q,T): Replenish inventory every T days with Q units."
[ss]: ## "Continuously monitor inventory; replenish up to S when the level drops below s."
[sssafety]: ## "Reorder-level (s,S) replenishment with safety stock — like (s,S) but considers a predefined safety stock buffer."
[rq]: ## "Replenish a fixed quantity Q whenever an order is placed (RQ policy)."
[periodic]: ## "Replenish at regular periodic intervals (Periodic policy)."

When creating a manufacturer, distributor, wholesaler, or retailer, you must specify the inventory replenishment policy and its parameters.

Currently, SupplyNetPy supports the following replenishment policies:

- [Reorder-level (s,S)](api-reference/api-ref-core.md#ssreplenish) — continuously monitor inventory and replenish up to S when the level drops below s.
- [Reorder-level (s,S) with Safety Stock](api-reference/api-ref-core.md#sssafetyreplenish) — reorder-level replenishment that factors in a safety stock buffer.
- [Replenish Quantity (RQ)](api-reference/api-ref-core.md#rqreplenish) — reorder a fixed quantity Q when placing an order.
- [Periodic (T,Q)](api-reference/api-ref-core.md#periodicreplenish) — replenish inventory every T days with Q units.

### 3. Create a Link

Let's connect these nodes to form a supply chain network. In this example, we are building a simple supply chain with three nodes: the manufacturer receives raw materials from the supplier, and the distributor obtains finished products from the manufacturer. When creating these links, be sure to specify the transportation cost and lead time for each connection.

```python
link_s1m1 = {'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': lambda: 3}
link_m1d1 = {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}
```

### 4. Specify Demand

We are now ready to run the simulation, but we still need to specify the demand for this supply chain. Since there is no retailer in the network yet, let's create demand at the distributor. This represents direct demand faced by the distributor (for example, a distributor receiving orders for custom-made products). Demand requires both the order arrival and order quantity models to be provided as callable functions. These can be constant values or random number generators to model order arrivals and quantities.

```python
demand = {'ID': 'demand_D1', 'name': 'Demand at Distributor', 'node_type': 'demand',
          'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10, 'demand_node': 'D1'}
```

### 5. Assemble and Simulate the Network

To create and simulate the supply chain, use the `create_sc_net` function to instantiate the supply chain nodes and assemble them into a network. This function adds metadata to your supply chain, such as the number of nodes, and other relevant information, keeping everything organized. It returns a Python dictionary containing all supply chain components and metadata. The `simulate_sc_net` function then simulates the supply chain network over a specified period and provides a log of the simulation run. It also calculates performance measures such as net profit, throughput, and more. Let's use these functions to build and simulate our supply chain.

```python
scnet = scm.create_sc_net([supplier, manufacturer, distributor], [link_s1m1, link_m1d1], [demand])
scnet = scm.simulate_sc_net(scnet, sim_time=30)
```

### 6. Review Results

After the simulation, inspect `scnet` to view performance metrics for the supply chain nodes. By default, the simulation log is displayed in the console and also saved to a local file named `simulation_trace.log` in the same directory as your Python script. Below is a sample simulation log generated by this program.

<div id="" style="overflow:scroll; height:600px;">
```
INFO sim_trace - 0.0000:M1: Inventory levels:200
INFO sim_trace - 0.0000:D1: Inventory levels:50
INFO sim_trace - 0.0000:D1:Replenishing inventory from supplier:Manufacturer 1, order placed for 100 units.
INFO sim_trace - 0.0000:M1:Replenishing raw material:Raw Material 1 from supplier:S1, order placed for 300 units. Current inventory level: {'RM1': 0}.
INFO sim_trace - 0.0000:D1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 0.0000:M1: Inventory levels:100
INFO sim_trace - 0.0000:demand_D1:Customer1:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 0.0000:D1: Inventory levels:40
INFO sim_trace - 0.0000:M1:shipment in transit from supplier:Supplier 1.
INFO sim_trace - 0.0000:demand_D1:Customer1:Demand at Distributor 1, Order quantity:10 received. Current inv: 40
INFO sim_trace - 1.0000:demand_D1:Customer2:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 1.0000:D1: Inventory levels:30
INFO sim_trace - 1.0000:demand_D1:Customer2:Demand at Distributor 1, Order quantity:10 received. Current inv: 30
INFO sim_trace - 2.0000:D1:Inventory replenished. reorder_quantity=100, Inventory levels:130
INFO sim_trace - 2.0000:demand_D1:Customer3:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 2.0000:D1: Inventory levels:120
INFO sim_trace - 2.0000:demand_D1:Customer3:Demand at Distributor 1, Order quantity:10 received. Current inv: 120
INFO sim_trace - 3.0000:M1:Order received from supplier:Supplier 1, inventory levels: {'RM1': 300}
INFO sim_trace - 3.0000:demand_D1:Customer4:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 3.0000:D1: Inventory levels:110
INFO sim_trace - 3.0000:demand_D1:Customer4:Demand at Distributor 1, Order quantity:10 received. Current inv: 110
INFO sim_trace - 4.0000:demand_D1:Customer5:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 4.0000:D1: Inventory levels:100
INFO sim_trace - 4.0000:D1:Replenishing inventory from supplier:Manufacturer 1, order placed for 50 units.
INFO sim_trace - 4.0000:demand_D1:Customer5:Demand at Distributor 1, Order quantity:10 received. Current inv: 100
INFO sim_trace - 4.0000:D1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 4.0000:M1: Inventory levels:50
INFO sim_trace - 4.0000:M1:Replenishing raw material:Raw Material 1 from supplier:S1, order placed for 750 units. Current inventory level: {'RM1': 210}.
INFO sim_trace - 4.0000:M1:shipment in transit from supplier:Supplier 1.
INFO sim_trace - 5.0000:demand_D1:Customer6:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 5.0000:D1: Inventory levels:90
INFO sim_trace - 5.0000:demand_D1:Customer6:Demand at Distributor 1, Order quantity:10 received. Current inv: 90
INFO sim_trace - 6.0000:M1: 30 units manufactured.
INFO sim_trace - 6.0000:M1: Product inventory levels:80
INFO sim_trace - 6.0000:D1:Inventory replenished. reorder_quantity=50, Inventory levels:140
INFO sim_trace - 6.0000:demand_D1:Customer7:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 6.0000:D1: Inventory levels:130
INFO sim_trace - 6.0000:demand_D1:Customer7:Demand at Distributor 1, Order quantity:10 received. Current inv: 130
INFO sim_trace - 7.0000:M1:Order received from supplier:Supplier 1, inventory levels: {'RM1': 870}
INFO sim_trace - 7.0000:demand_D1:Customer8:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 7.0000:D1: Inventory levels:120
INFO sim_trace - 7.0000:demand_D1:Customer8:Demand at Distributor 1, Order quantity:10 received. Current inv: 120
INFO sim_trace - 8.0000:demand_D1:Customer9:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 8.0000:D1: Inventory levels:110
INFO sim_trace - 8.0000:demand_D1:Customer9:Demand at Distributor 1, Order quantity:10 received. Current inv: 110
INFO sim_trace - 9.0000:M1: 30 units manufactured.
INFO sim_trace - 9.0000:M1: Product inventory levels:110
INFO sim_trace - 9.0000:demand_D1:Customer10:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 9.0000:D1: Inventory levels:100
INFO sim_trace - 9.0000:D1:Replenishing inventory from supplier:Manufacturer 1, order placed for 50 units.
INFO sim_trace - 9.0000:demand_D1:Customer10:Demand at Distributor 1, Order quantity:10 received. Current inv: 100
INFO sim_trace - 9.0000:D1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 9.0000:M1: Inventory levels:60
INFO sim_trace - 9.0000:M1:Sufficient raw material inventory for Raw Material 1, no order placed. Current inventory level: {'RM1': 780}.
INFO sim_trace - 10.0000:demand_D1:Customer11:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 10.0000:D1: Inventory levels:90
INFO sim_trace - 10.0000:demand_D1:Customer11:Demand at Distributor 1, Order quantity:10 received. Current inv: 90
INFO sim_trace - 11.0000:D1:Inventory replenished. reorder_quantity=50, Inventory levels:140
INFO sim_trace - 11.0000:demand_D1:Customer12:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 11.0000:D1: Inventory levels:130
INFO sim_trace - 11.0000:demand_D1:Customer12:Demand at Distributor 1, Order quantity:10 received. Current inv: 130
INFO sim_trace - 12.0000:M1: 30 units manufactured.
INFO sim_trace - 12.0000:M1: Product inventory levels:90
INFO sim_trace - 12.0000:demand_D1:Customer13:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 12.0000:D1: Inventory levels:120
INFO sim_trace - 12.0000:demand_D1:Customer13:Demand at Distributor 1, Order quantity:10 received. Current inv: 120
INFO sim_trace - 13.0000:demand_D1:Customer14:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 13.0000:D1: Inventory levels:110
INFO sim_trace - 13.0000:demand_D1:Customer14:Demand at Distributor 1, Order quantity:10 received. Current inv: 110
INFO sim_trace - 14.0000:demand_D1:Customer15:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 14.0000:D1: Inventory levels:100
INFO sim_trace - 14.0000:D1:Replenishing inventory from supplier:Manufacturer 1, order placed for 50 units.
INFO sim_trace - 14.0000:demand_D1:Customer15:Demand at Distributor 1, Order quantity:10 received. Current inv: 100
INFO sim_trace - 14.0000:D1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 14.0000:M1: Inventory levels:40
INFO sim_trace - 14.0000:M1:Replenishing raw material:Raw Material 1 from supplier:S1, order placed for 780 units. Current inventory level: {'RM1': 690}.
INFO sim_trace - 14.0000:M1:shipment in transit from supplier:Supplier 1.
INFO sim_trace - 15.0000:M1: 30 units manufactured.
INFO sim_trace - 15.0000:M1: Product inventory levels:70
INFO sim_trace - 15.0000:demand_D1:Customer16:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 15.0000:D1: Inventory levels:90
INFO sim_trace - 15.0000:demand_D1:Customer16:Demand at Distributor 1, Order quantity:10 received. Current inv: 90
INFO sim_trace - 16.0000:D1:Inventory replenished. reorder_quantity=50, Inventory levels:140
INFO sim_trace - 16.0000:demand_D1:Customer17:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 16.0000:D1: Inventory levels:130
INFO sim_trace - 16.0000:demand_D1:Customer17:Demand at Distributor 1, Order quantity:10 received. Current inv: 130
INFO sim_trace - 17.0000:M1:Order received from supplier:Supplier 1, inventory levels: {'RM1': 1380}
INFO sim_trace - 17.0000:demand_D1:Customer18:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 17.0000:D1: Inventory levels:120
INFO sim_trace - 17.0000:demand_D1:Customer18:Demand at Distributor 1, Order quantity:10 received. Current inv: 120
INFO sim_trace - 18.0000:M1: 30 units manufactured.
INFO sim_trace - 18.0000:M1: Product inventory levels:100
INFO sim_trace - 18.0000:demand_D1:Customer19:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 18.0000:D1: Inventory levels:110
INFO sim_trace - 18.0000:demand_D1:Customer19:Demand at Distributor 1, Order quantity:10 received. Current inv: 110
INFO sim_trace - 19.0000:demand_D1:Customer20:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 19.0000:D1: Inventory levels:100
INFO sim_trace - 19.0000:D1:Replenishing inventory from supplier:Manufacturer 1, order placed for 50 units.
INFO sim_trace - 19.0000:demand_D1:Customer20:Demand at Distributor 1, Order quantity:10 received. Current inv: 100
INFO sim_trace - 19.0000:D1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 19.0000:M1: Inventory levels:50
INFO sim_trace - 19.0000:M1:Sufficient raw material inventory for Raw Material 1, no order placed. Current inventory level: {'RM1': 1290}.
INFO sim_trace - 20.0000:demand_D1:Customer21:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 20.0000:D1: Inventory levels:90
INFO sim_trace - 20.0000:demand_D1:Customer21:Demand at Distributor 1, Order quantity:10 received. Current inv: 90
INFO sim_trace - 21.0000:M1: 30 units manufactured.
INFO sim_trace - 21.0000:M1: Product inventory levels:80
INFO sim_trace - 21.0000:D1:Inventory replenished. reorder_quantity=50, Inventory levels:140
INFO sim_trace - 21.0000:demand_D1:Customer22:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 21.0000:D1: Inventory levels:130
INFO sim_trace - 21.0000:demand_D1:Customer22:Demand at Distributor 1, Order quantity:10 received. Current inv: 130
INFO sim_trace - 22.0000:demand_D1:Customer23:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 22.0000:D1: Inventory levels:120
INFO sim_trace - 22.0000:demand_D1:Customer23:Demand at Distributor 1, Order quantity:10 received. Current inv: 120
INFO sim_trace - 23.0000:demand_D1:Customer24:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 23.0000:D1: Inventory levels:110
INFO sim_trace - 23.0000:demand_D1:Customer24:Demand at Distributor 1, Order quantity:10 received. Current inv: 110
INFO sim_trace - 24.0000:M1: 30 units manufactured.
INFO sim_trace - 24.0000:M1: Product inventory levels:110
INFO sim_trace - 24.0000:demand_D1:Customer25:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 24.0000:D1: Inventory levels:100
INFO sim_trace - 24.0000:D1:Replenishing inventory from supplier:Manufacturer 1, order placed for 50 units.
INFO sim_trace - 24.0000:demand_D1:Customer25:Demand at Distributor 1, Order quantity:10 received. Current inv: 100
INFO sim_trace - 24.0000:D1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 24.0000:M1: Inventory levels:60
INFO sim_trace - 24.0000:M1:Sufficient raw material inventory for Raw Material 1, no order placed. Current inventory level: {'RM1': 1110}.
INFO sim_trace - 25.0000:demand_D1:Customer26:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 25.0000:D1: Inventory levels:90
INFO sim_trace - 25.0000:demand_D1:Customer26:Demand at Distributor 1, Order quantity:10 received. Current inv: 90
INFO sim_trace - 26.0000:D1:Inventory replenished. reorder_quantity=50, Inventory levels:140
INFO sim_trace - 26.0000:demand_D1:Customer27:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 26.0000:D1: Inventory levels:130
INFO sim_trace - 26.0000:demand_D1:Customer27:Demand at Distributor 1, Order quantity:10 received. Current inv: 130
INFO sim_trace - 27.0000:M1: 30 units manufactured.
INFO sim_trace - 27.0000:M1: Product inventory levels:90
INFO sim_trace - 27.0000:demand_D1:Customer28:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 27.0000:D1: Inventory levels:120
INFO sim_trace - 27.0000:demand_D1:Customer28:Demand at Distributor 1, Order quantity:10 received. Current inv: 120
INFO sim_trace - 28.0000:demand_D1:Customer29:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 28.0000:D1: Inventory levels:110
INFO sim_trace - 28.0000:demand_D1:Customer29:Demand at Distributor 1, Order quantity:10 received. Current inv: 110
INFO sim_trace - 29.0000:demand_D1:Customer30:Demand at Distributor 1, Order quantity:10, available.
INFO sim_trace - 29.0000:D1: Inventory levels:100
INFO sim_trace - 29.0000:D1:Replenishing inventory from supplier:Manufacturer 1, order placed for 50 units.
INFO sim_trace - 29.0000:demand_D1:Customer30:Demand at Distributor 1, Order quantity:10 received. Current inv: 100
INFO sim_trace - 29.0000:D1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 29.0000:M1: Inventory levels:40
INFO sim_trace - 29.0000:M1:Sufficient raw material inventory for Raw Material 1, no order placed. Current inventory level: {'RM1': 1020}.
Performance Metrics:
Total Available Inventory: 140
Average Available Inventory: 201.33333333333331
Total Inventory Carry Cost: 4745.0
Total Inventory Spend: 36830
Total Transport Cost: 50
Total Revenue: 31500
Total Cost: 51790.0
Total Profit: -20290.0
Total Demand Placed by Customers: [30, 300]
Total Fulfillment Received by Customers: [30, 300]
Total Demand Placed by Site: [10, 2230]
Total Fulfillment Received by Site: [9, 2180]
Total Demand Placed: [40, 2530]
Total Fulfillment Received: [39, 2480]
Average Cost per Order: 1294.75
Average Cost per Item: 20.470355731225297
```
</div>

---

## Alternative Approach: Using Object-Oriented API

This approach demonstrates how to build and simulate a supply chain using SupplyNetPy's object-oriented API. Instead of passing dictionaries to utility functions, you instantiate supply chain components as Python objects, providing greater flexibility and extensibility. Each node and link is created as an object, and the simulation is managed within a SimPy environment, allowing for more advanced customization and integration with other SimPy-based processes.

```python
import SupplyNetPy.Components as scm
import simpy
simtime = 31
env = simpy.Environment() # create a simpy environment

supplier = scm.Supplier(env=env, ID='S1', name='Supplier', node_type="infinite_supplier") # create an infinite supplier

factory = scm.Manufacturer(env=env, ID='F1', name='factory 1', capacity=1000, initial_level=1000, inventory_holding_cost=0.1,
                           replenishment_policy=scm.RQReplenishment, policy_param={'R':500, 'Q':200},
                           product_buy_price=150, product_sell_price=300)


distributor1 = scm.InventoryNode(env=env, ID='D1', name='Distribution Center 1', node_type="distributor",
                                capacity=500, initial_level=500, inventory_holding_cost=0.22,
                                replenishment_policy = scm.SSReplenishment, policy_param={'s':300, 'S':200},
                                product_buy_price=150, product_sell_price=300)

link1 = scm.Link(env=env, ID='L1', source=supplier, sink=distributor1, cost=10, lead_time=lambda: 1)
link2 = scm.Link(env=env, ID='L2', source=supplier, sink=factory, cost=10, lead_time=lambda: 1)



demand = scm.Demand(env=env, ID='demand_D1', name='Demand at Distributor',
                    order_arrival_model=lambda: 1, order_quantity_model=lambda:10,
                    delivery_cost=lambda:10, lead_time=lambda: 1, demand_node=distributor1)

inventory_nodes = [supplier, factory, distributor1]
inventory_links = [link1, link2]
demand_nodes = [demand]
env.run(until=simtime)
supplynet = scm.create_sc_net(nodes = inventory_nodes, links = inventory_links, demands = demand_nodes)
supplynet = scm.simulate_sc_net(supplynet, sim_time=simtime)
```

After running the simulation, the simulation log will be printed to the screen, just as with the functional API. However, to view a summary of the supply chain's performance (such as inventory costs, transportation costs and profits), you need to call the `get_statistics()` method on each node object. For example:

```python
print(manufacturer.get_statistics())
print(distributor.get_statistics())
print(supplier.get_statistics())
```

This will display detailed performance metrics for each node in the supply chain.

This is to include a Python file directly.
