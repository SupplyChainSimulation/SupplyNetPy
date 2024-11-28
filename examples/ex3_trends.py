# # local import for testing
import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
import core as scm
import utilities as scm

# import the library
import matplotlib.pyplot as plt
# import SupplyNetPy.Components as scm

# ID, name, node_type, capacity, initial_level, inventory_holding_cost, replenishment_policy, policy_parameters
nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier'},
            {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 800, 'initial_level': 500, 'inventory_holding_cost': 0.1, 'replenishment_policy': 'sS', 'policy_param': [300],'product_sell_price': 350},
            {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 400, 'initial_level': 200, 'inventory_holding_cost': 0.5, 'replenishment_policy': 'sS', 'policy_param': [100],'product_sell_price': 360}
]

# ID, from_node, to_node, transportation_cost, lead_time
links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 80, 'lead_time': lambda: 1},
            {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 100, 'lead_time': lambda: 2}
]

# ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
demands = [{'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 'order_arrival_model': lambda: 0.09, 'order_quantity_model': lambda: 1, 'demand_node': 'D1'}]

# an empty list to hold net_profit of different simulation results
net_profit = []
unsat_demand = []
product_sold = []
sc_total_cost = []
inv_costs = []
transport_costs = []
node_profit = []
node_inv_cost = []
node_costs = []
node_products_sold = []
man_inv_cost = []
man_trans_cost = []
man_cost = []
man_profit = []
man_product_sold = []

# let us disable the logging, since we are doing multiple simulations
#scm.global_logger.disable_logging()
scm.global_logger.enable_logging(log_to_screen=False)

scm.default_product.manufacturing_time = 4
scm.default_product.manufacturing_cost = 340
print(scm.default_product.get_info())
print(scm.default_raw_material.get_info())

# inventory replenishment parameter for D1 (Note: Ss replenishment: check inventory levels every day, if it goes below threshold 's' then order to replenish it back to capacity 'S')
start = 10
end = 400
step = 10
simulation_period = 120
s = start
while(s<end):
    # change 's' for 'D1'
    nodes[2]['policy_param'] = [s]
    scm.global_logger.logger.info(f'\n *** \n Running simulation for D1 with s = {s}')
    # run the simulations
    supplychainnet = scm.create_sc_net(nodes, links, demands)
    supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=simulation_period)
    # record the perfomance of the model (in our case, the sc_profit)
    net_profit.append(supplychainnet['performance']['sc_profit'])
    unsat_demand.append(supplychainnet['performance']['total_unsatisfied_demand'])
    product_sold.append(supplychainnet['performance']['total_product_sold'])
    inv_costs.append(supplychainnet['performance']['sc_inv_cost'])
    sc_total_cost.append(supplychainnet['performance']['sc_total_cost'])
    transport_costs.append(supplychainnet['performance']['sc_tranport_cost'])
    node_inv_cost.append(supplychainnet['nodes'][2].inventory_cost)
    node_costs.append(supplychainnet['nodes'][2].node_cost)
    node_profit.append(supplychainnet['nodes'][2].net_profit)
    node_products_sold.append(supplychainnet['nodes'][2].total_products_sold)
    man_inv_cost.append(supplychainnet['nodes'][1].inventory_cost)
    man_trans_cost.append(supplychainnet['nodes'][1].transportation_cost)
    man_cost.append(supplychainnet['nodes'][1].node_cost)
    man_profit.append(supplychainnet['nodes'][1].net_profit)
    man_product_sold.append(supplychainnet['nodes'][1].total_products_sold)
    # next value for 's', the inventory parameter
    s += step
    del supplychainnet

plt.subplot(3, 3, 1)
plt.plot(range(start,end,step),man_inv_cost,label='M1 Inv cost',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('M1 Inv cost')
plt.legend()

plt.subplot(3, 3, 2)
plt.plot(range(start,end,step),man_cost,label='M1 node cost',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('M1 node cost')
plt.legend()

plt.subplot(3, 3, 3)
plt.plot(range(start,end,step),man_profit,label='M1 net profit',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('M1 net profit')
plt.legend()

plt.subplot(3, 3, 4)
plt.plot(range(start,end,step),node_inv_cost,label='D1 Inv cost',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('D1 Inv cost')
plt.legend()

plt.subplot(3, 3, 5)
plt.plot(range(start,end,step),node_costs,label='D1 node cost',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('D1 node cost')
plt.legend()

plt.subplot(3, 3, 6)
plt.plot(range(start,end,step),node_profit,label='D1 net profit',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('D1 net profit')
plt.legend()

plt.subplot(3, 3, 7)
plt.plot(range(start,end,step),inv_costs,label='sc inv cost',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('sc inv cost')
plt.legend()

plt.subplot(3, 3, 8)
plt.plot(range(start,end,step),sc_total_cost,label='SC total cost',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('SC total cost')
plt.legend()

plt.subplot(3, 3, 9)
plt.plot(range(start,end,step),net_profit,label='sc net_profit',marker='.', linestyle='-', color='b')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('sc tnet_profit')
plt.legend()
plt.show()