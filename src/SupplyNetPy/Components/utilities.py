import SupplyNetPy.Components.inventory as inv
import SupplyNetPy.Components.core as sccore
import simpy
import random
import networkx as nx
import matplotlib.pyplot as plt

def create_sc_nodes(env,num_of_nodes,node_type,inv_cap_bounds,inv_hold_cost_bounds,inv_reorder_lvl_bounds,product):
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
    locations = ["Goa", "Mumbai", "Delhi", "Banglore", "Hyderabad"] # this lst can be global or taken input as an argument
    nodes = []
    for i in range(0,num_of_nodes):
        id = random.randint(200,300) # any random ID
        inv_capacity = random.randint(inv_cap_bounds[0],inv_cap_bounds[1]) # choose an integer in given bounds
        inv_hold_cost = random.randint(inv_hold_cost_bounds[0],inv_hold_cost_bounds[1])
        inv_reorder_lvl = random.randint(inv_reorder_lvl_bounds[0],inv_reorder_lvl_bounds[1])
        if(node_type.lower()=="supplier"):
            node = sccore.Supplier(env=env, name=f"supplier{i}", node_id=str(id), location=random.choice(locations),inv_capacity=inv_capacity, inv_holding_cost=inv_hold_cost, reorder_level=inv_reorder_lvl)
            nodes.append(node)
        elif(node_type.lower()=="manufacturer"):
            node = sccore.Manufacturer(env=env,name=f"Manufacturer{i}", node_id=str(id),location=random.choice(locations), products=[product],production_cost=100, production_level=200,inv_capacity=inv_capacity, inv_holding_cost=inv_hold_cost, reorder_level=inv_reorder_lvl)
            nodes.append(node)
        elif(node_type.lower()=="distributor" or node_type.lower()=="warehouse"):
            node = sccore.Distributor(env=env,name=f"distributor{i}",node_id=id,location=random.choice(locations), products=[product],inv_capacity=inv_capacity,inv_holding_cost=inv_hold_cost,reorder_level=inv_reorder_lvl)
            nodes.append(node)
        elif(node_type.lower()=="retailer"):
            node = sccore.Retailer(env=env, name=f"retailer{i}", node_id=id, location=random.choice(locations),products=[product],inv_capacity=inv_capacity, inv_holding_cost=inv_hold_cost, reorder_level=inv_reorder_lvl)
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
    for i in range(0,len(from_nodes)):
        for j in range(0,len(to_nodes)):
            lead_time = random.randint(lead_time_bounds[0],lead_time_bounds[1])
            tranport_cost = random.randint(tranport_cost_bounds[0],tranport_cost_bounds[1])
            link_dist = random.randint(link_dist_bounds[0],link_dist_bounds[1])
            link = sccore.Link(from_node=from_nodes[i], to_node=to_nodes[j], lead_time=lead_time, transportation_cost=tranport_cost, link_distance=link_dist)
            links.append(link)
    return(links)

def create_a_random_product(name, desc, cost_bounds, profit_bounds, shelf_life_bounds):
    """
    Creates a product with given name and random cost, profit and shelf life
    Parameters:
    - name (str): name of the product
    - desc (str): short description of the product
    - cost_bounds (list/tuple): upper and lower bounds of the product cost
    - profit_bounds (list/tuple): upper and lower bounds of the profit made per unit of product sold
    - shelf_life_bounds (list/tuple): upper and lower bounds for product's shelf life
    Returns:
    - product (Product): An object of class Product
    """
    product_types = ["perishable","non-perishable"]
    product_type = random.choice(product_types)
    product_cost = random.randint(cost_bounds[0],cost_bounds[1])
    product_profit = random.randint(profit_bounds[0],profit_bounds[1])
    if(product_type=="perishable"):
        shelf_life = random.randint(shelf_life_bounds[0],shelf_life_bounds[1])
        product = inv.Product(sku="12325", name=name, description=desc, cost=product_cost,profit=product_profit, product_type=product_type, shelf_life=shelf_life)
    else:
        product = inv.Product(sku="12325", name=name, description=desc, cost=product_cost,profit=product_profit, product_type=product_type, shelf_life=None)
    return product

