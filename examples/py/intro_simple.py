#import-st
import SupplyNetPy.Components as scm
#import-en

#sup-st
supplier1 = {'ID': 'S1', 'name': 'Supplier1', 'node_type': 'infinite_supplier'}
#sup-en

#dis-st
distributor1 = {'ID': 'D1', 'name': 'Distributor1', 'node_type': 'distributor', 
                'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 0.2, 
                'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s':100,'S':150},
                'product_buy_price': 100,'product_sell_price': 105}
#dis-en

#ln-st
link1 = {'ID': 'L1', 'source': 'S1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}
#ln-en

#dem-st
demand1 = {'ID': 'd1', 'name': 'Demand1', 'order_arrival_model': lambda: 1,
            'order_quantity_model': lambda: 10, 'demand_node': 'D1'}
#dem-en
#cr-sim-st
# create a supply chain network
supplychainnet = scm.create_sc_net(nodes=[supplier1, distributor1], links=[link1], demands=[demand1])

# simulate for 20 days
supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=20, logging=True)
#cr-sim-en

#node-info-st
D1_node = supplychainnet["nodes"]["D1"] # Get D1 node 
stats = D1_node.stats.get_statistics() # Get D1_node statistics
print(stats) # print
#node-info-en

"""
#node-info-out-st
{'demand_placed': [5, 300], 
'fulfillment_received': [4, 250], 
'demand_received': [20, 200], 
'demand_fulfilled': [20, 200], 
'orders_shortage': [0, 0], 
'backorder': [0, 0], 
'inventory_level': 100, 
'inventory_waste': 0, 
'inventory_carry_cost': 410.0, 
'inventory_spend_cost': 25000, 
'transportation_cost': 25, 
'node_cost': 25435.0, 
'revenue': 21000, 
'profit': -4435.0}
#node-info-out-en
"""

"""
#alt-st
import simpy # importing simpy to create a simpy environment

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
#alt-en

#alt-util-st
# create a supply chain network
supplychainnet = scm.create_sc_net(env=env, nodes=[supplier1, distributor1], 
                                   links=[link1], demands=[demand1])

# simulate
supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=20, logging=True)
#alt-util-en
"""

