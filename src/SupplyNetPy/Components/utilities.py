import numpy as np
import random
import simpy
import networkx as nx
import matplotlib.pyplot as plt
from SupplyNetPy.Components.core import *

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
        G.add_edge(from_node, to_node, weight=edge.lead_time)

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

    for node in nodes:
        if node["node_type"].lower() == "supplier":
            nodes_instances.append(Supplier(env, **node))
        elif node["node_type"].lower() == "manufacturer":
            nodes_instances.append(Manufacturer(env, **node))
        elif node["node_type"].lower() == "distributor":
            nodes_instances.append(InventoryNode(env, **node))
        elif node["node_type"].lower() == "retailer":
            nodes_instances.append(InventoryNode(env, **node))
        else:
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
        links_instances.append(Link(env,link['ID'],source,sink,link['cost'],link['lead_time']))

    for d in demand:
        demand_node = None
        for node in nodes_instances:
            if node.ID == d["demand_node"]:
                demand_node = node
        if(demand_node is None):
            global_logger.logger.error(f"Invalid demand node {d['demand_node']}")
            raise ValueError("Invalid demand node")
        demand_instances.append(Demand(env,d['ID'],d['name'],d['order_arrival_model'],d['order_quantity_model'],demand_node))

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
    
    logger.info("*** Supply chain statistics ***")
    logger.info(f"Number of products sold = {sc_total_unit_sold}") 
    logger.info(f"SC total profit = {sc_net_profit}") 
    logger.info(f"SC total tranportation cost = {sc_net_transport_cost}") 
    logger.info(f"SC total cost = {sc_net_node_cost}")
    logger.info(f"SC inventory cost = {sc_net_inventory_cost}") 
    logger.info(f"Customers returned  = {sc_total_unsatisfied_demand}")
    
    return supplychainnet

if __name__ == "__main__": 
    
    # nodes input as netlist
    # ID, name, node_type, capacity, initial_level, inventory_holding_cost, replenishment_policy, policy_parameters
    nodes = [{'ID': 'S1', 'name': 'Supplier 1', 'node_type': 'supplier', 'capacity': 600, 'initial_level': 600, 'inventory_holding_cost': 0.2},
             {'ID': 'M1', 'name': 'Manufacturer 1', 'node_type': 'manufacturer', 'capacity': 300, 'initial_level': 200, 'inventory_holding_cost': 0.5, 'replenishment_policy': 'sS', 'policy_param': [150]},
             {'ID': 'D1', 'name': 'Distributor 1', 'node_type': 'distributor', 'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 1, 'replenishment_policy': 'sS', 'policy_param': [40]}
    ]
    
    # nodes input as netlist
    # ID, from_node, to_node, transportation_cost, lead_time
    links = [{'ID': 'L1', 'source': 'S1', 'sink': 'M1', 'cost': 5, 'lead_time': 3},
             {'ID': 'L2', 'source': 'M1', 'sink': 'D1', 'cost': 5, 'lead_time': 2}
    ]
    
    # demands input as netlist
    # ID, name, node_type, order_arrival_model, order_quantity_model, demand_node
    demands = [{'ID': 'demand_D1', 'name': 'Demand 1', 'node_type': 'demand', 'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 30, 'demand_node': 'D1'}]

    global_logger.enable_logging()
    supplychainnet = simulate_sc_net(create_sc_net(nodes, links, demands), sim_time=30)
    visualize_sc_net(supplychainnet)
    
    for node in supplychainnet["nodes"]:
        global_logger.logger.info(node.get_info())