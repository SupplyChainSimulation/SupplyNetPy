# SupplyNetPy Examples

## A simple six node supply chain

Let's create a supply chain network for a single product inventory with six nodes, a supplier, a manufacturer, adistributor and three retailer. The retailer has the option to replenish its inventory by obtaining products from the distributor. Meanwhile, the manufacturer can restock its own inventory by sourcing raw materials from the supplier to produce the goods.

~~~Python
# let us import the library
import SupplyNetPy.Components as scm
~~~
# Create a supply chain
~~~Python
# create supply chain nodes
supplier1 = scm.Supplier(ID="S1", name="Supplier 1",
                         capacity=500, initial_level=500, inventory_holding_cost=0.3)

manufacturer1 = scm.Manufacturer(ID="M1", name="Manufacturer 1",
                                 capacity=500, initial_level=300, inventoty_holding_cost=3,
                                 replenishment_policy="sS", policy_param=[200])

distributor1 = scm.InventoryNode(ID="D1", name="Distributor 1", node_type="distributor",
                                 capacity=300, initial_level=100, inventory_holding_cost=3,
                                 replenishment_policy="sS", policy_param=[50])

retailer1 = scm.InventoryNode(ID="R1", name="Retailer 1", node_type="retailer",
                              capacity=100, initial_level=50, inventory_holding_cost=3,
                              replenishment_policy="sS", policy_param=[50])

retailer2 = scm.InventoryNode(ID="R1", name="Retailer 1", node_type="retailer",
                              capacity=100, initial_level=50, inventory_holding_cost=3,
                              replenishment_policy="sS", policy_param=[50])

retailer3 = scm.InventoryNode(ID="R1", name="Retailer 1", node_type="retailer",
                              capacity=100, initial_level=50, inventory_holding_cost=3,
                              replenishment_policy="sS", policy_param=[50])
~~~

[sS]: ## "Reorder level-based inventory replenishment policy: In this approach, inventory levels are continuously monitored. When inventory levels drop below a certain threshold 's', an order is placed to restock it to its full capacity 'S'."
~~~Python
# Create links between the nodes
link_sup1_man1 = scm.Link(ID="L1", source=supplier1, sink=manufacturer1, cost=5, lead_time=3)
link_man1_dis1 = scm.Link(ID="L2", source=manufacturer1, sink=distributor1, cost=50, lead_time=2)
link_dis1_ret1 = scm.Link(ID="L3", source=distributor1, sink=retailer1, cost=50, lead_time=4)
link_dis1_ret2 = scm.Link(ID="L4", source=distributor1, sink=retailer2, cost=50, lead_time=4)
link_dis1_ret3 = scm.Link(ID="L5", source=distributor1, sink=retailer3, cost=50, lead_time=4)
~~~
To stimulate product movement within our network, we need to generate demand. Traditionally, retailers are the main points of contact for real customer demand. However, we can also create demand directly at the manufacturer node. Imagine a scenario in which a manufacturer not only supplies products to retailers but also directly responds to customer orders for personalized items. For example, consider the manufacturing of custom-designed T-shirts for a university baseball team. We use the `Demand` class from SupplyNetPy to generate deamnd at a particular node. Demand takes the order arrival and quantity models as callable functions. These can be a constant number of distribution generation functions to model order arrival and quantity.
~~~Python
# Create a demand
demand_r1 = scm.Demand(ID="demand_R1", name="Demand 1", order_arrival_model=lambda: 5,
                       order_quantity_model=lambda: 5, demand_node=retailer1)

demand_r2 = scm.Demand(ID="demand_R2", name="Demand 2", order_arrival_model=lambda: 3,
                       order_quantity_model=lambda: 7, demand_node=retailer2)

demand_r3 = scm.Demand(ID="demand_R3", name="Demand 3", order_arrival_model=lambda: 1,
                       order_quantity_model=lambda: 9, demand_node=retailer3)
~~~

