import SupplyNetPy.Components as scm

raw_mat1 = scm.RawMaterial(ID='rm1', name='raw_mat1', extraction_quantity=1000,
                           extraction_time=1, mining_cost=0.5, cost=0.8)

supplier1 = {'ID':'S1', 'name':'supplier1', 'node_type':'supplier', 'capacity':5000,
            'initial_level':5000, 'inventory_holding_cost':0.01, 'raw_material':raw_mat1}

product1 = scm.Product(ID='p1', name='product1', manufacturing_cost=20, manufacturing_time=1, 
                       batch_size=1000, raw_materials=[(raw_mat1, 2)], sell_price=30)

factory1 = {'ID':'F1', 'name':'factory1', 'node_type':'factory', 
            'capacity':2500, 'initial_level':2500, 'inventory_holding_cost':0.02, 
            'replenishment_policy':scm.SSReplenishment, 'policy_param': {'s':1000,'S':2500},
            'product':product1, 'product_sell_price':30}

distributor1 = {'ID': 'D1', 'name': 'Distributor1', 'node_type': 'distributor', 
                'capacity': 1000, 'initial_level': 1000, 'inventory_holding_cost': 0.2, 
                'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s':300,'S':1000},
                'product_buy_price':30,'product_sell_price': 35}

links1f1 = {'ID': 'L1', 'source': 'S1', 'sink': 'F1', 'cost': 100, 'lead_time': lambda: 2}

linkf1d1 = {'ID': 'L2', 'source': 'F1', 'sink': 'D1', 'cost': 120, 'lead_time': lambda: 3}

demand1 = {'ID': 'd1', 'name': 'Demand1', 'order_arrival_model': lambda: 0.4,
           'order_quantity_model': lambda: 30, 'demand_node': 'D1'}

supplychainnet = scm.create_sc_net(nodes=[supplier1, factory1, distributor1], 
                                   links=[links1f1, linkf1d1], demands=[demand1])

supplychainnet = scm.simulate_sc_net(supplychainnet, sim_time=20, logging=True)