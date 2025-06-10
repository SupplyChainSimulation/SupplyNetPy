import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
import core as scm
import utilities as scm

import simpy
import numpy as np
import matplotlib.pyplot as plt

def normal_quantity():
    sample = np.random.normal(357, 188, 1)[0]
    if(sample<0):
        sample = 1
    return sample

simlen = 3650 # simulation length in days
env = simpy.Environment()

# create an infinite supplier
supplier1 = scm.Supplier(env=env, ID="S1", name="Supplier1", node_type="infinite_supplier")

#create the distributor
distributor1 = scm.InventoryNode(env=env, ID="D1", name="Distributor1", node_type="distributor",
                                capacity=16000, initial_level=6000, inventory_holding_cost=0.1,
                                replenishment_policy="sS", policy_param=[6000], product_sell_price=399)

link1 = scm.Link(env=env,ID="l1", source=supplier1, sink=distributor1, cost=100, lead_time=lambda: 14)

demand1 = scm.Demand(env=env,ID="d1", name="demand_d1", 
                    order_arrival_model=lambda: 1, 
                    order_quantity_model=normal_quantity, demand_node=distributor1)

env.run(until=simlen)

# calculate performance metrics
safety_stock = []
replenish_cycles = [0]

inv_levels = np.array(distributor1.inventory.instantaneous_levels) # instantaneous inventory levels
# lets calculate safety stock level
for i in range(len(inv_levels)-1):
    if(inv_levels[i,1]<inv_levels[i+1,1]): # inventory level is increasing that means a replenishment order is received
        safety_stock.append(inv_levels[i,1])
        replenish_cycles.append(inv_levels[i,0]) # time of replenishment order

unsat_demand = np.array(demand1.unsatisfied_demand) # get record of unsatisfied demand, this is needed to calculate cycle service level
cycle_service_lvl = 0
prev_inx = -1
for i in range(len(unsat_demand)):
    inx = np.argmax(replenish_cycles > unsat_demand[i,0])
    if(inx!=prev_inx):
        cycle_service_lvl += 1
    prev_inx = inx

# calculate average flow time (amount of time an item is stored in inventory)
flow_time = []
for i in range(len(replenish_cycles)-1):
    flow_time.append(replenish_cycles[i+1]-replenish_cycles[i])

print("\n\t***\nSafety Stock Level: ", np.mean(safety_stock))
print("Average Inventory Level:", np.mean(inv_levels[:,1]))
print("Cycle Service Level: ", (len(replenish_cycles)-cycle_service_lvl+1)*100/len(replenish_cycles),"%")
print("Average Flow Time: ", np.mean(flow_time)/2, "days","\n")

# plot the inventory level over time
plt.plot(inv_levels[:,0], inv_levels[:,1],  label="Inventory Level", color='blue')
plt.axhline(y=6000, color='r', linestyle='--', label="ROP")
plt.xlabel("Time (days)")
plt.ylabel("Inventory Level")
plt.title("Inventory Level over Time")
plt.legend()
plt.grid()
plt.show()
