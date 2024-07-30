from SupplyNetPy.Components.core import *
import numpy as np
import random
import networkx as nx
import matplotlib.pyplot as plt

def create_sc_nodes(num_of_nodes,node_type,inv_cap_bounds,inv_hold_cost_bounds,inv_reorder_lvl_bounds,product=default_product,env=env):
    """
    Creates number of nodes of given node type
    Parameters:
    - env: SimPy Environment variable
    - num_of_node (int): number of nodes to be created
    - node_type (str): type of node to be created
    - inv_cap_bounds (list): Inventory capacity lower and upper bounds 
    - inv_hold_cost_bounds (list): Inventory holding cost  lower and upper bounds 
    - inv_reorder_lvl_bounds (list): Inventory reorder level lower and upper bounds 
    - product (Product): Product in the inventory
    Return:
    - nodes (list): list of objects (supply chain nodes) that are created
    """
    nodes = []
    for i in range(0,num_of_nodes):
        id = random.randint(0,100) # any random ID
        inv_capacity = random.randint(inv_cap_bounds[0],inv_cap_bounds[1]) # choose an integer in given bounds
        inv_hold_cost = random.randint(inv_hold_cost_bounds[0],inv_hold_cost_bounds[1])
        inv_reorder_lvl = random.randint(inv_reorder_lvl_bounds[0],inv_reorder_lvl_bounds[1])
        if(node_type.lower()=="supplier"):
            node = Supplier(ID=f"S{id}", name="Supplier", capacity=inv_capacity, initial_level=inv_capacity, inventory_holding_cost=inv_hold_cost, product=product)
            nodes.append(node)
        elif(node_type.lower()=="manufacturer"):
            node = Manufacturer(ID=f"M{id}", name="Manufacturer", capacity=inv_capacity, initial_level=inv_capacity, inventoty_holding_cost=inv_hold_cost, replenishment_policy="sS", policy_param=[inv_reorder_lvl],product=product)
            nodes.append(node)
        elif(node_type.lower()=="distributor" or node_type.lower()=="warehouse"):
            node = InventoryNode(ID=f"D{id}", name="Distributor", node_type="distributor", capacity=inv_capacity, initial_level=inv_capacity, inventory_holding_cost=inv_hold_cost, replenishment_policy="sS", policy_param=[inv_reorder_lvl],product=product)
            nodes.append(node)
        elif(node_type.lower()=="retailer"):
            node = InventoryNode(ID=f"R{id}", name="Retailer", node_type="retailer", capacity=inv_capacity, initial_level=inv_capacity, inventory_holding_cost=inv_hold_cost, replenishment_policy="sS", policy_param=[inv_reorder_lvl],product=product)
            nodes.append(node)
    return nodes

def create_sc_links(from_nodes,to_nodes,lead_time_bounds,tranport_cost_bounds,link_dist_bounds):
    """
    Creates links from each node in from_nodes list to every other node in to_nodes list.
    Parameters:
    - from_nodes (list): List of nodes 
    - to_nodes (list): List of nodes 
    - lead_time_bounds (list): Upper and lower bounds on the lead time of these links
    - tranport_cost_bounds (list): Upper and lower bounds on the tranportation cost
    - link_dist_bounds (list): Upper and lower bounds on the distance
    Returns:
    - links (list): List of links created in the SC network
    """
    links = []
    for source in from_nodes:
        for sink in to_nodes:
            id = random.randint(0,100) # any random ID
            lead_time = random.randint(lead_time_bounds[0],lead_time_bounds[1])
            tranport_cost = random.randint(tranport_cost_bounds[0],tranport_cost_bounds[1])
            link = Link(ID=f"L{id}", source=source, sink=sink, cost=tranport_cost, lead_time=lead_time)
            links.append(link)
    return(links)

