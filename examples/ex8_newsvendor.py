import simpy
import random
import numpy as np
import SupplyNetPy.Components as scm
import matplotlib.pyplot as plt

# Parameters for the normal distribution
mean = 100
std_dev = 15
num_samples = 1000

cost = 2
sell_price = 5
salvage = 1
cost_arr = []
profit_arr = []

order_quantity = 100

cost_arr = []
profit_arr = []

def normal_quantity():
    sample = random.gauss(mean, std_dev)
    while(sample<0):
        sample = random.gauss(mean, std_dev)
    return sample

for order_quantity in range(20, 190, 10):
    env = simpy.Environment()

    # create an infinite supplier
    supplier1 = scm.Supplier(env=env, ID="S1", name="Supplier1", node_type="infinite_supplier")

    #create the distributor
    newsvendor1 = scm.InventoryNode(env=env, ID="D1", name="News Vendor", node_type="distributor",
                                    capacity=order_quantity, initial_level=order_quantity, inventory_holding_cost=0.1,
                                    inventory_type="perishable", shelf_life=1.00001, replenishment_policy=scm.PeriodicReplenishment,
                                    policy_param={"T": 1, "Q": order_quantity}, product_sell_price=sell_price, 
                                    product_buy_price=cost)

    link1 = scm.Link(env=env,ID="l1", source=supplier1, sink=newsvendor1, cost=10, lead_time=lambda: 0)
    
    demand1 = scm.Demand(env=env,ID="d1", name="demand_d1", 
                        order_arrival_model=lambda: 1, consume_available=True,
                        order_quantity_model=normal_quantity, demand_node=newsvendor1)

    scm.global_logger.disable_logging()
    env.run(until=num_samples)

    # Calculate the cost and profit
    # total demand fulfilled by newsvendor is available in variable demand_fulfilled
    # list element 0 is number of orders, element 1 is total quantity
    daily_sales = newsvendor1.stats.demand_fulfilled[1] 
    wasted_inventory = newsvendor1.inventory.waste
    everyday_profit = (daily_sales*sell_price + wasted_inventory*salvage - order_quantity*num_samples*cost)/num_samples
    profit_arr.append([order_quantity,everyday_profit])

profit_arr = np.array(profit_arr)
Q = np.argmax(profit_arr[:,1])
plt.plot(profit_arr[:,0], profit_arr[:,1], marker='.', linestyle='-', color='b')
plt.plot(profit_arr[Q,0], profit_arr[Q,1], marker='o', linestyle='-', color='r', label=f'Q={profit_arr[Q,0]}')
plt.xlabel('Order Quantity')
plt.ylabel('Profit')
plt.title('Profit vs Order Quantity')
plt.legend()
plt.grid()
plt.show()