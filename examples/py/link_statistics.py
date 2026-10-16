import random
import SupplyNetPy.Components as scm

scm.set_seed(7)
rng = random.Random(7)

# nodes
supplier = {'ID': 'S1', 'name': 'Supplier1', 'node_type': 'infinite_supplier'}

distributor1 = {'ID': 'D1', 'name': 'Distributor1', 'node_type': 'distributor',
                'capacity': 300, 'initial_level': 150, 'inventory_holding_cost': 0.1,
                'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': 120, 'S': 300},
                'product_buy_price': 90, 'product_sell_price': 100}

distributor2 = {'ID': 'D2', 'name': 'Distributor2', 'node_type': 'distributor',
                'capacity': 150, 'initial_level': 80, 'inventory_holding_cost': 0.1,
                'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': 40, 'S': 150},
                'product_buy_price': 90, 'product_sell_price': 100}

retailer = {'ID': 'R1', 'name': 'Retailer1', 'node_type': 'retailer',
            'capacity': 120, 'initial_level': 60, 'inventory_holding_cost': 0.2,
            'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': 50, 'S': 120},
            'product_buy_price': 100, 'product_sell_price': 120,
            'supplier_selection_policy': scm.SelectCheapest}

# links (the cheaper link from D1 is disrupted now and then, D2 restocks slowly)
links = [{'ID': 'L1', 'source': 'S1', 'sink': 'D1', 'cost': 20, 'lead_time': lambda: 3},
         {'ID': 'L2', 'source': 'S1', 'sink': 'D2', 'cost': 20, 'lead_time': lambda: 8},
         {'ID': 'L3', 'source': 'D1', 'sink': 'R1', 'cost': 5, 'lead_time': lambda: 2,
          'link_failure_p': 0.05, 'link_recovery_time': lambda: 4},
         {'ID': 'L4', 'source': 'D2', 'sink': 'R1', 'cost': 8, 'lead_time': lambda: 1}]

# customer demand
demand = {'ID': 'd1', 'name': 'Demand1', 'demand_node': 'R1', 'tolerance': 2,
          'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: rng.randint(5, 20)}

supplychainnet = scm.create_sc_net(nodes=[supplier, distributor1, distributor2, retailer],
                                   links=links, demands=[demand])

# warm-up, reset, then the measured period
scm.simulate_sc_net(supplychainnet, sim_time=30, logging=False)
scm.reset_stats(supplychainnet)
scm.simulate_sc_net(supplychainnet, sim_time=230, logging=False)

# one link
L3 = supplychainnet["links"]["L3"]
print(L3.stats.get_statistics())

# what R1 ordered, and from whom
R1 = supplychainnet["nodes"]["R1"]
scm.print_link_wise_performance(R1.suppliers)

# who ordered from S1
S1 = supplychainnet["nodes"]["S1"]
scm.print_link_wise_performance(S1.buyers)