Let us leverage SupplyNetPy's create_sc and simulate_sc_net functions to assemble the supply chain components we created above in a single network and simulate it. 

~~~Python
scnet = scm.create_sc_net(nodes=[supplier1, manufacturer1, distributor1, retailer1, retailer2, retailer3],
                          links=[link_sup1_man1, link_man1_dis1, link_dis1_ret1, link_dis1_ret2, link_dis1_ret3],
                          demands=[demand_r1, demand_r2, demand_r3])

# Simulate the supply chain network
scm.simulate_sc_net(scnet, sim_time=100)
~~~

### Code output

Below is the simulation log printed on the console by running the above code snippet.
<div style="overflow-y: auto; padding: 0px; max-height: 500px;">
```bash
INFO sim_trace - 0:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:45.
INFO sim_trace - 0:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:43.
INFO sim_trace - 0:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:41.
INFO sim_trace - 1:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 55 units.
INFO sim_trace - 1:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 57 units.
INFO sim_trace - 1:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 59 units.
INFO sim_trace - 1:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:32.
INFO sim_trace - 1:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 1:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 1:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 2:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:23.
INFO sim_trace - 3:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:36.
INFO sim_trace - 3:R1:Inventory replenished. Inventory levels:100
INFO sim_trace - 3:R1:Inventory replenished. Inventory levels:93
INFO sim_trace - 3:R1:Inventory replenished. Inventory levels:82
INFO sim_trace - 3:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:73.
INFO sim_trace - 4:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:64.
INFO sim_trace - 5:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:95.
INFO sim_trace - 5:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:55.
INFO sim_trace - 6:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:86.
INFO sim_trace - 6:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:46.
INFO sim_trace - 7:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 54 units.
INFO sim_trace - 7:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:37.
INFO sim_trace - 7:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 8:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:28.
INFO sim_trace - 9:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:79.
INFO sim_trace - 9:R1:Inventory replenished. Inventory levels:82
INFO sim_trace - 9:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:73.
INFO sim_trace - 10:M1:Product manufactured.
INFO sim_trace - 10:M1: Raw material inventory levels:{'RM1': 291.0}
INFO sim_trace - 10:M1: Product inventory levels:105
INFO sim_trace - 10:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:90.
INFO sim_trace - 10:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:64.
INFO sim_trace - 11:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:55.
INFO sim_trace - 12:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:72.
INFO sim_trace - 12:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:46.
INFO sim_trace - 13:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 54 units.
INFO sim_trace - 13:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:37.
INFO sim_trace - 13:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 14:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:28.
INFO sim_trace - 15:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:85.
INFO sim_trace - 15:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:65.
INFO sim_trace - 15:R1:Inventory replenished. Inventory levels:82
INFO sim_trace - 15:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:73.
INFO sim_trace - 16:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:64.
INFO sim_trace - 17:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:55.
INFO sim_trace - 18:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:58.
INFO sim_trace - 18:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:46.
INFO sim_trace - 19:R1:Replenishing inventory from supplier:Distributor 1, order placed for 54 units.
INFO sim_trace - 19:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:37.
INFO sim_trace - 19:R1:shipment in transit from supplier:Distributor 1.
INFO sim_trace - 20:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:80.
INFO sim_trace - 20:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 20:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:28.
INFO sim_trace - 21:M1:Product manufactured.
INFO sim_trace - 21:M1: Raw material inventory levels:{'RM1': 282.0}
INFO sim_trace - 21:M1: Product inventory levels:81
INFO sim_trace - 21:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:51.
INFO sim_trace - 21:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 21:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:19.
INFO sim_trace - 22:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 22:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:10.
INFO sim_trace - 23:R1:Inventory replenished. Inventory levels:64
INFO sim_trace - 23:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 23:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:55.
INFO sim_trace - 24:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:44.
INFO sim_trace - 24:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 24:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 56 units.
INFO sim_trace - 24:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:46.
INFO sim_trace - 24:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 25:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:75.
INFO sim_trace - 25:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 25:R1:Product not available at suppliers. Required quantity:54.
INFO sim_trace - 25:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:37.
INFO sim_trace - 26:R1:Inventory replenished. Inventory levels:100
INFO sim_trace - 26:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 26:R1:Product not available at suppliers. Required quantity:63.
INFO sim_trace - 26:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:28.
INFO sim_trace - 27:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:93.
INFO sim_trace - 27:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 27:R1:Product not available at suppliers. Required quantity:72.
INFO sim_trace - 27:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:19.
INFO sim_trace - 28:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 28:R1:Product not available at suppliers. Required quantity:81.
INFO sim_trace - 28:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:10.
INFO sim_trace - 29:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 29:R1:Product not available at suppliers. Required quantity:90.
INFO sim_trace - 29:demand_R3:Demand at Retailer 1, Order quantity:9 received, inventory level:1.
INFO sim_trace - 30:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:70.
INFO sim_trace - 30:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:86.
INFO sim_trace - 30:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 30:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 30:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 31:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 31:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 31:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 32:M1:Product manufactured.
INFO sim_trace - 32:M1: Raw material inventory levels:{'RM1': 273.0}
INFO sim_trace - 32:M1: Product inventory levels:55
INFO sim_trace - 32:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 32:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 32:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 33:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:79.
INFO sim_trace - 33:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 33:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 33:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 34:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 34:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 34:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 35:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:65.
INFO sim_trace - 35:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 35:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 35:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 36:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:72.
INFO sim_trace - 36:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 36:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 36:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 37:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 37:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 37:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 38:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 38:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 38:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 39:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:65.
INFO sim_trace - 39:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 39:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 39:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 40:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:60.
INFO sim_trace - 40:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 40:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 40:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 41:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 41:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 41:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 42:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:58.
INFO sim_trace - 42:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 42:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 42:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 43:M1:Product manufactured.
INFO sim_trace - 43:M1: Raw material inventory levels:{'RM1': 264.0}
INFO sim_trace - 43:M1: Product inventory levels:85
INFO sim_trace - 43:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 43:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 43:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 44:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 44:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 44:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 45:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:55.
INFO sim_trace - 45:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:51.
INFO sim_trace - 45:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 45:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 45:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 46:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 46:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 46:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 47:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 47:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 47:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 48:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:44.
INFO sim_trace - 48:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 48:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 56 units.
INFO sim_trace - 48:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 48:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 48:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 49:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 49:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 49:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 50:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:50.
INFO sim_trace - 50:R1:Inventory replenished. Inventory levels:100
INFO sim_trace - 50:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 50:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 50:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 51:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:93.
INFO sim_trace - 51:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 51:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 51:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 52:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 52:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 52:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 53:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 53:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 53:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 54:M1:Product manufactured.
INFO sim_trace - 54:M1: Raw material inventory levels:{'RM1': 255.0}
INFO sim_trace - 54:M1: Product inventory levels:59
INFO sim_trace - 54:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:86.
INFO sim_trace - 54:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 54:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 54:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 55:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:45.
INFO sim_trace - 55:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 55:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 55 units.
INFO sim_trace - 55:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 55:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 55:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 56:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 56:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 56:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 57:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:79.
INFO sim_trace - 57:R1:Inventory replenished. Inventory levels:100
INFO sim_trace - 57:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 57:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 57:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 58:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 58:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 58:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 59:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 59:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 59:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 60:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:95.
INFO sim_trace - 60:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:72.
INFO sim_trace - 60:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 60:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 60:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 61:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 61:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 61:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 62:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 62:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 62:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 63:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:65.
INFO sim_trace - 63:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 63:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 63:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 64:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 64:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 64:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 65:M1:Product manufactured.
INFO sim_trace - 65:M1: Raw material inventory levels:{'RM1': 246.0}
INFO sim_trace - 65:M1: Product inventory levels:34
INFO sim_trace - 65:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:90.
INFO sim_trace - 65:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 65:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 65:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 66:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:58.
INFO sim_trace - 66:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 66:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 66:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 67:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 67:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 67:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 68:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 68:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 68:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 69:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:51.
INFO sim_trace - 69:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 69:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 69:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 70:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:85.
INFO sim_trace - 70:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 70:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 70:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 71:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 71:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 71:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 72:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:44.
INFO sim_trace - 72:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 72:R1:Product not available at suppliers. Required quantity:56.
INFO sim_trace - 72:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 72:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 73:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 73:R1:Product not available at suppliers. Required quantity:56.
INFO sim_trace - 73:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 73:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 74:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 74:R1:Product not available at suppliers. Required quantity:56.
INFO sim_trace - 74:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 74:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 75:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:80.
INFO sim_trace - 75:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:37.
INFO sim_trace - 75:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 75:R1:Product not available at suppliers. Required quantity:63.
INFO sim_trace - 75:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 75:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 76:M1:Product manufactured.
INFO sim_trace - 76:M1: Raw material inventory levels:{'RM1': 237.0}
INFO sim_trace - 76:M1: Product inventory levels:64
INFO sim_trace - 76:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 76:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 63 units.
INFO sim_trace - 76:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 76:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 76:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - 77:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 77:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 77:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 78:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:30.
INFO sim_trace - 78:R1:Inventory replenished. Inventory levels:93
INFO sim_trace - 78:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 78:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 78:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 79:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 79:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 79:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 80:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:75.
INFO sim_trace - 80:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 80:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 80:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 81:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:86.
INFO sim_trace - 81:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 81:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 81:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 82:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 82:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 82:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 83:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 83:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 83:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 84:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:79.
INFO sim_trace - 84:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 84:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 84:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 85:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:70.
INFO sim_trace - 85:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 85:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 85:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 86:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 86:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 86:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 87:M1:Product manufactured.
INFO sim_trace - 87:M1: Raw material inventory levels:{'RM1': 228.0}
INFO sim_trace - 87:M1: Product inventory levels:31
INFO sim_trace - 87:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:72.
INFO sim_trace - 87:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 87:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 87:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 88:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 88:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 88:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 89:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 89:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 89:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 90:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:65.
INFO sim_trace - 90:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:65.
INFO sim_trace - 90:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 90:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 90:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 91:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 91:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 91:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 92:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 92:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 92:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 93:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:58.
INFO sim_trace - 93:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 93:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 93:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 94:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 94:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 94:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 95:demand_R1:Demand at Retailer 1, Order quantity:5 received, inventory level:60.
INFO sim_trace - 95:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 95:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 95:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 96:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:51.
INFO sim_trace - 96:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 96:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 96:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 97:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 97:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 97:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 98:M1:Product manufactured.
INFO sim_trace - 98:M1: Raw material inventory levels:{'RM1': 219.0}
INFO sim_trace - 98:M1: Product inventory levels:61
INFO sim_trace - 98:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 98:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 98:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 99:demand_R2:Demand at Retailer 1, Order quantity:7 received, inventory level:44.
INFO sim_trace - 99:D1:Product not available at suppliers. Required quantity:254.
INFO sim_trace - 99:R1:Replenishing inventory from supplier:Manufacturer 1, order placed for 56 units.
INFO sim_trace - 99:R1:Product not available at suppliers. Required quantity:99.
INFO sim_trace - 99:demand_R3:Demand at Retailer 1, Order quantity:9 not available, inventory level:1.
INFO sim_trace - 99:R1:shipment in transit from supplier:Manufacturer 1.
INFO sim_trace - *** Supply chain statistics ***
INFO sim_trace - Number of products sold = 608
INFO sim_trace - SC total profit = -47217.2
INFO sim_trace - SC total tranportation cost = 550
INFO sim_trace - SC total cost = 120731.0
INFO sim_trace - SC inventory cost = 93231.0
INFO sim_trace - Customers returned  = 630
```
</div>