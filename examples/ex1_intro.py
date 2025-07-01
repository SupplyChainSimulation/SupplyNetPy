# local import for testing
import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
import core as scm
import utilities as scm

#import SupplyNetPy.Components as scm # import the library
supplier1 = {'ID': 'S1', 'name': 'Supplier1', 'node_type': 'infinite_supplier'}
distributor1 = {'ID': 'D1', 'name': 'Distributor1', 'node_type': 'distributor', 'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 0.2, 'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s':100,'S':150},'product_buy_price': 100,'product_sell_price': 105}
link1 = {'ID': 'L1', 'source': 'S1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}
demand1 = {'ID': 'd1', 'name': 'Demand1', 'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10, 'demand_node': 'D1'}
scm.global_logger.enable_logging() # enable logging for debugging
supplychainnet = scm.create_sc_net(nodes=[supplier1, distributor1], links=[link1], demands=[demand1])
supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=20)