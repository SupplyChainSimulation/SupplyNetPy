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

 T = number of days
 l = deterministic lead time
 e = shelf life of the drugs (months)
 R = number of simulation replication
 b = shortage cost
 z = waste cost
 h = holding cost
 o = ordering cost
 dt = demand on day t (stochastic)
 yt = binary variable for supply disruption status (yt=0 disrupted, yt=1 available) (stochastic)

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

class Distributions:
    def __init__(self,mu,lam):
        self.mu = mu
        self.lam = lam

    def poisson_demand(self):
        return np.random.poisson(self.lam)

    def expo_arrival(self):
        return np.random.exponential(self.mu)

class PerishableInventory(scm.Inventory):
    def __init__(self, env: simpy.Environment, capacity: int, initial_level: int, replenishment_policy: str) -> None:
        super().__init__(env, capacity, initial_level, replenishment_policy)
        self.waste = []
        self.inventory_position = self.inventory.level
        self.env.process(self.remove_expired_drugs())

    def remove_expired_drugs(self):
        while True:
            yield self.env.timeout(30)
            # all drugs in the inventory are expired at the end of the month
            self.waste.append(self.inventory.level)
            self.inventory.get(self.inventory.level)
            if(self.inventory_position >= self.inventory.level):
                self.inventory_position -= self.inventory.level


st = Distributions(mu=0.5,lam=10)
env = simpy.Environment()

# create an infinite supplier
supplier1 = scm.Supplier(env=env, ID="S1", name="Supplier 1", node_type="infinite_supplier")

#create the distributor
distributor1 = scm.InventoryNode(env=env, ID="D1", name="Distributor 1", node_type="distributor",
                                 capacity=2000, initial_level=1000, inventory_holding_cost=1, 
                                 replenishment_policy="sS", policy_param=[1500], product_sell_price=360)
# set perishable inventory for it
distributor1.inventory = PerishableInventory(env=env, capacity=2000, initial_level=1000, replenishment_policy="sS")

# set demand
demand1 = scm.Demand(env=env,ID="d1", name="demand 1", 
                    order_arrival_model=st.expo_arrival, 
                    order_quantity_model=st.poisson_demand, demand_node=distributor1)
# link the nodes
link1 = scm.Link(env=env,ID="l1", source=supplier1, sink=distributor1, cost=5, lead_time=lambda: 1)
# create a sc net
supplynet = {"nodes": [supplier1,distributor1], "links": [link1], "demand": [demand1]}

# run the simulation
env.run(until=360)