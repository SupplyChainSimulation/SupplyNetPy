# import the library
import SupplyNetPy.Components as scm
import matplotlib.pyplot as plt

# ID, name, node_type, capacity, initial_level, inventory_holding_cost, replenishment_policy, policy_parameters
nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier'},
            {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 300, 'initial_level': 200, 'inventory_holding_cost': 0.5, 'replenishment_policy': 'sS', 'policy_param': [200],'product_sell_price': 350},
            {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 1, 'replenishment_policy': 'sS', 'policy_param': [100],'product_sell_price': 360}
]

# ID, from_node, to_node, transportation_cost, lead_time
links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': lambda: 3},
            {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}
]

# ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
demands = [{'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10, 'demand_node': 'D1'}]

# an empty list to hold net_profit of different simulation results
net_profit = []

# let us disable the logging, since we are doing multiple simulations
scm.global_logger.disable_logging()

print(scm.default_product.get_info())
print(scm.default_raw_material.get_info())

# inventory replenishment parameter for D1 (Note: Ss replenishment: check inventory levels every day, if it goes below threshold 's' then order to replenish it back to capacity 'S')
start = 10
end = 150
step = 10
simulation_period = 60
s = start
while(s<end):
    # change 's' for 'D1'
    nodes[2]['policy_param'] = [s]
    # run the simulations
    supplychainnet = scm.create_sc_net(nodes, links, demands)
    supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=simulation_period)
    # record the perfomance of the model (in our case, the sc_profit)
    net_profit.append(supplychainnet['performance']['sc_profit'])
    # next value for 's', the inventory parameter
    s += step
    del supplychainnet

plt.plot(range(start,end,step),net_profit,label='Net Profit',marker='.', linestyle='-', color='b')
plt.title('Net Profit vs Inventory Replenishment Parameter (D1)')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('Net Profit')
plt.show()