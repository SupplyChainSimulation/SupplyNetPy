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

class Distributions:
    """
    Class to generate random numbers for demand (order quantity) and order arrival arrival times.
    Parameters:
        mu (float): Mean of the exponential distribution for order arrival times.
        lam (float): Lambda parameter of the Poisson distribution for demand (order quantity).        
    """
    def __init__(self,mu=1,lam=1,p=0.01):
        self.mu = mu
        self.lam = lam
        self.p = p

    def poisson_demand(self):
        return np.random.poisson(self.lam)

    def expo_arrival(self):
        return np.random.exponential(self.mu)
    
    def geometric(self):
        return np.random.geometric(self.p,1)[0]

def manufacturer_date_cal(time_now):
    """
    Function to calculate the manufacture date based on the current time.
    Parameters:
        time_now (int): Current time in days.
    """
    man_dt = time_now - (time_now % 30)  # round down to the nearest month
    return man_dt

# Global parameters
T = 360     #number of days (360 days)
l = 6       #deterministic lead time (6 days)
e = 90      #shelf life of the drugs (months) (3 months)
R = 5000    #number of simulation replication (5000)
b = 5       #shortage cost (5 units)
z = 1       #waste cost (1 units)
h = 0.001   #holding cost (0.001 units)
o = 0.5     #ordering cost (0.5 units)
dt = 25     #demand on day t (stochastic) (Poission 25/day)
# yt = binary variable for supply disruption status on day t (yt=0 disrupted, yt=1 available) (stochastic) (p=0.01)
yt_p = 0.01  # ~ Geometric(p=0.01), sampled from Geometric distribution with probability p = 0.01
# node recovery time ~ Geometric(p=1/30), sampled from Geometric distribution with probability p = 1/30 = 0.033

def single_sim_run(S,s,ini_level):
    """
    Function to run a single simulation with given parameters.
    Parameters:
        S (int): Capacity of the distributor.
        s (int): Reorder point for the distributor.
        ini_level (int): Initial inventory level at the distributor.
    """
    st = Distributions(mu=1,lam=dt)
    disrupt_time = Distributions(p=0.01)
    recovery_time = Distributions(p=1/30)
    # create the environment
    env = simpy.Environment()

    # create an infinite supplier
    supplier1 = scm.Supplier(env=env, ID="S1", name="Supplier 1", node_type="infinite_supplier", 
                             node_disrupt_time=disrupt_time.geometric, node_recovery_time=recovery_time.geometric)

    #create the distributor
    distributor1 = scm.InventoryNode(env=env, ID="D1", name="Distributor 1", node_type="distributor",
                                    capacity=S, initial_level=ini_level, inventory_holding_cost=h, inventory_type="perishable",
                                    manufacture_date = manufacturer_date_cal,
                                    shelf_life=e, replenishment_policy="sS", policy_param=[s], product_sell_price=350)
    link1 = scm.Link(env=env,ID="l1", source=supplier1, sink=distributor1, cost=o, lead_time=lambda: l) # link the nodes
    # set demand
    demand1 = scm.Demand(env=env,ID="d1", name="demand 1", 
                        order_arrival_model=lambda:1, # every day
                        order_quantity_model=st.poisson_demand, demand_node=distributor1,
                        tolerance=0.2)
    scm.global_logger.enable_logging() # enable logging
    env.run(until=360) # run the simulation
    # calculate the costs
    instantaneous_levels = np.array(distributor1.inventory.instantaneous_levels)
    instantaneous_levels = instantaneous_levels[instantaneous_levels[:,0]>30] # discard first 30 days data
    if(distributor1.transportation_cost):
        transportation_cost = np.array(distributor1.transportation_cost)
        transportation_cost = transportation_cost[transportation_cost[:,0]>30]
    else:
        transportation_cost = np.array([[0,0]])
    if(distributor1.inventory.inventory.waste):
        waste_arr = np.array(distributor1.inventory.inventory.waste)
        waste_arr = waste_arr[waste_arr[:,0]>30]
    else:
        waste_arr = np.array([[0,0]])
    if(demand1.shortage):
        shortage_arr = np.array(demand1.shortage)
        shortage_arr = shortage_arr[shortage_arr[:,0]>30]
    else:
        shortage_arr = np.array([[0,0]])
    
    print("Shortage cost: ", sum(shortage_arr[:,1]))
    print("Waste cost: ", sum(waste_arr[:,1]))
    print("Holding Cost: ", sum(instantaneous_levels[:,1]))
    print("Transportation Cost: ",transportation_cost[:,1])
    print("Total Cost: ", (sum(shortage_arr[:,1])*b + sum(waste_arr[:,1])*z + sum(instantaneous_levels[:,1])*h + sum(transportation_cost[:,1]))/((T-30)))#*(b+z+h+o)

