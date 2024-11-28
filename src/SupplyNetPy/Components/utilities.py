import simpy
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
#from SupplyNetPy.Components.core import *
# Local import
import sys, os
sys.path.insert(1, 'src/SupplyNetPy/Components')
from core import *

def visualize_sc_net(supplychainnet):
    """
    Visualize the supply chain network as a graph.

    Parameters:
        supplychainnet (dict): The supply chain network containing nodes and edges.

    Returns:
        None
    """
    G = nx.Graph()
    nodes = supplychainnet["nodes"]
    edges = supplychainnet["edges"]

    # Add nodes to the graph
    for node in nodes:
        G.add_node(node.ID, level=node.node_type)

    # Add edges to the graph
    for edge in edges:
        from_node = edge.source.ID
        to_node = edge.sink.ID
        G.add_edge(from_node, to_node, weight=edge.lead_time())

    # Generate the layout of the graph
    pos = nx.spring_layout(G)

    # Draw the graph
    nx.draw(G, pos, node_color='#CCCCCC', with_labels=True)

    # Add edge labels
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)

    # Set the title and display the graph
    plt.title("Supply chain network")
    plt.show()

def get_sc_net_info(supplychainnet):
    """
    Get supply chain network information. 

    This function displays the following information about the supply chain network:
    - Number of nodes
    - Number of edges
    - Number of suppliers
    - Number of manufacturers
    - Number of distributors
    - Number of retailers
    - Node parameters
    - Edge parameters
    - Demand
    - Products

    Parameters: 
        supplychainnet (dict): A dictionary representing the supply chain network.

    Returns:
        str: A string containing the supply chain network information.
    """
    sc_info = "Supply chain configuration: \n"
    logger = global_logger.logger
    logger.info(f"Number of nodes in the network: {supplychainnet['num_of_nodes']}") 
    logger.info(f"Number of edges in the network: {supplychainnet['num_of_edges']}") 
    logger.info(f"\t Number of suppliers: {supplychainnet['num_suppliers']}") 
    logger.info(f"\t Number of manufacturers: {supplychainnet['num_manufacturers']}") 
    logger.info(f"\t Number of distributors: {supplychainnet['num_distributors']}") 
    logger.info(f"\t Number of retailers: {supplychainnet['num_retailers']}") 
    
    sc_info += f"Number of nodes in the network: {supplychainnet['num_of_nodes']} \n Number of edges in the network: {supplychainnet['num_of_edges']} \n Number of suppliers: {supplychainnet['num_suppliers']} \n Number of manufacturers: {supplychainnet['num_manufacturers']} \n Number of distributors: {supplychainnet['num_distributors']} \n Number of retailers: {supplychainnet['num_retailers']}"
    for node in supplychainnet["nodes"]:
        sc_info += node.get_info()
    for link in supplychainnet["edges"]:
        sc_info += link.get_info()
    for demand in supplychainnet["demand"]:
        sc_info += demand.get_info()
    sc_info += "\nSupply chain performance: \n"
    logger.info(f"Supply chain performance: \n") 
    if("performance" in supplychainnet):
        logger.info(f"Number of products sold = {supplychainnet['total_product_sold']}") 
        logger.info(f"SC total profit = {supplychainnet['sc_profit']}") 
        logger.info(f"SC total tranportation cost = {supplychainnet['sc_tranport_cost']}")
        logger.info(f"SC inventory cost = {supplychainnet['sc_inv_cost']}") 
        logger.info(f"SC revenue (profit - cost) = {supplychainnet['sc_revenue']}") 
        logger.info(f"Average revenue (per day) = {supplychainnet['avg_revenue']}") 
        logger.info(f"Customers returned  = {supplychainnet['total_customer_returned']}") 
    
        sc_info += f"Number of products sold = {supplychainnet['total_product_sold']}  \n SC total profit = {supplychainnet['sc_profit']}  \n SC total tranportation cost = {supplychainnet['sc_tranport_cost']}  \n SC inventory cost = {supplychainnet['sc_inv_cost']}  \n SC revenue (profit - cost) = {supplychainnet['sc_revenue']}  \n Average revenue (per day) = {supplychainnet['avg_revenue']}  \n Customers returned  = {supplychainnet['total_customer_returned']}"
    return sc_info

