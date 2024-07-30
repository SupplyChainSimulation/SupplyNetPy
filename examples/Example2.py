# import the library
import SupplyNetPy.Components as scm
# Create a supply chain nodes
supplier1 = scm.Supplier(ID="S1", name="Supplier 1", capacity=500, initial_level=500, inventory_holding_cost=0.3)
manufacturer1 = scm.Manufacturer(ID="M1", name="Manufacturer 1", capacity=500, initial_level=300, inventoty_holding_cost=3, replenishment_policy="sS", policy_param=[200])
distributor1 = scm.InventoryNode(ID="D1", name="Distributor 1", node_type="distributor", capacity=300, initial_level=100, inventory_holding_cost=3, replenishment_policy="sS", policy_param=[50])
retailer1 = scm.InventoryNode(ID="R1", name="Retailer 1", node_type="retailer", capacity=100, initial_level=50, inventory_holding_cost=3, replenishment_policy="sS", policy_param=[50])
retailer2 = scm.InventoryNode(ID="R1", name="Retailer 1", node_type="retailer", capacity=100, initial_level=50, inventory_holding_cost=3, replenishment_policy="sS", policy_param=[50])
retailer3 = scm.InventoryNode(ID="R1", name="Retailer 1", node_type="retailer", capacity=100, initial_level=50, inventory_holding_cost=3, replenishment_policy="sS", policy_param=[50])
# Create links between the nodes
link_sup1_man1 = scm.Link(ID="L1", source=supplier1, sink=manufacturer1, cost=5, lead_time=3)
link_man1_dis1 = scm.Link(ID="L2", source=manufacturer1, sink=distributor1, cost=50, lead_time=2)
link_dis1_ret1 = scm.Link(ID="L3", source=distributor1, sink=retailer1, cost=50, lead_time=4)
link_dis1_ret2 = scm.Link(ID="L4", source=distributor1, sink=retailer2, cost=50, lead_time=4)
link_dis1_ret3 = scm.Link(ID="L5", source=distributor1, sink=retailer3, cost=50, lead_time=4)
# Create a demand
demand_r1 = scm.Demand(ID="demand_R1", name="Demand 1", order_arrival_model=lambda: 5, order_quantity_model=lambda: 5, demand_node=retailer1)
demand_r2 = scm.Demand(ID="demand_R2", name="Demand 2", order_arrival_model=lambda: 3, order_quantity_model=lambda: 7, demand_node=retailer2)
demand_r3 = scm.Demand(ID="demand_R3", name="Demand 3", order_arrival_model=lambda: 1, order_quantity_model=lambda: 9, demand_node=retailer3)
# Create a supply chain network
scnet = scm.create_sc_net(nodes=[supplier1, manufacturer1, distributor1, retailer1, retailer2, retailer3],
                          links=[link_sup1_man1, link_man1_dis1, link_dis1_ret1, link_dis1_ret2, link_dis1_ret3],
                          demands=[demand_r1, demand_r2, demand_r3])
# visualize the supply chain network
scm.visualize_sc_net(scnet)
# Simulate the supply chain network
scm.simulate_sc_net(scnet, sim_time=100)