# import the library
import SupplyNetPy.Components as scm

# nodes input as netlist
# ID, name, node_type, capacity, initial_level, inventory_holding_cost, replenishment_policy, policy_parameters
nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'supplier', 'capacity': 600, 'initial_level': 600, 'inventory_holding_cost': 0.2},
            {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 300, 'initial_level': 200, 'inventory_holding_cost': 0.5, 'replenishment_policy': 'sS', 'policy_param': [150]},
            {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 1, 'replenishment_policy': 'sS', 'policy_param': [40]}
]

# nodes input as netlist
# ID, from_node, to_node, transportation_cost, lead_time
links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': 3},
            {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': 2}
]

# demands input as netlist
# ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
demands = [{'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 30, 'demand_node': 'D1'}]

scm.global_logger.enable_logging()
supplychainnet = scm.simulate_sc_net(scm.create_sc_net(nodes, links, demands), sim_time=30)