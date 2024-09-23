# import the library
import SupplyNetPy.Components as scm
import matplotlib.pyplot as plt

# ID, name, node_type, capacity, initial_level, inventory_holding_cost, replenishment_policy, policy_parameters
nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier'},
            {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 800, 'initial_level': 500, 'inventory_holding_cost': 0.1, 'replenishment_policy': 'sS', 'policy_param': [300],'product_sell_price': 350},
            {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 400, 'initial_level': 200, 'inventory_holding_cost': 0.5, 'replenishment_policy': 'sS', 'policy_param': [100],'product_sell_price': 360}
]

# ID, from_node, to_node, transportation_cost, lead_time
links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 3, 'lead_time': lambda: 1},
            {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 1, 'lead_time': lambda: 2}
]

# ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
demands = [{'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 'order_arrival_model': lambda: 0.09, 'order_quantity_model': lambda: 1, 'demand_node': 'D1'}]

# an empty list to hold net_profit of different simulation results
net_profit = []
unsat_demand = []
product_sold = []

# let us disable the logging, since we are doing multiple simulations
#scm.global_logger.disable_logging()
scm.global_logger.enable_logging()

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
    # run the simulations
    supplychainnet = scm.create_sc_net(nodes, links, demands)
    supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=simulation_period)
    # record the perfomance of the model (in our case, the sc_profit)
    net_profit.append(supplychainnet['performance']['sc_profit'])
    unsat_demand.append(supplychainnet['performance']['total_unsatisfied_demand'])
    product_sold.append(supplychainnet['performance']['total_product_sold'])
    # next value for 's', the inventory parameter
    s += step
    del supplychainnet

plt.subplot(2, 2, 1)
plt.plot(range(start,end,step),net_profit,label='Net Profit',marker='.', linestyle='-', color='b')
plt.title('Net Profit vs Inventory Replenishment Parameter (D1)')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('Net Profit')
plt.legend()

plt.subplot(2, 2, 2)
plt.plot(range(start,end,step),unsat_demand,label='Unsat Demand',marker='.', linestyle='-', color='r')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('Unsat Demand')
plt.legend()

plt.subplot(2, 2, 3)
plt.plot(range(start,end,step),product_sold,label='Product sold',marker='.', linestyle='-', color='g')
plt.xlabel('Inventory Replenishment Parameter (D1)')
plt.ylabel('Product sold')
plt.legend()
plt.show()