def create_random_sc_net(num_suppliers,num_manufacturers,num_distributors,num_retailers,env=env,product=default_product):
    """
    This function creates a fully connected random SC network
    Parameters:
    - num_suppliers (int): number of suppliers
    - num_manufacturers (int): number of manufacturers
    - num_distributors (int): number of distributors
    - num_retailers (int): number of retailers
    """
    # To - Do #
    # get bounds for node/edge parameters as as attributes

    # create a product
    if(num_suppliers!=0):
        suppliers = create_sc_nodes(num_of_nodes=num_suppliers,node_type="supplier",inv_cap_bounds=[800,900],
                                     inv_hold_cost_bounds=[1,3],inv_reorder_lvl_bounds=[700,750],product=default_product)
    if(num_manufacturers!=0):
        manufacturers = create_sc_nodes(num_of_nodes=num_manufacturers,node_type="manufacturer",inv_cap_bounds=[600,700],
                                         inv_hold_cost_bounds=[2,4],inv_reorder_lvl_bounds=[400,500],product=default_product)
    else:
        raise ValueError(f"number of manufacturers can not be zero!")
    
    if(num_distributors!=0):
        distributors = create_sc_nodes(num_of_nodes=num_distributors,node_type="distributor",inv_cap_bounds=[300,400],
                                         inv_hold_cost_bounds=[3,5],inv_reorder_lvl_bounds=[200,250],product=default_product)
    if(num_retailers!=0):
        retailers = create_sc_nodes(num_of_nodes=num_retailers,node_type="retailer",inv_cap_bounds=[100,200],
                                         inv_hold_cost_bounds=[5,9],inv_reorder_lvl_bounds=[50,100],product=default_product)
    else:
        raise ValueError(f"Number of retailers cannot be zero!")
    
    edges = []
    
    # create links
    if(num_suppliers!=0):
        links = create_sc_links(from_nodes=suppliers,to_nodes=manufacturers,lead_time_bounds=[5,7],tranport_cost_bounds=[100,200],link_dist_bounds=[500,800])
        for link in links:
            edges.append(link)
    if(num_distributors!=0):
        links = create_sc_links(from_nodes=manufacturers,to_nodes=distributors,lead_time_bounds=[3,5],tranport_cost_bounds=[100,200],link_dist_bounds=[400,600])
        for link in links:
            edges.append(link)
        links = create_sc_links(from_nodes=distributors,to_nodes=retailers,lead_time_bounds=[2,4],tranport_cost_bounds=[100,200],link_dist_bounds=[300,400])
        for link in links:
            edges.append(link)
    else:
        links = create_sc_links(from_nodes=manufacturers,to_nodes=retailers,lead_time_bounds=[3,5],tranport_cost_bounds=[100,200],link_dist_bounds=[400,600])
        for link in links:
            edges.append(link)
    
    demands = []
    # create demand 
    def poisson_arrivals(lambda_val=10):
        return np.random.poisson(lambda_val)
    def uniform_order(lower_bound=10,upper_bound=20):
        return np.random.randint(lower_bound,upper_bound)
    # (Note: currently by default we are modeling the demand as a Poisson process with arrival rate lambda)
    for retailer in retailers:
        id = random.randint(0,100) # any random ID
        lambda_val = random.randint(5,10) # any random ID
        lower, upper = random.randint(10,20), random.randint(21,50)
        demand_ret = Demand(ID=f"d{id}", name="demand", order_arrival_model=poisson_arrivals, order_quantity_model=uniform_order, demand_node=retailer)
        demands.append(demand_ret)

    supplychainnet = {"num_of_nodes":num_suppliers+num_manufacturers+num_distributors+num_retailers,
                      "num_suppliers":num_suppliers,
                      "num_manufacturers":num_manufacturers,
                      "num_distributors":num_distributors,
                      "num_retailers":num_retailers,
                      "num_of_edges":len(edges),
                      "nodes":[*suppliers,*distributors,*manufacturers,*retailers],
                      "edges":edges, 
                      "demand":demands,
                      "products": [product]}

    return supplychainnet

