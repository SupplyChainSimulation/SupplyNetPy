# # local import for testing
import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
import core as scm
import utilities as scm
import numpy as np

# import SupplyNetPy.Components as scm # import the library
import matplotlib.pyplot as plt

class Distributions:
    def __init__(self, mean, std, lam, low, high):
        self.mean = mean
        self.std = std
        self.lam = lam
        self.low = low
        self.high = high

    def normal(self):
        sample = -1
        while(sample<0):
            sample = np.random.normal(self.mean, self.std, 1)
        return sample[0]
    
    def poisson(self):
        sample = np.random.poisson(self.lam, 1)
        return sample[0]
    
    def uniform(self):
        sample = np.random.uniform(self.low, self.high, 1)
        return sample[0]

distri = Distributions(mean=20, std=5, lam=1, low=1, high=5)
rawmat1 = scm.RawMaterial(ID='rm1', name='raw_material1', extraction_quantity=100, extraction_time=1, mining_cost=0.3, cost=0.5)
product = scm.Product(ID='p1', name='product1', manufacturing_cost=50, manufacturing_time=2,sell_price=100, raw_materials=[(rawmat1,1)], batch_size=10)

# ID, name, node_type, capacity, initial_level, inventory_holding_cost, replenishment_policy, policy_parameters
nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier', 'raw_material': rawmat1},
         
            {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 800, 'initial_level': 500, 
             'inventory_holding_cost': 0.1, 'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s':300,'S':800},
             'product':product, 'product_sell_price': 345},

            {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 500, 'initial_level': 200, 
             'inventory_holding_cost': 1, 'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s':100,'S':500},
             'product_buy_price': 180,'product_sell_price': 348}]

# ID, from_node, to_node, transportation_cost, lead_time
links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 50, 'lead_time': distri.uniform},
            {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 60, 'lead_time': distri.uniform}]

# ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
demands = [{'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 'order_arrival_model': lambda: 1, 'order_quantity_model': distri.normal, 'demand_node': 'D1'}]
scm.global_logger.disable_logging() # let us disable the logging, since we are doing multiple simulations

start = 10
end = 500
step = 10
simulation_period = 120
s = start

inv_costs = []
node_costs = []
net_profits = []
d1_inv_costs = []
d1_net_profits = []
while(s<end):
    # change 's' for 'D1'
    nodes[2]['policy_param']['s'] = s
    scm.global_logger.logger.info(f'\n *** \n Running simulation for D1 with s = {s}')
    # run the simulations
    supplychainnet = scm.create_sc_net(nodes, links, demands)
    scm.global_logger.enable_logging()
    supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=simulation_period)
    # record the perfomance of the model (in our case, the sc_profit)
    inv_costs.append(supplychainnet["nodes"]["M1"].stats.inventory_carry_cost)
    node_costs.append(supplychainnet["nodes"]["M1"].stats.node_cost)
    net_profits.append(supplychainnet["nodes"]["M1"].stats.profit)

    d1_inv_costs.append(supplychainnet["nodes"]['D1'].stats.inventory_carry_cost)
    d1_net_profits.append(supplychainnet["nodes"]['D1'].stats.profit)
    
    # next value for 's', the inventory parameter
    s += step
    del supplychainnet

plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
plt.subplot(2, 2, 1)
plt.plot(range(start, end, step), inv_costs, label='M1 Inventory Cost')
plt.ylabel('Inventory cost')

plt.legend()

plt.subplot(2, 2, 2)
plt.plot(range(start, end, step), node_costs, label='M1 Node Cost')    
plt.ylabel('Node cost')

plt.legend()

plt.subplot(2, 2, 3)
plt.plot(range(start, end, step), net_profits, label='M1 Net Profit')
plt.xlabel('Replenishment Parameter (s)')
plt.ylabel('Net Profit')
plt.legend()

plt.figure()
plt.subplot(2, 1, 1)
plt.plot(range(start, end, step), d1_inv_costs, label='D1 Inventory Cost')
plt.ylabel('Inventory cost')
plt.legend()

plt.subplot(2, 1, 2)
plt.plot(range(start, end, step), d1_net_profits, label='D1 Net Profit')    
plt.xlabel('Replenishment Parameter (s)')
plt.ylabel('Net Profit')
plt.legend()
plt.suptitle('Inventory Cost and Net Profit for M1 and D1 with different s values')

plt.show()