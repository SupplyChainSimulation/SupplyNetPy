

# lets create a supply chain network for a single product inventory 
# with three sc nodes, a supplier, a manufacturer and a retailer
# lets import the library

import SupplyNetPy.Components as scm

# first we need to create a SimPy enviornment where we are going to run the supply chain simulations
import simpy
env = simpy.Environment()

# lets create a product
product1 = scm.Product(sku="12325",name="Brush",description="Cleaning supplies",cost=200,profit=100,product_type="Non-perishable",shelf_life=None)

# lets create supply chain nodes
supplier1 = scm.Supplier(env=env,name="supplier1",node_id=123,location="Goa",inv_capacity=800,inv_holding_cost=1,reorder_level=600)
manufacturer1 = scm.Manufacturer(env=env,name="man1",node_id=124,location="Mumbai",production_cost=100,production_level=200,
                                 products=[product1],inv_capacity=600,inv_holding_cost=2,reorder_level=300)
retailer1 = scm.Retailer(env=env,name=f"retailer1",node_id=125,location="Mumbai",products=[product1],inv_capacity=300,
                         inv_holding_cost=3,reorder_level=100)

# lets create links in the supply chain
link1 = scm.Link(from_node=supplier1,to_node=manufacturer1,lead_time=3,transportation_cost=100,link_distance=300)
link2 = scm.Link(from_node=manufacturer1,to_node=retailer1,lead_time=2,transportation_cost=70,link_distance=200)

# lets create some demand to the sc nodes
demand_ret1 = scm.Demand(env=env, arr_dist="Poisson",arr_params=[6],node=retailer1,demand_dist="Uniform",demand_params=[1,10])
demand_man1 = scm.Demand(env=env, arr_dist="Poisson",arr_params=[1],node=manufacturer1,demand_dist="Uniform",demand_params=[1,3])

# let put all together in a network
scnet = scm.createSC(products=[product1],
                     nodes = [supplier1,manufacturer1,retailer1],
                     links = [link1, link2],
                     demands = [demand_ret1,demand_man1])

# lets simulate the supply chain network we created
scm.global_logger.enable_logging(log_to_file=False,log_to_screen=True)
scm.simulate_sc_net(env,scnet,sim_time=50)