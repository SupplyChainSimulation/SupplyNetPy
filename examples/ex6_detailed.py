# A detailed example of a supply chain network including raw products, products 

# local import for testing
import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
import core as scm
import utilities as scm

# import SupplyNetPy.Components as scm
import simpy

env = simpy.Environment()
# Define raw materials
raw_material1 = scm.RawMaterial(ID="rm1", name="RawMaterial1", extraction_quantity=200, extraction_time=1, mining_cost=0.02, cost=0.5)
raw_material2 = scm.RawMaterial(ID="rm2",name="RawMaterial2", extraction_quantity=300, extraction_time=1, mining_cost=0.02, cost=0.5)

# Define product
product = scm.Product(ID="pr1", name="Product1", manufacturing_cost=20, manufacturing_time=2, sell_price=100, 
                      raw_materials=[(raw_material1,12),(raw_material2,15)],batch_size=30)

# Define suppliers
supplier1 = scm.Supplier(env=env, ID="s1",name="Supplier1",capacity=10000, initial_level=3000, 
                         inventory_holding_cost=0.10, raw_material= raw_material1)
supplier2 = scm.Supplier(env=env, ID="s2",name="Supplier2",capacity=10000, initial_level=3000, 
                         inventory_holding_cost=0.10, raw_material= raw_material2)

# Define manufacturer
manufacturer = scm.Manufacturer(env=env, ID="m1", name="Manufacturer1", capacity=500, initial_level=300, 
                                inventory_holding_cost=0.10, product=product, product_sell_price=100,
                                replenishment_policy=scm.SSReplenishment, policy_param={'s':350,'S':500})


# Define distributor
distributor = scm.InventoryNode(env=env, ID="d1", name="Distributor1", node_type="distributor", capacity=400, 
                                initial_level=200, inventory_holding_cost=0.10, product=product, product_sell_price=100,
                                replenishment_policy=scm.SSReplenishment, policy_param={'s':200, 'S':400},
                                product_buy_price=95)

# Define retailers
retailer1 = scm.InventoryNode(env=env, ID="r1", name="Retailer1", node_type="retailer", capacity=200, initial_level=100,
                            inventory_holding_cost=0.10, product=product, product_sell_price=100,
                            replenishment_policy=scm.SSReplenishment, policy_param={'s':50, 'S':200}, product_buy_price=98)
retailer2 = scm.InventoryNode(env=env, ID="r2", name="Retailer2", node_type="retailer", capacity=200, initial_level=100,
                            inventory_holding_cost=0.10, product=product, product_sell_price=100,
                            replenishment_policy=scm.SSReplenishment, policy_param={'s':50, 'S':200}, product_buy_price=97)

demand_r1 = scm.Demand(env=env,ID="demand_r1", name="demand1", order_arrival_model=lambda: 1, order_quantity_model=lambda: 10, demand_node=retailer1)

demand_r2 = scm.Demand(env=env,ID="demand_r2", name="demand2", order_arrival_model=lambda: 1, order_quantity_model=lambda: 10, demand_node=retailer2)

link1 = scm.Link(env=env, ID="l1", source=supplier1, sink=manufacturer, cost=80, lead_time=lambda: 1)
link2 = scm.Link(env=env, ID="l2", source=supplier2, sink=manufacturer, cost=80, lead_time=lambda: 1)
link3 = scm.Link(env=env, ID="l3", source=manufacturer, sink=distributor, cost=100, lead_time=lambda: 2)
link4 = scm.Link(env=env, ID="l4", source=distributor, sink=retailer1, cost=50, lead_time=lambda: 1)
link5 = scm.Link(env=env, ID="l5", source=distributor, sink=retailer2, cost=50, lead_time=lambda: 1)

scnet = scm.create_sc_net(env=env, nodes = [supplier1, supplier2, manufacturer, distributor, retailer1, retailer2],
                          links = [link1, link2, link3, link4, link5],
                          demands = [demand_r1, demand_r2])
# Run the simulation
scnet = scm.simulate_sc_net(scnet, sim_time=120)
scm.visualize_sc_net(scnet)