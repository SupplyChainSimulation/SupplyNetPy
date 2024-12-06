# local import for testing
# import sys, os
# sys.path.insert(1, 'src/SupplyNetPy/Components')
# import core as scm
# import utilities as scm

# import the library
import SupplyNetPy.Components as scm

# ID, name, node_type, capacity, initial_level, inventory_holding_cost, replenishment_policy, policy_parameters
nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier'},
            {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 300, 'initial_level': 200, 'inventory_holding_cost': 0.5, 'replenishment_policy': 'sS', 'policy_param': [150],'product_sell_price': 310},
            {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 1, 'replenishment_policy': 'sS', 'policy_param': [40],'product_sell_price': 320},
            {'ID': 'R1', 'name': 'Retailer 1', 'node_type': 'retailer', 'capacity': 100, 'initial_level': 50, 'inventory_holding_cost': 3, 'replenishment_policy': 'sS', 'policy_param': [50],'product_sell_price': 330},
            {'ID': 'R2', 'name': 'Retailer 2', 'node_type': 'retailer', 'capacity': 100, 'initial_level': 50, 'inventory_holding_cost': 3, 'replenishment_policy': 'sS', 'policy_param': [50],'product_sell_price': 335},
            {'ID': 'R3', 'name': 'Retailer 3', 'node_type': 'retailer', 'capacity': 100, 'initial_level': 50, 'inventory_holding_cost': 3, 'replenishment_policy': 'sS', 'policy_param': [50],'product_sell_price': 325}
        ]

# ID, from_node, to_node, transportation_cost, lead_time
links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': lambda: 3},
            {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2},
            {'ID': 'L3', 'source': 'D1', 'sink': 'R1', 'cost': 5, 'lead_time': lambda: 2},
            {'ID': 'L4', 'source': 'D1', 'sink': 'R2', 'cost': 5, 'lead_time': lambda: 2},
            {'ID': 'L5', 'source': 'D1', 'sink': 'R3', 'cost': 5, 'lead_time': lambda: 2}
        ]

# ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
demands = [{'ID': 'demand_R1', 'name': 'Demand 1', 'node_type': 'demand', 'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10, 'demand_node': 'R1'},
            {'ID': 'demand_R2', 'name': 'Demand 2', 'node_type': 'demand', 'order_arrival_model': lambda: 2, 'order_quantity_model': lambda: 20, 'demand_node': 'R2'},
            {'ID': 'demand_R3', 'name': 'Demand 3', 'node_type': 'demand', 'order_arrival_model': lambda: 3, 'order_quantity_model': lambda: 15, 'demand_node': 'R3'}
          ]

scm.global_logger.enable_logging()
supplychainnet = scm.simulate_sc_net(scm.create_sc_net(nodes, links, demands), sim_time=30)
scm.visualize_sc_net(supplychainnet)