"""
#out-st
INFO D1 - 0.0000:D1: Inventory levels:50, on hand:50
INFO D1 - 0.0000:D1:Replenishing inventory from supplier:Supplier1, order placed for 100 units.
INFO D1 - 0.0000:D1:shipment in transit from supplier:Supplier1.
INFO d1 - 0.0000:d1:Customer1:Order quantity:10, available.
INFO D1 - 0.0000:D1: Inventory levels:40, on hand:140
INFO d1 - 1.0000:d1:Customer2:Order quantity:10, available.
INFO D1 - 1.0000:D1: Inventory levels:30, on hand:130
INFO D1 - 2.0000:D1:Inventory replenished. reorder_quantity=100, Inventory levels:130
INFO d1 - 2.0000:d1:Customer3:Order quantity:10, available.
INFO D1 - 2.0000:D1: Inventory levels:120, on hand:120
INFO d1 - 3.0000:d1:Customer4:Order quantity:10, available.
INFO D1 - 3.0000:D1: Inventory levels:110, on hand:110
INFO d1 - 4.0000:d1:Customer5:Order quantity:10, available.
INFO D1 - 4.0000:D1: Inventory levels:100, on hand:100
INFO D1 - 4.0000:D1:Replenishing inventory from supplier:Supplier1, order placed for 50 units.
INFO D1 - 4.0000:D1:shipment in transit from supplier:Supplier1.
INFO d1 - 5.0000:d1:Customer6:Order quantity:10, available.
INFO D1 - 5.0000:D1: Inventory levels:90, on hand:140
INFO D1 - 6.0000:D1:Inventory replenished. reorder_quantity=50, Inventory levels:140
INFO d1 - 6.0000:d1:Customer7:Order quantity:10, available.
INFO D1 - 6.0000:D1: Inventory levels:130, on hand:130
INFO d1 - 7.0000:d1:Customer8:Order quantity:10, available.
INFO D1 - 7.0000:D1: Inventory levels:120, on hand:120
INFO d1 - 8.0000:d1:Customer9:Order quantity:10, available.
INFO D1 - 8.0000:D1: Inventory levels:110, on hand:110
INFO d1 - 9.0000:d1:Customer10:Order quantity:10, available.
INFO D1 - 9.0000:D1: Inventory levels:100, on hand:100
INFO D1 - 9.0000:D1:Replenishing inventory from supplier:Supplier1, order placed for 50 units.
INFO D1 - 9.0000:D1:shipment in transit from supplier:Supplier1.
INFO d1 - 10.0000:d1:Customer11:Order quantity:10, available.
INFO D1 - 10.0000:D1: Inventory levels:90, on hand:140
INFO D1 - 11.0000:D1:Inventory replenished. reorder_quantity=50, Inventory levels:140
INFO d1 - 11.0000:d1:Customer12:Order quantity:10, available.
INFO D1 - 11.0000:D1: Inventory levels:130, on hand:130
INFO d1 - 12.0000:d1:Customer13:Order quantity:10, available.
INFO D1 - 12.0000:D1: Inventory levels:120, on hand:120
INFO d1 - 13.0000:d1:Customer14:Order quantity:10, available.
INFO D1 - 13.0000:D1: Inventory levels:110, on hand:110
INFO d1 - 14.0000:d1:Customer15:Order quantity:10, available.
INFO D1 - 14.0000:D1: Inventory levels:100, on hand:100
INFO D1 - 14.0000:D1:Replenishing inventory from supplier:Supplier1, order placed for 50 units.
INFO D1 - 14.0000:D1:shipment in transit from supplier:Supplier1.
INFO d1 - 15.0000:d1:Customer16:Order quantity:10, available.
INFO D1 - 15.0000:D1: Inventory levels:90, on hand:140
INFO D1 - 16.0000:D1:Inventory replenished. reorder_quantity=50, Inventory levels:140
INFO d1 - 16.0000:d1:Customer17:Order quantity:10, available.
INFO D1 - 16.0000:D1: Inventory levels:130, on hand:130
INFO d1 - 17.0000:d1:Customer18:Order quantity:10, available.
INFO D1 - 17.0000:D1: Inventory levels:120, on hand:120
INFO d1 - 18.0000:d1:Customer19:Order quantity:10, available.
INFO D1 - 18.0000:D1: Inventory levels:110, on hand:110
INFO d1 - 19.0000:d1:Customer20:Order quantity:10, available.
INFO D1 - 19.0000:D1: Inventory levels:100, on hand:100
INFO D1 - 19.0000:D1:Replenishing inventory from supplier:Supplier1, order placed for 50 units.
INFO D1 - 19.0000:D1:shipment in transit from supplier:Supplier1.
INFO sim_trace - Supply chain info:
INFO sim_trace - available_inv                     : 100
INFO sim_trace - avg_available_inv                 : 112.5
INFO sim_trace - avg_cost_per_item                 : 50.87
INFO sim_trace - avg_cost_per_order                : 1017.4
INFO sim_trace - backorders                        : [0, 0]
INFO sim_trace - demand_by_customers               : [20, 200]
INFO sim_trace - demand_by_site                    : [5, 300]
INFO sim_trace - demands                           : {'d1': Demand1}
INFO sim_trace - env                               : <simpy.core.Environment object at 0x0000028D55F67C10>
INFO sim_trace - fulfillment_received_by_customers : [20, 200]
INFO sim_trace - fulfillment_received_by_site      : [4, 250]
INFO sim_trace - inventory_carry_cost              : 410.0
INFO sim_trace - inventory_spend_cost              : 25000
INFO sim_trace - inventory_waste                   : 0
INFO sim_trace - links                             : {'L1': S1 to D1}
INFO sim_trace - nodes                             : {'S1': Supplier1, 'D1': Distributor1}
INFO sim_trace - num_distributors                  : 1
INFO sim_trace - num_manufacturers                 : 0
INFO sim_trace - num_of_links                      : 1
INFO sim_trace - num_of_nodes                      : 2
INFO sim_trace - num_retailers                     : 0
INFO sim_trace - num_suppliers                     : 1
INFO sim_trace - profit                            : -4435.0
INFO sim_trace - revenue                           : 21000
INFO sim_trace - shortage                          : [0, 0]
INFO sim_trace - total_cost                        : 25435.0
INFO sim_trace - total_demand                      : [25, 500]
INFO sim_trace - total_fulfillment_received        : [24, 450]
INFO sim_trace - transportation_cost               : 25
#out-en
"""