def create_random_sc_net(env,num_suppliers,num_manufacturers,num_distributors,num_retailers):
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
    product = create_a_random_product(name="Bottle", desc="Water Bottle Steel", cost_bounds=[300,1000], profit_bounds=[100,150], shelf_life_bounds=[10,15])
    
    if(num_suppliers!=0):
        suppliers = create_sc_nodes(env,num_of_nodes=num_suppliers,node_type="supplier",inv_cap_bounds=[800,900],
                                     inv_hold_cost_bounds=[1,3],inv_reorder_lvl_bounds=[700,750],product=product)
    if(num_manufacturers!=0):
        manufacturers = create_sc_nodes(env,num_of_nodes=num_manufacturers,node_type="manufacturer",inv_cap_bounds=[600,700],
                                         inv_hold_cost_bounds=[2,4],inv_reorder_lvl_bounds=[400,500],product=product)
    else:
        raise ValueError(f"number of manufacturers can not be zero!")
    
    if(num_distributors!=0):
        distributors = create_sc_nodes(env,num_of_nodes=num_distributors,node_type="distributor",inv_cap_bounds=[300,400],
                                         inv_hold_cost_bounds=[3,5],inv_reorder_lvl_bounds=[200,250],product=product)
    if(num_retailers!=0):
        retailers = create_sc_nodes(env,num_of_nodes=num_retailers,node_type="retailer",inv_cap_bounds=[100,200],
                                         inv_hold_cost_bounds=[5,9],inv_reorder_lvl_bounds=[50,100],product=product)
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
    # (Note: currently by default we are modeling the demand as a Poisson process with arrival rate lambda)
    for i in range(0,num_retailers):
        demand_ret = sccore.Demand(env=env, arr_dist="Poisson",arr_params=[6],node=retailers[i],demand_dist="Uniform",demand_params=[1,10])
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
    logger = sccore.global_logger.logger
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
    for i in range(0,len(nodes)):
        G.add_node(nodes[i].name,level=nodes[i].name)
    
    for i in range(0,len(edges)):
        from_node = edges[i].from_node.name
        to_node = edges[i].to_node.name
        G.add_edge(from_node,to_node,weight=edges[i].lead_time)

    pos=nx.spring_layout(G)
    nx.draw(G,pos,node_color='#CCCCCC',with_labels = True)
    labels = nx.get_edge_attributes(G,'weight')
    nx.draw_networkx_edge_labels(G,pos,edge_labels=labels)
    plt.title("Supply chain network")
    plt.show()

def simulate_sc_net(env,supplychainnet,sim_time):
    """
    Simulate the supply chain network for given time period
    Parameters:
    - env : SimPy Environment variable
    - supplychainnet (dict): a supply chain network
    - sim_time (int): simulation time
    Returns:
    - supplychainnet (dict): updated dict with listed performance measures
    """
    logger = sccore.global_logger.logger
    get_sc_net_info(supplychainnet)

    demands = supplychainnet["demand"]
    nodes = supplychainnet["nodes"]
    edges = supplychainnet["edges"]

    # lets create some variable to store stats 
    sc_tranport_cost = 0
    sc_profit = 0
    sc_total_unit_sold = 0
    sc_revenue = 0
    sc_total_customers_returned = 0
    sc_inventory_cost = 0
    
    # create demand events to retailer nodes
    for i in range(0,len(demands)):
        env.process(demands[i].poisson_arrivals(env=env))
    
    # run the simulation
    env.run(sim_time)

    # calculate stats
    for node in nodes:
        node.calculate_stats(env.now)
        sc_profit += node.profit
        sc_total_unit_sold += node.total_sale
        sc_inventory_cost += sum(node.inventory.stats_inventory_hold_costs)
    
    for edge in edges:
        sc_tranport_cost += edge.total_transport_cost

    for demand in demands:
        sc_total_customers_returned += demand.stats_customer_returned

    sc_revenue = sc_profit - sc_tranport_cost - sc_inventory_cost
    sc_avg_revenue = sc_revenue/sim_time
    
    supplychainnet["performance"] = {"total_product_sold":sc_total_unit_sold,
                                     "sc_profit":sc_profit,
                                     "sc_tranport_cost":sc_tranport_cost,
                                     "sc_inv_cost":sc_inventory_cost,
                                     "sc_revenue":sc_revenue,
                                     "avg_revenue":sc_avg_revenue,
                                     "total_customer_returned": sc_total_customers_returned}
    logger.info(f"*** SC stats ***")
    logger.info(f"Number of products sold = {sc_total_unit_sold}") 
    logger.info(f"SC total profit = {sc_profit}") 
    logger.info(f"SC total tranportation cost = {sc_tranport_cost}") 
    logger.info(f"SC inventory cost = {sc_inventory_cost}") 
    logger.info(f"SC revenue (profit - cost) = {sc_revenue}") 
    logger.info(f"Average revenue (per day) = {sc_avg_revenue}") 
    logger.info(f"Customers returned  = {sc_total_customers_returned}")
    
    return supplychainnet

if __name__ == "__main__": 
    env = simpy.Environment()
    supplychainnet = create_random_sc_net(env=env,num_suppliers=2,num_manufacturers=1,num_distributors=2,num_retailers=4)
    sccore.global_logger.enable_logging(log_to_file=True,log_to_screen=True)
    supplychainnet = simulate_sc_net(env,supplychainnet,sim_time=10)
    visualize_sc_net(supplychainnet)