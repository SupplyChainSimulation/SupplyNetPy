"""
System Decription

Inventory Type: Perishable
Inventory position (level at given time t) = inventory on hand + inventory en route
Replenishment Policy: (s,S) When level falls below s, order is placed for (S - current inventory position) units
Review period = 1 day (monitor inventory everyday)

H = Inventory at hand
H' = Inventory at hand that expires at the end of the day t
P = Inventory position = H + inventory en route

Algorithm: Process flow of Perishable Inventory
Begin day t
    1. Order arrive at the Pharmacy
    2. Update Inventory Levels (H)
    3. Satisfy demand based on Inventory Levels
        3.1. If (d>H):
            - demand Satisfied = H
            - Shortage = d-H
            - Waste = 0
        3.2. Else:
            - demand Satisfied = d
            - Shortage = 0
            - Waste = max{0,H'-d}
    4. Discard Expired Drugs
    5. Update Inventory Levels (H)
        5.1. Is (s>P) and (Supplier not Disrupted):
            - Place order for (S-P)
        5.2. Else:
            - Do not place order
    6. End of the day t

Optimization Objective: Minimize Expected Cost per day
Costs of interest are shortage, waste, holding and ordering

Assumptions:
 - all drugs that arrive in the same month come from the same production batch and have 
 same end of the month expiration date. Hence drugs are only discarded at the end of the month.
 - the inventory on-hand and estimated days until inventory expires is known each day t.
 - lead time is deterministic and +ve. order place at the end of the day (t-1) arrives at the begining of the day t.
 - demand is stochastic
 - supply uncertainty is due to disruptions 
 (these two are independent of each other)
 - all demand that is not met is lost
 - first in first out protocol is followed when serving orders

 T = number of days (360 days)
 l = deterministic lead time (6 days)
 e = shelf life of the drugs (months) (3 months)
 R = number of simulation replication (5000)
 b = shortage cost (5 units)
 z = waste cost (1 units)
 h = holding cost (0.001 units)
 o = ordering cost (0.5 units)
 dt = demand on day t (stochastic) (Poission 25/day)
 yt = binary variable for supply disruption status on day t (yt=0 disrupted, yt=1 available) (stochastic) (p=0.01)

 No restriction on the probability distribution of these sources of uncertainty

"""

# Create the model
import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
import core as scm
import utilities as scm

import simpy
import numpy as np
# import SupplyNetPy.Components as scm
import matplotlib.pyplot as plt

# global variables

class Distributions:
    def __init__(self,mu,lam):
        self.mu = mu
        self.lam = lam

    def poisson_demand(self):
        return np.random.poisson(self.lam)

    def expo_arrival(self):
        return np.random.exponential(self.mu)

