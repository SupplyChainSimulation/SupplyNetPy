# SupplyNetPy Examples

## A simple six node supply chain

Let's create a supply chain network for a single product inventory with six nodes, a supplier, a manufacturer, a distributor and three retailer. The retailer has the option to replenish its inventory by obtaining products from the distributor. Meanwhile, the manufacturer can restock its own inventory by sourcing raw materials from the supplier to produce the goods. In this example we create a supplier with infinite supply of raw material. Let us import the library for modeling a supply chain.

~~~Python
# let us import the library
import SupplyNetPy.Components as scm
~~~
### Create a supply chain

To create a supply chain node, we must define the node and its parameter values in a Python dictionary. Below, we create multiple nodes of different types in a single list called nodes. 

#### Creating Nodes
~~~Python
# Defining supply chain nodes

# The following configurable parameters are mandatory to define a supply chain node: 
# ID, name, node_type, capacity, initial_level, inventory_holding_cost,
# replenishment_policy, policy_parameters

nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier'},

         {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer',
          'capacity': 300, 'initial_level': 200, 'inventory_holding_cost': 0.5,
          'replenishment_policy': 'sS', 'policy_param': [150],'product_sell_price': 310},
            
         {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor',
          'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 1,
          'replenishment_policy': 'sS', 'policy_param': [40],'product_sell_price': 320},

         {'ID': 'R1', 'name': 'Retailer 1', 'node_type': 'retailer',
          'capacity': 100, 'initial_level': 50, 'inventory_holding_cost': 3,
          'replenishment_policy': 'sS', 'policy_param': [50],'product_sell_price': 330},

         {'ID': 'R2', 'name': 'Retailer 2', 'node_type': 'retailer',
          'capacity': 100, 'initial_level': 50, 'inventory_holding_cost': 3,
          'replenishment_policy': 'sS', 'policy_param': [50],'product_sell_price': 335},

         {'ID': 'R3', 'name': 'Retailer 3', 'node_type': 'retailer',
          'capacity': 100, 'initial_level': 50, 'inventory_holding_cost': 3,
          'replenishment_policy': 'sS', 'policy_param': [50],'product_sell_price': 325}
        ]
~~~

[sS]: ## "Reorder level-based inventory replenishment policy: In this approach, inventory levels are continuously monitored. When inventory levels drop below a certain threshold 's', an order is placed to restock it to its full capacity 'S'."

[sS replenishment policy][sS]

#### Creating Links
~~~Python
# defining links between the nodes. 
# Mandatory link parameters: ID, from_node, to_node, transportation_cost, lead_time
links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': lambda: 3},
         {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2},
         {'ID': 'L3', 'source': 'D1', 'sink': 'R1', 'cost': 5, 'lead_time': lambda: 2},
         {'ID': 'L4', 'source': 'D1', 'sink': 'R2', 'cost': 5, 'lead_time': lambda: 2},
         {'ID': 'L5', 'source': 'D1', 'sink': 'R3', 'cost': 5, 'lead_time': lambda: 2}
        ]
~~~
To stimulate product movement within our network, we need to generate demand. Traditionally, retailers are the main points of contact for real customer demand. However, we can also create demand directly at the manufacturer node. Imagine a scenario in which a manufacturer not only supplies products to retailers but also directly responds to customer orders for personalized items. For example, consider the manufacturing of custom-designed T-shirts for a university baseball team. We use the `Demand` class from SupplyNetPy to generate deamnd at a particular node. Demand takes the order arrival and quantity models as callable functions. These can be a constant number or distribution generation functions to model order arrival and quantity. In this example we create a deterministic demand.