def get_sc_net_info(supplychainnet):
    """
    Get supply chain network information. 
    It displays following information:
    Number of nodes, edges, node parameters, edge parameters, demand, and products
    Parameters: 
    - supplychainnet (dict): a supply chain network
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


def visualize_sc_net(supplychainnet):
    """
    Visualize the supply chain network as a graph
    Nodes: supply chain nodes
    Edges: links between supply chain nodes
    Parameters:
    - supplychainnet (dict): supply chain network 
    """
    G=nx.Graph()
    nodes = supplychainnet["nodes"]
    edges = supplychainnet["edges"]
    for node in nodes:
        G.add_node(node.ID,level=node.node_type)
    
    for edge in edges:
        from_node = edge.source.ID
        to_node = edge.sink.ID
        G.add_edge(from_node,to_node,weight=edge.lead_time)

    pos=nx.spring_layout(G)
    nx.draw(G,pos,node_color='#CCCCCC',with_labels = True)
    labels = nx.get_edge_attributes(G,'weight')
    nx.draw_networkx_edge_labels(G,pos,edge_labels=labels)
    plt.title("Supply chain network")
    plt.show()

def simulate_sc_net(supplychainnet,sim_time,env=env):
    """
    Simulate the supply chain network for given time period
    Parameters:
    - env : SimPy Environment variable
    - supplychainnet (dict): a supply chain network
    - sim_time (int): simulation time
    Returns:
    - supplychainnet (dict): updated dict with listed performance measures
    """
    logger = global_logger.logger
    #get_sc_net_info(supplychainnet)

    demands = supplychainnet["demand"]
    nodes = supplychainnet["nodes"]

    # lets create some variable to store stats 
    sc_net_inventory_cost = 0
    sc_net_transport_cost = 0
    sc_net_node_cost = 0
    sc_net_profit = 0
    sc_total_unit_sold = 0
    sc_total_unsatisfied_demand = 0
    
    # run the simulation
    env.run(sim_time)

    # calculate stats
    for node in nodes:
        sc_net_inventory_cost += node.inventory_cost
        sc_net_transport_cost += node.transportation_cost
        sc_net_node_cost += node.node_cost
        sc_net_profit += node.net_profit
    
    for demand in demands:
        sc_total_unit_sold += demand.total_products_sold
        sc_total_unsatisfied_demand += demand.unsatisfied_demand
    
    supplychainnet["performance"] = {"total_product_sold":sc_total_unit_sold,
                                     "sc_profit":sc_net_profit,
                                     "sc_tranport_cost":sc_net_transport_cost,
                                     "sc_inv_cost":sc_net_inventory_cost,
                                     "sc_total_cost":sc_net_node_cost,
                                     "total_unsatisfied_demand": sc_total_unsatisfied_demand}
    
    logger.info(f"*** Supply chain statistics ***")
    logger.info(f"Number of products sold = {sc_total_unit_sold}") 
    logger.info(f"SC total profit = {sc_net_profit}") 
    logger.info(f"SC total tranportation cost = {sc_net_transport_cost}") 
    logger.info(f"SC total cost = {sc_net_node_cost}")
    logger.info(f"SC inventory cost = {sc_net_inventory_cost}") 
    logger.info(f"Customers returned  = {sc_total_unsatisfied_demand}")
    
    return supplychainnet

def create_sc_net(nodes:list = [],links:list = [],demands:list = [],products:list = []):
    """
    Create a supply chain network
    Parameters:
    - nodes (list): list of supply chain nodes
    - links (list): list of links between supply chain nodes
    - demands (list): list of demands
    - products (list): list of products
    Returns:
    - supplychainnet (dict): a supply chain network
    """
    supplychainnet = {"num_of_nodes":len(nodes),
                      "num_of_edges":len(links),
                      "nodes":nodes,
                      "edges":links, 
                      "demand":demands,
                      "products": products}
    return supplychainnet

if __name__ == "__main__": 
    supplychainnet = create_random_sc_net(num_suppliers=1,num_manufacturers=1,num_distributors=1,num_retailers=4)
    visualize_sc_net(supplychainnet)
    for node in supplychainnet["nodes"]:
        global_logger.logger.info(node.get_info())
    supplychainnet = simulate_sc_net(supplychainnet,sim_time=100)