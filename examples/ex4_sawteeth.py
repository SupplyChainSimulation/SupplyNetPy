# this script creates supply chain networks with increasing number of nodes 
# and measures the time taken to run a single simulation
import simpy
import random
import time
import matplotlib.pyplot as plt
import SupplyNetPy.Components as scm

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

    supplynet = {"nodes": nodes, "edges": links, "demand": demand}
    #print(supplynet)
    #scm.global_logger.disable_logging()
    env.run(until=simtime)
    return supplynet

# Following code is to plot inventory levels for all nodes in the supply chain network
# this is to observe if the model is working as expected
# sawtooth pattern should be observed for all nodes
N = 10
scm.global_logger.disable_logging()
supplynet = generate_supply_chain(N,simtime = 1000)

# plotting inventory levels for all nodes
num_suppliers = 0
for i in supplynet["nodes"]:
    if(i.node_type == "infinite_supplier"):
        num_suppliers += 1
num_nodes = len(supplynet["nodes"]) - num_suppliers
fig, axs = plt.subplots(num_nodes)
i = 0
colors = ['red','green','blue','yellow','black','orange','purple','brown','pink','gray']
for node in supplynet["nodes"]:
    if(node.node_type != "infinite_supplier"):
        axs[i].plot(node.inventory.inventory.timedata, node.inventory.inventory.leveldata, label=node.ID, marker='.', color=colors[i%len(colors)])
        axs[i].axhline(y=node.policy_param[0], color='r', linestyle='--',label=f's = {node.policy_param[0]}')  
        i += 1
fig.legend()
plt.show()

scm.visualize_sc_net(supplynet)