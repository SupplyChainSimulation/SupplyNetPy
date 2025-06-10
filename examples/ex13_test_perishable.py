# local import for testing
import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components/')
import core as scm
import utilities as scm

import simpy
env = simpy.Environment()

shelf_life = 90

scm.default_raw_material = scm.RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=300, extraction_time=1, mining_cost=0.9, cost=3) # create a default raw material
scm.deafult_product = scm.Product(ID="P1", name="Product 1", manufacturing_cost=50, manufacturing_time=3, sell_price=341, raw_materials=[{"raw_material": scm.default_raw_material, "quantity": 3}], units_per_cycle=100) # create a default product

sup = scm.Supplier(env=env, ID='S1', name='Supplier', node_type="supplier", capacity=3000, initial_level=3000, 
                   inventory_holding_cost=0.1)

man = scm.Manufacturer(env=env, ID='M1', name='Manufacturer', capacity=800, initial_level=800, inventory_holding_cost=0.5,
                       inventory_type="perishable", shelf_life=shelf_life, replenishment_policy="sS", policy_param=[400], 
                       product_sell_price=310)

dis = scm.InventoryNode(env=env, ID='D1', name='Distributor', node_type="warehouse", capacity=500, initial_level=500, 
                        inventory_holding_cost=1, inventory_type="perishable", shelf_life=shelf_life, replenishment_policy="sS",
                        policy_param=[200], product_sell_price=320)

ret = scm.InventoryNode(env=env, ID='R1', name='Retailer', node_type="retailer", capacity=200, initial_level=200,
                        inventory_holding_cost=2, inventory_type="perishable", shelf_life=shelf_life, replenishment_policy="sS",
                        policy_param=[100], product_sell_price=330)

link_s1m1 = scm.Link(env=env, ID='L1', source=sup, sink=man, cost=5, lead_time=lambda: 3)
link_m1d1 = scm.Link(env=env, ID='L2', source=man, sink=dis, cost=5, lead_time=lambda: 2)
link_d1r1 = scm.Link(env=env, ID='L3', source=dis, sink=ret, cost=5, lead_time=lambda: 1)

demand_ret = scm.Demand(env=env, ID='demand_R1', name='Demand at Retailer', order_arrival_model=lambda: 1,
                        order_quantity_model=lambda: 50, demand_node=ret, tolerance = 2)

scm.global_logger.enable_logging(log_to_file=False)
env.run(until=360)