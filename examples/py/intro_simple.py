import SupplyNetPy.Components as scm
import simpy

"""
supplier1 = {'ID': 'S1', 'name': 'Supplier1', 'node_type': 'infinite_supplier'}
distributor1 = {'ID': 'D1', 'name': 'Distributor1', 'node_type': 'distributor', 
                'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 0.2, 
                'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s':100,'S':150},
                'product_buy_price': 100,'product_sell_price': 105}
link1 = {'ID': 'L1', 'source': 'S1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}
demand1 = {'ID': 'd1', 'name': 'Demand1', 'order_arrival_model': lambda: 1,
            'order_quantity_model': lambda: 10, 'demand_node': 'D1'}
supplychainnet = scm.create_sc_net(nodes=[supplier1, distributor1], links=[link1], demands=[demand1])
supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=20, logging=True)

#D1_node = supplychainnet["nodes"]["D1"] # Get D1 node 
#stats = D1_node.stats.get_statistics() # Get D1_node statistics
#print(stats) # print
"""

env = simpy.Environment() # create a simpy environment

# create an infinite supplier
supplier1 = scm.Supplier(env=env, ID='S1', name='Supplier', node_type="infinite_supplier") 

# create a distributor node
distributor1 = scm.InventoryNode(env=env, ID='D1', name='Distributor1', node_type='distributor',
                                 capacity=150, initial_level=50, inventory_holding_cost=0.2,
                                 replenishment_policy=scm.SSReplenishment, 
                                 policy_param={'s':100, 'S':150}, product_buy_price=100,
                                 product_sell_price=105)

# create a link for distributor
link1 = scm.Link(env=env, ID='L1', source=supplier1, sink=distributor1, cost=5, lead_time=lambda: 2)

# create demand at distributor1
demand1 = scm.Demand(env=env, ID='d1', name='Demand1', order_arrival_model=lambda: 1, 
                     order_quantity_model=lambda:10, demand_node=distributor1)

# we can simulate the supply chain 
env.run(until=20)

supplychainnet = scm.create_sc_net(env=env, nodes=[supplier1, distributor1], links=[link1], demands=[demand1])
supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=20, logging=True)