def manufacturer_date_cal(time_now):
    return (time_now//30)*30

def single_sim_run(S,s,ini_level):

    st = Distributions(mu=1,lam=25)
    # create the environment
    env = simpy.Environment()

    # create an infinite supplier
    supplier1 = scm.Supplier(env=env, ID="S1", name="Supplier 1", node_type="infinite_supplier", failure_p=0.01)

    #create the distributor
    distributor1 = scm.InventoryNode(env=env, ID="D1", name="Distributor 1", node_type="distributor",
                                    capacity=S, initial_level=ini_level, inventory_holding_cost=0.001, inventory_type="perishable",
                                    manufactur_date = manufacturer_date_cal,
                                    shelf_life=90, replenishment_policy="sS", policy_param=[s], product_sell_price=360)

    # set demand
    demand1 = scm.Demand(env=env,ID="d1", name="demand 1", 
                        order_arrival_model=st.expo_arrival, 
                        order_quantity_model=st.poisson_demand, demand_node=distributor1,
                        tolerance=float('inf'))
    # link the nodes
    link1 = scm.Link(env=env,ID="l1", source=supplier1, sink=distributor1, cost=0.5, lead_time=lambda: 6)
    # create a sc net
    #supplynet = {"nodes": [supplier1,distributor1], "links": [link1], "demand": [demand1]}
    # run the simulation
    env.run(until=360)
    instantaneous_levels = np.array(distributor1.inventory.instantaneous_levels)
    #plt.plot(instantaneous_levels[:,0], instantaneous_levels[:,1], marker='.', linestyle='-', color='b')
    #plt.xlabel('Time (days)')
    #plt.ylabel('Inventory Level')
    #plt.title('Inventory Level over Time')
    #plt.show()
    transportation_cost = np.array(supplier1.transportation_cost)
    transportation_cost = transportation_cost[transportation_cost[:,0]>30]
    if(distributor1.inventory.inventory.waste):
        waste_arr = np.array(distributor1.inventory.inventory.waste)
    else:
        waste_arr = np.array([[0,0]])
    print("Shortage: ", demand1.shortage)
    print("Waste: ", sum(waste_arr[30:,1]))
    instantaneous_levels = instantaneous_levels[instantaneous_levels[:,0]>30]
    print("Holding Cost: ", sum(instantaneous_levels[:,1])*0.001)
    print("Transportation Cost: ", len(transportation_cost)*0.5)
    print("Total Cost: ", (sum(demand1.shortage)*5 + sum(waste_arr[30:,1]) + sum(instantaneous_levels[:,1])*0.001 + len(transportation_cost)*0.5)/330)

def run_for_s(s_low,s_high,s_step,capacity,ini_level,num_replications):
    st = Distributions(mu=1,lam=25)
    R = num_replications # number of replications
    exp_cost_per_day = []
    for reorder_point in range(s_low,s_high,s_step):
        
        # initialize the costs
        shortage_cost = 0 #(5 units)
        waste_cost = 0 #(1 units)
        holding_cost = 0 #(0.001 units)
        ordering_cost = 0 #(0.5 units)
        
        exp_cost_arr = []

        for i in range(0,R):
            env = simpy.Environment()

            # create an infinite supplier
            supplier1 = scm.Supplier(env=env, ID="S1", name="Supplier 1", node_type="infinite_supplier", failure_p=0.01)

            #create the distributor
            distributor1 = scm.InventoryNode(env=env, ID="D1", name="Distributor 1", node_type="distributor",
                                            capacity=capacity, initial_level=ini_level, inventory_holding_cost=0.001, inventory_type="perishable",
                                            manufactur_date = manufacturer_date_cal,
                                            shelf_life=90, replenishment_policy="sS", policy_param=[reorder_point], product_sell_price=360)

            # set demand
            demand1 = scm.Demand(env=env,ID="d1", name="demand 1", 
                                order_arrival_model=st.expo_arrival, 
                                order_quantity_model=st.poisson_demand, demand_node=distributor1,
                                tolerance=float('inf'))
            # link the nodes
            link1 = scm.Link(env=env,ID="l1", source=supplier1, sink=distributor1, cost=0.5, lead_time=lambda: 6)
            # create a sc net
            #supplynet = {"nodes": [supplier1,distributor1], "links": [link1], "demand": [demand1]}
            scm.global_logger.disable_logging()
            # run the simulation
            env.run(until=360)

            if(demand1.shortage):
                shortage_arr = np.array(demand1.shortage)
                shortage_arr = shortage_arr[shortage_arr[:,0]>30]
            else:
                shortage_arr = np.array([[0,0]])
            if(distributor1.inventory.inventory.waste):
                waste_arr = np.array(distributor1.inventory.inventory.waste)
                waste_arr = waste_arr[waste_arr[:,0]>30]
            else:
                waste_arr = np.array([[0,0]])
            
            if(supplier1.transportation_cost):
                transportation_cost_arr = np.array(supplier1.transportation_cost)
                transportation_cost_arr = transportation_cost_arr[transportation_cost_arr[:,0]>30]
            else:
                transportation_cost_arr = np.array([[0,0]])
            instantaneous_levels = np.array(distributor1.inventory.instantaneous_levels)

            shortage_cost = sum(shortage_arr[:,1]) #(5 units)
            waste_cost = sum(waste_arr[:,1]) #(1 units)
            holding_cost = sum(instantaneous_levels[30:,1]) #(0.001 units)
            ordering_cost = sum(transportation_cost_arr[:,1]) #(0.5 units)

            exp_cost = (shortage_cost*5 + waste_cost + holding_cost*0.001 + ordering_cost*0.5)/330
            exp_cost_arr.append(exp_cost)

        exp_cost_per_day.append(sum(exp_cost_arr)/R)

    plt.plot(range(s_low,s_high,s_step), exp_cost_per_day, marker='.', linestyle='-', color='b', label=f"S={capacity}, ini_level={ini_level}")
    plt.xlabel('Reorder Point (s)')
    plt.ylabel('Expected Cost per Day')
    plt.legend()
    plt.show()

#single_sim_run(S=2000,s=500,ini_level=2000)
run_for_s(s_low=500,s_high=4000,s_step=500,capacity=4000,ini_level=4000,num_replications=1000)