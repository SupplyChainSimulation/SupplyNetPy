import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
import core as scm
import utilities as scm

import simpy
import numpy as np
import matplotlib.pyplot as plt

"""
 Demand for the Deskpro computer at Best Buy is 1,000 units per month. Best Buy incurs a fixed order placement, 
 transportation, and receiving cost of $4,000 each time an order is placed. Each computer costs Best Buy $500 
 and the retailer has a holding cost of 20 percent. Evaluate the number of computers that the store manager 
 should order in each replenishment lot.
 
 Analysis:
 In this case, the store manager has the following inputs:
 - Annual demand, D = 1,000 * 12 = 12,000 units (approx 34 units per day)
 - Order cost per lot, S = 4,000 
 - Unit cost per computer, C = 500
 - Holding cost per year as a fraction of unit cost, h = 0.2 (500*0.2 = 100 per year => 100/365 = 0.273 per day)

 Assumptions:
 - Demand is constant and deterministic
 - Lead time is zero

Optimum Economic Order Quantity (EOQ) is determined to minimize the total cost.
Total cost = Annual material cost + Annual ordering cost + Annual holding cost
This is same as -> Total cost = total transportation cost + inventory cost (we'll ignore material cost since it is constant)
"""

D = 12000 # annual demand
d = 34 # daily demand
order_cost = 4000 # order cost
unit_cost = 500 # unit cost
holding_cost = 0.273 # holding cost per day
lead_time = 0 # lead time

simlen = 3650 # simulation length in days


total_cost_arr = []
unsat_arr = []
for lot_size in range(800,1600,10):

    order_interval = int(365*lot_size/D)
    
    env = simpy.Environment()
    
    hp_supplier = scm.Supplier(env=env, ID="S1", name="HPComputers", node_type="infinite_supplier")

    bestbuy = scm.InventoryNode(env=env, ID="D1", name="Best Buy", node_type="distributor",
                                    capacity=lot_size, initial_level=lot_size, inventory_holding_cost=holding_cost,
                                    replenishment_policy="periodic", policy_param=[order_interval,lot_size], product_sell_price=unit_cost)

    link1 = scm.Link(env=env,ID="l1", source=hp_supplier, sink=bestbuy, cost=order_cost, lead_time=lambda: lead_time)

    demand1 = scm.Demand(env=env,ID="d1", name="demand_d1", order_arrival_model=lambda: 1, 
                        order_quantity_model=lambda: d, demand_node=bestbuy, tolerance=0.2)
    scm.global_logger.disable_logging() # disable logging for all components
    env.run(until=simlen)

    bb_invlevels = np.array(bestbuy.inventory.instantaneous_levels)
    hp_sup_transportation_cost = np.array(bestbuy.transportation_cost)

    total_cost = sum(bb_invlevels[:,1])*holding_cost + sum(hp_sup_transportation_cost[:,1])
    total_cost_arr.append([lot_size, total_cost/simlen])
    
    if(demand1.unsatisfied_demand):
        unsat_demand = np.array(demand1.unsatisfied_demand)
    else:
        unsat_demand = np.zeros((1,2))
    unsat_arr.append([lot_size,sum(unsat_demand[:,1])])
    print(f"hold cost = {sum(bb_invlevels[:,1])*holding_cost:.2f}, order cost = {sum(hp_sup_transportation_cost[:,1])}, avg cost per year = {total_cost*365/simlen:.2f}, unsat demand = {sum(unsat_demand[:,1])}")

total_cost_arr = np.array(total_cost_arr)
unsat_arr = np.array(unsat_arr)
EOQ = np.argmin(total_cost_arr[:,1])

plt.subplot(2,1,1)
plt.plot(total_cost_arr[:,0], total_cost_arr[:,1],marker='.',linestyle='-')
plt.plot(total_cost_arr[EOQ,0], total_cost_arr[EOQ,1],marker='o',color='red',label=f'EOQ = {total_cost_arr[EOQ,0]:.2f} with cost = {total_cost_arr[EOQ,1]:.2f}')
plt.xlabel("lot size")
plt.ylabel("Average cost per day")
plt.title("Average cost vs lot size")
plt.legend()
plt.grid()

plt.subplot(2,1,2)
plt.plot(unsat_arr[:,0], unsat_arr[:,1],marker='.',linestyle='-')
plt.xlabel("lot size")
plt.ylabel("Unsatisfied demand")
plt.title("Unsatisfied demand vs lot size")
plt.grid()

plt.show()