#### Creating Demand
~~~Python
# Create a demand
# ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
demands = [{'ID': 'demand_R1', 'name': 'Demand 1', 'node_type': 'demand', 
           'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10, 'demand_node': 'R1'},

           {'ID': 'demand_R2', 'name': 'Demand 2', 'node_type': 'demand', 
           'order_arrival_model': lambda: 2, 'order_quantity_model': lambda: 20, 'demand_node': 'R2'},

           {'ID': 'demand_R3', 'name': 'Demand 3', 'node_type': 'demand',
           'order_arrival_model': lambda: 3, 'order_quantity_model': lambda: 15, 'demand_node': 'R3'}
          ]
~~~

Let us leverage SupplyNetPy's `create_sc` and `simulate_sc_net` functions create instances for supply chain components we defined above and assemble them as a supply chain network and simulate it. 

### Running simulations
~~~Python
scm.global_logger.enable_logging()
supplychainnet = scm.simulate_sc_net(scm.create_sc_net(nodes, links, demands), sim_time=30)
~~~

### Code output

Below is the simulation log printed on the console by running the above code snippet.
<div style="overflow-y: auto; padding: 0px; max-height: 500px;">
```bash
INFO sim_trace - 0:demand_R1:Demand at Retailer 1, Order quantity:10 received, inventory level:40.
INFO sim_trace - 0:demand_R2:Demand at Retailer 2, Order quantity:20 received, inventory level:30.
INFO sim_trace - 0:demand_R3:Demand at Retailer 3, Order quantity:15 received, inventory level:35.
INFO sim_trace - 1:M1: Raw materials not available.
INFO sim_trace - 1:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 1:D1: Inventory levels:50
INFO sim_trace - 1:R1:Product not available at suppliers. Required quantity:60.
INFO sim_trace - 1:R1: Inventory levels:40
INFO sim_trace - 1:R2:Product not available at suppliers. Required quantity:70.
INFO sim_trace - 1:R2: Inventory levels:30
INFO sim_trace - 1:R3:Product not available at suppliers. Required quantity:65.
INFO sim_trace - 1:R3: Inventory levels:35
INFO sim_trace - 1:demand_R1:Demand at Retailer 1, Order quantity:10 received, inventory level:30.
INFO sim_trace - 2:demand_R2:Demand at Retailer 2, Order quantity:20 received, inventory level:10.
INFO sim_trace - 2:M1: Raw materials not available.
INFO sim_trace - 2:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 2:D1: Inventory levels:50
INFO sim_trace - 2:R1:Product not available at suppliers. Required quantity:70.
INFO sim_trace - 2:R1: Inventory levels:30
INFO sim_trace - 2:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 2:R2: Inventory levels:10
INFO sim_trace - 2:R3:Product not available at suppliers. Required quantity:65.
INFO sim_trace - 2:R3: Inventory levels:35
INFO sim_trace - 2:demand_R1:Demand at Retailer 1, Order quantity:10 received, inventory level:20.
INFO sim_trace - 3:demand_R3:Demand at Retailer 3, Order quantity:15 received, inventory level:20.
INFO sim_trace - 3:M1: Raw materials not available.
INFO sim_trace - 3:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 3:D1: Inventory levels:50
INFO sim_trace - 3:R1:Product not available at suppliers. Required quantity:80.
INFO sim_trace - 3:R1: Inventory levels:20
INFO sim_trace - 3:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 3:R2: Inventory levels:10
INFO sim_trace - 3:R3:Product not available at suppliers. Required quantity:80.
INFO sim_trace - 3:R3: Inventory levels:20
INFO sim_trace - 3:demand_R1:Demand at Retailer 1, Order quantity:10 received, inventory level:10.
INFO sim_trace - 4:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 4:M1: Raw materials not available.
INFO sim_trace - 4:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 4:D1: Inventory levels:50
INFO sim_trace - 4:R1:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 4:R1: Inventory levels:10
INFO sim_trace - 4:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 4:R2: Inventory levels:10
INFO sim_trace - 4:R3:Product not available at suppliers. Required quantity:80.
INFO sim_trace - 4:R3: Inventory levels:20
INFO sim_trace - 4:demand_R1:Demand at Retailer 1, Order quantity:10 received, inventory level:0.
INFO sim_trace - 5:M1: Raw materials not available.
INFO sim_trace - 5:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 5:D1: Inventory levels:50
INFO sim_trace - 5:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 5:R1: Inventory levels:0
INFO sim_trace - 5:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 5:R2: Inventory levels:10
INFO sim_trace - 5:R3:Product not available at suppliers. Required quantity:80.
INFO sim_trace - 5:R3: Inventory levels:20
INFO sim_trace - 5:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 6:demand_R3:Demand at Retailer 3, Order quantity:15 received, inventory level:5.
INFO sim_trace - 6:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 6:M1: Raw materials not available.
INFO sim_trace - 6:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 6:D1: Inventory levels:50
INFO sim_trace - 6:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 6:R1: Inventory levels:0
INFO sim_trace - 6:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 6:R2: Inventory levels:10
INFO sim_trace - 6:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 6:R3: Inventory levels:5
INFO sim_trace - 6:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 7:M1: Raw materials not available.
INFO sim_trace - 7:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 7:D1: Inventory levels:50
INFO sim_trace - 7:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 7:R1: Inventory levels:0
INFO sim_trace - 7:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 7:R2: Inventory levels:10
INFO sim_trace - 7:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 7:R3: Inventory levels:5
INFO sim_trace - 7:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 8:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 8:M1: Raw materials not available.
INFO sim_trace - 8:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 8:D1: Inventory levels:50
INFO sim_trace - 8:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 8:R1: Inventory levels:0
INFO sim_trace - 8:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 8:R2: Inventory levels:10
INFO sim_trace - 8:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 8:R3: Inventory levels:5
INFO sim_trace - 8:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 9:demand_R3:Demand at Retailer 3, Order quantity:15 not available, inventory level:5.
INFO sim_trace - 9:M1: Raw materials not available.
INFO sim_trace - 9:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 9:D1: Inventory levels:50
INFO sim_trace - 9:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 9:R1: Inventory levels:0
INFO sim_trace - 9:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 9:R2: Inventory levels:10
INFO sim_trace - 9:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 9:R3: Inventory levels:5
INFO sim_trace - 9:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 10:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 10:M1: Raw materials not available.
INFO sim_trace - 10:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 10:D1: Inventory levels:50
INFO sim_trace - 10:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 10:R1: Inventory levels:0
INFO sim_trace - 10:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 10:R2: Inventory levels:10
INFO sim_trace - 10:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 10:R3: Inventory levels:5
INFO sim_trace - 10:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 11:M1: Raw materials not available.
INFO sim_trace - 11:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 11:D1: Inventory levels:50
INFO sim_trace - 11:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 11:R1: Inventory levels:0
INFO sim_trace - 11:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 11:R2: Inventory levels:10
INFO sim_trace - 11:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 11:R3: Inventory levels:5
INFO sim_trace - 11:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 12:demand_R3:Demand at Retailer 3, Order quantity:15 not available, inventory level:5.
INFO sim_trace - 12:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 12:M1: Raw materials not available.
INFO sim_trace - 12:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 12:D1: Inventory levels:50
INFO sim_trace - 12:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 12:R1: Inventory levels:0
INFO sim_trace - 12:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 12:R2: Inventory levels:10
INFO sim_trace - 12:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 12:R3: Inventory levels:5
INFO sim_trace - 12:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 13:M1: Raw materials not available.
INFO sim_trace - 13:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 13:D1: Inventory levels:50
INFO sim_trace - 13:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 13:R1: Inventory levels:0
INFO sim_trace - 13:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 13:R2: Inventory levels:10
INFO sim_trace - 13:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 13:R3: Inventory levels:5
INFO sim_trace - 13:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 14:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 14:M1: Raw materials not available.
INFO sim_trace - 14:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 14:D1: Inventory levels:50
INFO sim_trace - 14:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 14:R1: Inventory levels:0
INFO sim_trace - 14:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 14:R2: Inventory levels:10
INFO sim_trace - 14:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 14:R3: Inventory levels:5
INFO sim_trace - 14:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 15:demand_R3:Demand at Retailer 3, Order quantity:15 not available, inventory level:5.
INFO sim_trace - 15:M1: Raw materials not available.
INFO sim_trace - 15:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 15:D1: Inventory levels:50
INFO sim_trace - 15:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 15:R1: Inventory levels:0
INFO sim_trace - 15:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 15:R2: Inventory levels:10
INFO sim_trace - 15:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 15:R3: Inventory levels:5
INFO sim_trace - 15:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 16:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 16:M1: Raw materials not available.
INFO sim_trace - 16:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 16:D1: Inventory levels:50
INFO sim_trace - 16:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 16:R1: Inventory levels:0
INFO sim_trace - 16:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 16:R2: Inventory levels:10
INFO sim_trace - 16:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 16:R3: Inventory levels:5
INFO sim_trace - 16:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 17:M1: Raw materials not available.
INFO sim_trace - 17:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 17:D1: Inventory levels:50
INFO sim_trace - 17:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 17:R1: Inventory levels:0
INFO sim_trace - 17:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 17:R2: Inventory levels:10
INFO sim_trace - 17:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 17:R3: Inventory levels:5
INFO sim_trace - 17:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 18:demand_R3:Demand at Retailer 3, Order quantity:15 not available, inventory level:5.
INFO sim_trace - 18:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 18:M1: Raw materials not available.
INFO sim_trace - 18:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 18:D1: Inventory levels:50
INFO sim_trace - 18:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 18:R1: Inventory levels:0
INFO sim_trace - 18:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 18:R2: Inventory levels:10
INFO sim_trace - 18:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 18:R3: Inventory levels:5
INFO sim_trace - 18:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 19:M1: Raw materials not available.
INFO sim_trace - 19:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 19:D1: Inventory levels:50
INFO sim_trace - 19:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 19:R1: Inventory levels:0
INFO sim_trace - 19:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 19:R2: Inventory levels:10
INFO sim_trace - 19:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 19:R3: Inventory levels:5
INFO sim_trace - 19:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 20:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 20:M1: Raw materials not available.
INFO sim_trace - 20:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 20:D1: Inventory levels:50
INFO sim_trace - 20:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 20:R1: Inventory levels:0
INFO sim_trace - 20:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 20:R2: Inventory levels:10
INFO sim_trace - 20:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 20:R3: Inventory levels:5
INFO sim_trace - 20:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 21:demand_R3:Demand at Retailer 3, Order quantity:15 not available, inventory level:5.
INFO sim_trace - 21:M1: Raw materials not available.
INFO sim_trace - 21:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 21:D1: Inventory levels:50
INFO sim_trace - 21:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 21:R1: Inventory levels:0
INFO sim_trace - 21:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 21:R2: Inventory levels:10
INFO sim_trace - 21:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 21:R3: Inventory levels:5
INFO sim_trace - 21:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 22:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 22:M1: Raw materials not available.
INFO sim_trace - 22:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 22:D1: Inventory levels:50
INFO sim_trace - 22:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 22:R1: Inventory levels:0
INFO sim_trace - 22:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 22:R2: Inventory levels:10
INFO sim_trace - 22:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 22:R3: Inventory levels:5
INFO sim_trace - 22:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 23:M1: Raw materials not available.
INFO sim_trace - 23:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 23:D1: Inventory levels:50
INFO sim_trace - 23:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 23:R1: Inventory levels:0
INFO sim_trace - 23:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 23:R2: Inventory levels:10
INFO sim_trace - 23:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 23:R3: Inventory levels:5
INFO sim_trace - 23:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 24:demand_R3:Demand at Retailer 3, Order quantity:15 not available, inventory level:5.
INFO sim_trace - 24:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 24:M1: Raw materials not available.
INFO sim_trace - 24:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 24:D1: Inventory levels:50
INFO sim_trace - 24:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 24:R1: Inventory levels:0
INFO sim_trace - 24:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 24:R2: Inventory levels:10
INFO sim_trace - 24:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 24:R3: Inventory levels:5
INFO sim_trace - 24:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 25:M1: Raw materials not available.
INFO sim_trace - 25:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 25:D1: Inventory levels:50
INFO sim_trace - 25:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 25:R1: Inventory levels:0
INFO sim_trace - 25:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 25:R2: Inventory levels:10
INFO sim_trace - 25:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 25:R3: Inventory levels:5
INFO sim_trace - 25:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 26:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 26:M1: Raw materials not available.
INFO sim_trace - 26:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 26:D1: Inventory levels:50
INFO sim_trace - 26:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 26:R1: Inventory levels:0
INFO sim_trace - 26:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 26:R2: Inventory levels:10
INFO sim_trace - 26:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 26:R3: Inventory levels:5
INFO sim_trace - 26:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 27:demand_R3:Demand at Retailer 3, Order quantity:15 not available, inventory level:5.
INFO sim_trace - 27:M1: Raw materials not available.
INFO sim_trace - 27:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 27:D1: Inventory levels:50
INFO sim_trace - 27:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 27:R1: Inventory levels:0
INFO sim_trace - 27:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 27:R2: Inventory levels:10
INFO sim_trace - 27:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 27:R3: Inventory levels:5
INFO sim_trace - 27:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 28:demand_R2:Demand at Retailer 2, Order quantity:20 not available, inventory level:10.
INFO sim_trace - 28:M1: Raw materials not available.
INFO sim_trace - 28:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 28:D1: Inventory levels:50
INFO sim_trace - 28:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 28:R1: Inventory levels:0
INFO sim_trace - 28:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 28:R2: Inventory levels:10
INFO sim_trace - 28:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 28:R3: Inventory levels:5
INFO sim_trace - 28:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace - 29:M1: Raw materials not available.
INFO sim_trace - 29:M1: Raw materials' inventory levels:{'RM1': 0}, Product inventory levels:200
INFO sim_trace - 29:D1: Inventory levels:50
INFO sim_trace - 29:R1:Product not available at suppliers. Required quantity:100.
INFO sim_trace - 29:R1: Inventory levels:0
INFO sim_trace - 29:R2:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 29:R2: Inventory levels:10
INFO sim_trace - 29:R3:Product not available at suppliers. Required quantity:95.
INFO sim_trace - 29:R3: Inventory levels:5
INFO sim_trace - 29:demand_R1:Demand at Retailer 1, Order quantity:10 not available, inventory level:0.
INFO sim_trace -
Supply chain performance:
INFO sim_trace - Number of products sold = 135
INFO sim_trace - SC total profit = -6242.25
INFO sim_trace - SC total tranportation cost = 0
INFO sim_trace - SC total cost = 6330.0
INFO sim_trace - SC inventory cost = 6330.0
INFO sim_trace - Unsatisfied demand  = 615
```
</div>