def run_for_s(s_low,s_high,s_step,capacity,ini_level,num_replications):
    """ Function to run the simulation for a range of reorder points with given number of replications.
    Parameters:
        s_low (int): Lower bound for the reorder point.
        s_high (int): Upper bound for the reorder point.
        s_step (int): Step size for the reorder point.
        capacity (int): Inventory capacity of the distributor.
        ini_level (int): Initial inventory level at the distributor.
        num_replications (int): Number of replications to run for each reorder point.
    """
    st = Distributions(mu=1,lam=25)
    disrupt_time = Distributions(p=0.01)
    recovery_time = Distributions(p=1/30)
    R = num_replications # number of replications
    exp_cost_per_day = []
    for reorder_point in range(s_low,s_high,s_step):
        # initialize the costs
        shortage_cost = 0 
        waste_cost = 0 
        holding_cost = 0 
        ordering_cost = 0 
        exp_cost_arr = []
        for i in range(0,R):
            env = simpy.Environment()
            supplier1 = scm.Supplier(env=env, ID="S1", name="Supplier 1", node_type="infinite_supplier", 
                                    node_disrupt_time=disrupt_time.geometric, node_recovery_time=recovery_time.geometric)
            distributor1 = scm.InventoryNode(env=env, ID="D1", name="Distributor 1", node_type="distributor", capacity=capacity, 
                                             initial_level=ini_level, inventory_holding_cost=h, manufacture_date = manufacturer_date_cal,
                                             inventory_type="perishable", shelf_life=e, replenishment_policy="sS", 
                                             policy_param=[reorder_point], product_sell_price=350)
            link1 = scm.Link(env=env,ID="l1", source=supplier1, sink=distributor1, cost=o, lead_time=lambda: l)
            demand1 = scm.Demand(env=env,ID="d1", name="demand 1", order_arrival_model=lambda:1, 
                                order_quantity_model=st.poisson_demand, demand_node=distributor1, tolerance=0.2)
            scm.global_logger.disable_logging()
            env.run(until=360) # run the simulation

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
            if(distributor1.transportation_cost):
                transportation_cost_arr = np.array(distributor1.transportation_cost)
                transportation_cost_arr = transportation_cost_arr[transportation_cost_arr[:,0]>30]
            else:
                transportation_cost_arr = np.array([[0,0]])
            instantaneous_levels = np.array(distributor1.inventory.instantaneous_levels)

            shortage_cost = sum(shortage_arr[:,1]) # b = 5 units
            waste_cost = sum(waste_arr[:,1]) # z = 1 units
            holding_cost = sum(instantaneous_levels[29:,1]) # h = 0.001 units
            ordering_cost = sum(transportation_cost_arr[:,1]) # o = 0.5 units

            exp_cost = (shortage_cost*b + waste_cost*z + holding_cost*h + ordering_cost)/((T-30)*(b+z+h+o))
            exp_cost_arr.append(exp_cost)

        exp_cost_per_day.append((reorder_point, sum(exp_cost_arr)/R))
        
    return exp_cost_per_day

single_sim_run(S=5000,s=4000,ini_level=5000)
#exp_cost_per_day = run_for_s(s_low=10,s_high=11,s_step=2,capacity=5000,ini_level=5000,num_replications=500)