# this script creates supply chain networks with increasing number of nodes 
# and measures the time taken to run a single simulation

# local import for testing
import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
import core as scm
import utilities as scm

import simpy
import random
import time
import matplotlib.pyplot as plt
# import SupplyNetPy.Components as scm

class Demand_dist:
    def __init__(self,mean=10,var=5):
        self.mean = mean
        self.var = var

    def gauss(self):
        k = -1
        while(k<0):
            k = int(random.gauss(self.mean, self.var))
        return k 
    
    def uniform(self):
        k = -1
        while(k<0):
            k = int(random.uniform(self.mean-self.var, self.mean+self.var))
        return k
    
    def exponential(self):
        k = -1
        while(k<0):
            k = int(random.expovariate(1/self.mean))
        return k
    
    def constant(self):
        return self.mean

class Inter_arrival_time_dist:
    def __init__(self,lam=1.0):
        self.lam = lam

    def poisson(self):
        return random.expovariate(self.lam)
    
class Lead_time_dist:
    def __init__(self,mean=3,var=2):
        self.mean = mean
        self.var = var

    def gauss(self):
        k = -1
        while(k<0):
            k = random.gauss(self.mean, self.var)
        return k
    
    def uniform(self):
        k = -1
        while(k<0):
            k = random.uniform(self.mean-self.var, self.mean+self.var)
        return k
    
    def exponential(self):
        k = -1
        while(k<0):
            k = random.expovariate(1/self.mean)
        return k
    
# function to generate a supply chain network with n nodes
def generate_supply_chain(n: int, simtime:int) -> dict:
    # decide the number of suppliers, manufacturers, distributors, and retailers
    # Simple Example of Ratios (Generalized for Balanced Networks)
    # - Suppliers to Manufacturers: 3 to 10 suppliers for every manufacturer.
    # - Manufacturers to Warehouses: 1 to 3 warehouses for every manufacturer.
    # - Warehouses to Retailers: 1 to 10 retailers for every warehouse.

    env = simpy.Environment()

    if(n<4):
        print("cannot create with less than 4 nodes!")
        return

    # number of suppliers
    num_suppliers = n // 5
    if(num_suppliers==0):
        num_suppliers = 1
    # number of manufacturers
    num_manufacturers = n // 10
    if(num_manufacturers==0):
        num_manufacturers = 1
    # number of distributors
    num_distributors = n // 7
    if(num_distributors==0):
        num_distributors = 1
    # number of retailers
    num_retailers = n - num_suppliers - num_manufacturers - num_distributors

    nodes = []
    links = []
    demand = []

    for i in range(1, num_suppliers+1):
        ID = "S" + str(i)
        name = "Supplier " + str(i)
        nodes.append(scm.Supplier(env=env, ID=ID, name=name, node_type="infinite_supplier"))

    for i in range(1, num_manufacturers+1):
        ID = "M" + str(i)
        name = "Manufacturer " + str(i)
        capacity = random.randint(500, 800)
        initial_level = random.randint(300, 400)
        inventory_holding_cost = random.randint(1, 3)
        policy_param = [random.randint(300, 400)]
        product_sell_price = random.randint(200, 300)
        nodes.append(scm.Manufacturer(env=env, ID=ID, name=name, 
                                 capacity=capacity, initial_level=initial_level, inventory_holding_cost=inventory_holding_cost, 
                                 replenishment_policy="sS", policy_param=policy_param, product_sell_price=product_sell_price))
        for j in range(0, num_suppliers):
            Id = "Ls" + str(j+1) + "m" + str(i)
            cost = random.randint(1, 3)
            lead_time = Lead_time_dist().gauss
            links.append(scm.Link(env=env,ID=Id, source=nodes[j], sink=nodes[-1], cost=cost, lead_time=lead_time))
        
    for i in range(1, num_distributors+1):
        ID = "D" + str(i)
        name = "Distributor " + str(i)
        capacity = random.randint(300, 500)
        initial_level = random.randint(200, 300)
        inventory_holding_cost = random.randint(2, 4)
        policy_param = [random.randint(200, 250)]
        product_sell_price = random.randint(300, 400)
        nodes.append(scm.InventoryNode(env=env, ID=ID, name=name, node_type="distributor",
                                 capacity=capacity, initial_level=initial_level, inventory_holding_cost=inventory_holding_cost, 
                                 replenishment_policy="sS", policy_param=policy_param, product_sell_price=product_sell_price))
        
        for j in range(num_suppliers, num_suppliers+num_manufacturers):
            Id = "Lm" + str(j+1) + "d" + str(i)
            cost = random.randint(1, 3)
            lead_time = Lead_time_dist().gauss
            links.append(scm.Link(env=env,ID=Id, source=nodes[j], sink=nodes[-1], cost=cost, lead_time=lead_time))
        
    for i in range(1, num_retailers+1):
        ID = "R" + str(i)
        name = "Retailer " + str(i)
        capacity = random.randint(100, 300)
        initial_level = random.randint(50, 100)
        inventory_holding_cost = random.randint(3, 5)
        policy_param = [random.randint(30, 80)]
        product_sell_price = random.randint(400, 500)
        nodes.append(scm.InventoryNode(env=env, ID=ID, name=name, node_type="retailer",
                                 capacity=capacity, initial_level=initial_level, inventory_holding_cost=inventory_holding_cost, 
                                 replenishment_policy="sS", policy_param=policy_param, product_sell_price=product_sell_price))
        
        ID = "demand_" + ID
        name = "Demand " + str(i)
        order_arrival_model = Demand_dist().exponential
        order_quantity_model = Demand_dist().uniform
        demand.append(scm.Demand(env=env,ID=ID, name=name, 
                                 order_arrival_model=order_arrival_model, 
                                 order_quantity_model=order_quantity_model, demand_node=nodes[-1]))
        
        for j in range(num_suppliers+num_manufacturers, num_suppliers+num_manufacturers+num_distributors):
            Id = "Ld" + str(j+1) + "r" + str(i)
            cost = random.randint(1, 3)
            lead_time = Lead_time_dist().gauss
            links.append(scm.Link(env=env,ID=Id, source=nodes[j], sink=nodes[-1], cost=cost, lead_time=lead_time))

    supplynet = {"nodes": nodes, "links": links, "demand": demand}
    time_now = time.time()
    env.run(until=simtime)
    exe_time = time.time() - time_now
    return exe_time

#Following code is to measure the time taken to run a single simulation
num_of_nodes_low = 5
inc_step = 10
num_of_nodes_high = 50
sim_time = 360
num_of_sim_runs = 50

scm.global_logger.disable_logging()

exe_time = []
for N in range(num_of_nodes_low,num_of_nodes_high,inc_step): # run for N number of nodes
    avg_exe_time = 0
    for i in range(0, num_of_sim_runs): # run for num_of_sim_runs times to find average execution time
        avg_exe_time += generate_supply_chain(N,simtime = sim_time)
    exe_time.append([N, avg_exe_time/num_of_sim_runs])

plt.plot([x[0] for x in exe_time], [x[1] for x in exe_time], marker='.', linestyle='-', color='b')
plt.xlabel('Number of Nodes')
plt.ylabel('Execution Time (sec)')
plt.show()