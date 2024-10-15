import SupplyNetPy.Components as snp
import simpy

env = simpy.Environment()
# Define raw materials
raw_material1 = snp.RawMaterial(ID="rm1", name="RawMaterial1", extraction_quantity=200, extraction_time=1, cost=0.25)
raw_material2 = snp.RawMaterial(ID="rm2",name="RawMaterial2", extraction_quantity=300, extraction_time=1, cost=0.5)

# Define product
product = snp.Product(ID="pr1", name="Product1", manufacturing_cost=20, manufacturing_time=2, sell_price=100, 
                      raw_materials=[{"raw_material": raw_material1, "quantity": 12},
                      {"raw_material": raw_material2, "quantity": 15}],
                      units_per_cycle=30)

# Define suppliers
supplier1 = snp.Supplier(env=env, ID="s1",name="Supplier1",capacity=10000, initial_level=3000, 
                         inventory_holding_cost=0.10, raw_material= raw_material1)
supplier2 = snp.Supplier(env=env, ID="s2",name="Supplier2",capacity=10000, initial_level=3000, 
                         inventory_holding_cost=0.10, raw_material= raw_material2)

# Define manufacturer
manufacturer = snp.Manufacturer(env=env, ID="m1", name="Manufacturer1", capacity=500, initial_level=300, 
                                inventory_holding_cost=0.10, product=product, product_sell_price=100,
                                replenishment_policy="sS", policy_param=[350])


# Define distributor
distributor = snp.InventoryNode(env=env, ID="d1", name="Distributor1", node_type="distributor", capacity=400, initial_level=200,
                                inventory_holding_cost=0.10, product=product, product_sell_price=100,
                                replenishment_policy="sS", policy_param=[100])

# Define retailers
retailer1 = snp.InventoryNode(env=env, ID="r1", name="Retailer1", node_type="retailer", capacity=200, initial_level=100,
                            inventory_holding_cost=0.10, product=product, product_sell_price=100,
                            replenishment_policy="sS", policy_param=[50])
retailer2 = snp.InventoryNode(env=env, ID="r2", name="Retailer2", node_type="retailer", capacity=200, initial_level=100,
                            inventory_holding_cost=0.10, product=product, product_sell_price=100,
                            replenishment_policy="sS", policy_param=[50])

demand_r1 = snp.Demand(env=env,ID="demand_r1", name="demand1", order_arrival_model=lambda: 1, order_quantity_model=lambda: 10, demand_node=retailer1)

demand_r2 = snp.Demand(env=env,ID="demand_r2", name="demand2", order_arrival_model=lambda: 1, order_quantity_model=lambda: 10, demand_node=retailer2)

link1 = snp.Link(env=env, ID="l1", source=supplier1, sink=manufacturer, cost=80, lead_time=lambda: 1)
link2 = snp.Link(env=env, ID="l2", source=supplier2, sink=manufacturer, cost=80, lead_time=lambda: 1)
link3 = snp.Link(env=env, ID="l3", source=manufacturer, sink=distributor, cost=100, lead_time=lambda: 2)
link4 = snp.Link(env=env, ID="l4", source=distributor, sink=retailer1, cost=50, lead_time=lambda: 1)
link5 = snp.Link(env=env, ID="l5", source=distributor, sink=retailer2, cost=50, lead_time=lambda: 1)

# Create the supply chain
scnet = {
    "env":env,
    "nodes": [supplier1, supplier2, manufacturer, distributor, retailer1, retailer2],
    "edges": [link1, link2, link3, link4, link5],
    "demand": [demand_r1, demand_r2],
    "num_suppliers": 2,
    "num_manufacturers": 1,
    "num_distributors": 1,
    "num_retailers": 2,
    "num_of_nodes": 6,
    "num_of_edges": 5,
}

# Run the simulation
scnet = snp.simulate_sc_net(scnet, sim_time=120)