def create_sc_net(nodes: list, links: list, demand: list):
    """
    This functions inputs the nodes, links and demand netlists and creates supply chain nodes, links and demand objects. 
    It then creates a supply chain network by putting all the objects in a dictionary.

    Parameters:
        nodes (list): A netlist of nodes in the supply chain network.
        links (list): A netlist of links between the nodes.
        demand (list): A netlist of demand nodes in the supply chain network.

    Returns:
        dict: A dictionary representing the supply chain network.
    """
    # create simpy environment
    env = simpy.Environment()
    nodes_instances = []
    links_instances = []
    demand_instances = []
    used_ids = []

    for node in nodes:
        if(node["ID"] in used_ids):
            global_logger.logger.error(f"Duplicate node ID {node['ID']}")
            raise ValueError("Invalid node type")
        used_ids.append(node["ID"])
        if node["node_type"].lower() == "supplier" or node["node_type"].lower() == "infinite_supplier":
            nodes_instances.append(Supplier(env=env, **node))
        elif node["node_type"].lower() == "manufacturer":
            # excluding key 'node_type', since it is not required for Manufacturer class
            node_ex = {key: node[key] for key in node if key != 'node_type'}
            nodes_instances.append(Manufacturer(env=env, **node_ex))
        elif node["node_type"].lower() == "distributor" or node["node_type"].lower() == "warehouse":
            nodes_instances.append(InventoryNode(env=env, **node))
        elif node["node_type"].lower() == "retailer":
            nodes_instances.append(InventoryNode(env=env, **node))
        else:
            used_ids.remove(node["ID"])
            global_logger.logger.error(f"Invalid node type {node['node_type']}")
            raise ValueError("Invalid node type")
    
    for link in links:
        source = None
        sink = None
        for node in nodes_instances:
            if node.ID == link["source"]:
                source = node
            if node.ID == link["sink"]:
                sink = node
        if(source is None or sink is None):
            global_logger.logger.error(f"Invalid source or sink node {link['source']} {link['sink']}")
            raise ValueError("Invalid source or sink node")
        links_instances.append(Link(env=env,ID=link['ID'],source=source,sink=sink,link['cost'],link['lead_time']))

    for d in demand:
        # check for which node the demand is
        demand_node = None
        for node in nodes_instances:
            if node.ID == d["demand_node"]:
                demand_node = node
        if(demand_node is None):
            global_logger.logger.error(f"Invalid demand node {d['demand_node']}")
            raise ValueError("Invalid demand node")
        demand_instances.append(Demand(env=env,ID=d['ID'],name=d['name'],order_arrival_model=d['order_arrival_model'],
                                       order_quantity_model=d['order_quantity_model'],demand_node=demand_node))

    supplychainnet = {
        "env":env,
        "nodes": nodes_instances,
        "edges": links_instances,
        "demand": demand_instances,
        "num_of_nodes": len(nodes),
        "num_of_edges": len(links),
    }
    return supplychainnet

def simulate_sc_net(supplychainnet, sim_time):
    """
    Simulate the supply chain network for a given time period.

    Parameters:
        supplychainnet (dict): A supply chain network.
        sim_time (int): Simulation time.
        env (SimPy Environment variable): SimPy Environment variable.

    Returns:
        supplychainnet (dict): Updated dict with listed performance measures.
    """
    logger = global_logger.logger

    env = supplychainnet["env"]
    demands = supplychainnet["demand"]
    nodes = supplychainnet["nodes"]

    # Let's create some variables to store stats
    sc_net_inventory_cost = 0
    sc_net_transport_cost = 0
    sc_net_node_cost = 0
    sc_net_profit = 0
    sc_total_unit_sold = 0
    sc_total_unsatisfied_demand = 0
    
    # Run the simulation
    env.run(sim_time)

    # Calculate stats
    for node in nodes:
        sc_net_inventory_cost += node.inventory_cost
        sc_net_transport_cost += node.transportation_cost
        sc_net_node_cost += node.node_cost
        sc_net_profit += node.net_profit
    
    for demand in demands:
        sc_total_unit_sold += demand.total_products_sold
        sc_total_unsatisfied_demand += demand.unsatisfied_demand
    
    supplychainnet["performance"] = {
        "total_product_sold": sc_total_unit_sold,
        "sc_profit": sc_net_profit,
        "sc_tranport_cost": sc_net_transport_cost,
        "sc_inv_cost": sc_net_inventory_cost,
        "sc_total_cost": sc_net_node_cost,
        "total_unsatisfied_demand": sc_total_unsatisfied_demand
    }
    
    logger.info("\nSupply chain performance:")
    logger.info(f"Number of products sold = {sc_total_unit_sold}") 
    logger.info(f"SC total profit = {sc_net_profit}") 
    logger.info(f"SC total tranportation cost = {sc_net_transport_cost}") 
    logger.info(f"SC total cost = {sc_net_node_cost}")
    logger.info(f"SC inventory cost = {sc_net_inventory_cost}") 
    logger.info(f"Unsatisfied demand  = {sc_total_unsatisfied_demand}")
    
    return supplychainnet

if __name__ == "__main__": 
    
    # ID, name, node_type, capacity, initial_level, inventory_holding_cost, replenishment_policy, policy_parameters
    nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'infinite_supplier', 'raw_material': default_raw_material},
             {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 300, 'initial_level': 200, 'inventory_holding_cost': 0.5, 'replenishment_policy': 'sS', 'policy_param': [200],'product_sell_price': 350},
             {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 1, 'replenishment_policy': 'sS', 'policy_param': [100],'product_sell_price': 360}
    ]
    
    # ID, from_node, to_node, transportation_cost, lead_time
    links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': lambda: 3},
             {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}
    ]
    
    # ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
    demands = [{'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10, 'demand_node': 'D1'}]

    # enable/disable logging
    global_logger.enable_logging()
    
    # create the supply chain model and visualize it
    supplychainnet = create_sc_net(nodes, links, demands)
    visualize_sc_net(supplychainnet)

    # get the supply chain network information
    for node in supplychainnet["nodes"]:
        str_details = ""
        for key, value in node.get_info().items():
            str_details += f"{key}: {value}, "
        global_logger.logger.info(f"{node}: {str_details}\n")
    
    # simulate the supply chain model
    supplychainnet = simulate_sc_net(supplychainnet, sim_time=60)

    # lets plot inventory levels for each node
    for node in supplychainnet["nodes"]:
        # get level data and timedata from the inventory
        levels = np.array((node.inventory.instantaneous_levels))
        # check if it is not a supplier and has a replenishment policy
        if("supplier" not in node.node_type and node.policy_param != []):
            if(node.replenishment_policy == 'sS'): # check if it is sS policy, plot threshold line s
                s = node.policy_param[0]    
                plt.axhline(y=s, color='r', linestyle='--',label='s (sS replenish)')    
            plt.title(f"Inventory Level for {node.ID}")
            plt.plot(levels[:,0], levels[:,1], label=node.ID, marker='.', linestyle='-')
            plt.xlabel("Time")
            plt.ylabel("Inventory Level")
            plt.legend()
            plt.show()