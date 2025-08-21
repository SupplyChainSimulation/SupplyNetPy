import simpy
import networkx as nx
import matplotlib.pyplot as plt
from SupplyNetPy.Components.core import *

def check_duplicate_id(used_ids, new_id, entity_type="ID"):
    """
    Checks if the new_id is already in used_ids. If it is, logs an error and raises a ValueError.

    Parameters:
        used_ids (list): List of already used IDs.
        new_id (str): The new ID to check.
        entity_type (str): Type of the entity for which the ID is being checked (e.g., "node ID", "link ID").

    Attributes:
        None

    Returns:
        None

    Raises:
        ValueError: If the new_id is already in used_ids.
    """
    if new_id in used_ids:
        global_logger.logger.error(f"Duplicate {entity_type} {new_id}")
        raise ValueError(f"Duplicate {entity_type}")
    used_ids.append(new_id)

def process_info_dict(info_dict, logger):
    """
    Processes the dictionary and logs the key-value pairs.

    Parameters:
        info_dict (dict): The information dictionary to process.
        logger (logging.Logger): The logger instance used for logging messages.

    Attributes:
        None
    
    Returns:
        str: A string representation of the processed information.
    """
    info_string = ""
    for key, value in info_dict.items():
        if isinstance(value, object):
            value = str(value)
        if callable(value):
            value = value.__name__
        info_string += f"{key}: {value}\n"
        logger.info(f"{key}: {value}")
    return info_string

def visualize_sc_net(supplychainnet):
    """
    Visualize the supply chain network as a graph.

    Parameters:
        supplychainnet (dict): The supply chain network containing nodes and edges.

    Attributes:
        None

    Returns:
        None
    """
    G = nx.Graph()
    nodes = supplychainnet["nodes"]
    edges = supplychainnet["links"]

    # Add nodes to the graph
    for node_id, node in nodes.items():
        G.add_node(node_id, level=node.node_type)

    # Add edges to the graph
    for edge_id, edge in edges.items():
        from_node = edge.source.ID
        to_node = edge.sink.ID
        G.add_edge(from_node, to_node, weight=round(edge.lead_time(),2))

    # Generate the layout of the graph
    pos = nx.spectral_layout(G)

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

    Parameters: 
        supplychainnet (dict): A dictionary representing the supply chain network.

    Attributes:
        logger (logging.Logger): The logger instance used for logging messages.
        sc_info (str): A string to accumulate the supply chain network information.
        info_keys (list): A list of keys to extract information from the supply chain network.
        keys (set): A set of keys in the supply chain network regarding performance of the network.
    
    Returns:
        str: A string containing the supply chain network information.
    """
    logger = global_logger.logger
    global_logger.enable_logging(log_to_screen=True)
    sc_info = "Supply chain configuration: \n"
    info_keys = ['num_of_nodes', 'num_of_links', 'num_suppliers','num_manufacturers', 'num_distributors', 'num_retailers']
    for key in info_keys:
        if key in supplychainnet.keys():
            sc_info += f"{key}: {supplychainnet[key]}\n"
            logger.info(f"{key}: {supplychainnet[key]}")
    logger.info(f"Nodes in the network: {list(supplychainnet['nodes'].keys())}")
    sc_info += "Nodes in the network:\n"
    for node_id, node in supplychainnet["nodes"].items():
        sc_info += process_info_dict(node.get_info(), logger)
    logger.info(f"Edges in the network: {list(supplychainnet['links'].keys())}")
    sc_info += "Edges in the network:\n"
    for edge_id, edge in supplychainnet["links"].items():
        sc_info += process_info_dict(edge.get_info(), logger)
    logger.info(f"Demands in the network: {list(supplychainnet['demands'].keys())}")                
    sc_info += "Demands in the network:\n"
    for demand_id, demand in supplychainnet["demands"].items():
        sc_info += process_info_dict(demand.get_info(), logger)    
    keys = supplychainnet.keys() - {'nodes', 'links', 'demands', 'env', 'num_of_nodes', 'num_of_links', 'num_suppliers','num_manufacturers', 'num_distributors', 'num_retailers'}
    sc_info += "Supply chain network performance:\n"
    logger.info("Supply chain network performance:")
    for key in sorted(keys):
        sc_info += f"{key}: {supplychainnet[key]}\n"
        logger.info(f"{key}: {supplychainnet[key]}")
    return sc_info

def create_sc_net(nodes: list, links: list, demands: list, env:simpy.Environment = None):
    """
    This functions inputs the nodes, links and demand netlists and creates supply chain nodes, links and demand objects. 
    It then creates a supply chain network by putting all the objects in a dictionary.

    Parameters:
        nodes (list): A netlist of nodes in the supply chain network.
        links (list): A netlist of links between the nodes.
        demand (list): A netlist of demand nodes in the supply chain network.
        env (simpy.Environment, optional): A SimPy Environment object. If not provided, a new environment will be created.

    Attributes:
        global_logger (GlobalLogger): The global logger instance used for logging messages.
        supplychainnet (dict): A dictionary representing the supply chain network.
        used_ids (list): A list to keep track of used IDs to avoid duplicates.
        num_suppliers (int): Counter for the number of suppliers.
        num_manufacturers (int): Counter for the number of manufacturers.
        num_distributors (int): Counter for the number of distributors.
        num_retailers (int): Counter for the number of retailers.

    Raises:
        ValueError: If the SimPy Environment object is not provided or if there are duplicate IDs in nodes, links, or demands.
        ValueError: If an invalid node type is encountered.
        ValueError: If an invalid source or sink node is specified in a link.
        ValueError: If an invalid demand node is specified in a demand.

    Returns:
        dict: A dictionary representing the supply chain network.
    """
    if (isinstance(nodes[0],Node) or isinstance(links[0],Link) or isinstance(demands[0],Demand)) and env is None:
        global_logger.logger.error("Please provide SimPy Environment object env")
        raise ValueError("A SimPy Environment object is required!")
    if len(nodes)==0 or len(links)==0 or len(demands)==0:
        global_logger.logger.error("Nodes, links, and demands cannot be empty")
        raise ValueError("Nodes, links, and demands cannot be empty")
    if(env is None):
        env = simpy.Environment()
    supplychainnet = {"nodes":{},"links":{},"demands":{}} # create empty supply chain network
    used_ids = []
    num_suppliers = 0
    num_manufacturers = 0
    num_distributors = 0
    num_retailers = 0
    for node in nodes:
        if isinstance(node, dict):
            check_duplicate_id(used_ids, node["ID"], "node ID")
            node_id = node['ID']
            if node["node_type"].lower() in ["supplier", "infinite_supplier"]:
                supplychainnet["nodes"][f"{node_id}"] = Supplier(env=env, **node)
                num_suppliers += 1
            elif node["node_type"].lower() in ["manufacturer", "factory"]:
                node_ex = {key: node[key] for key in node if key != 'node_type'} # excluding key 'node_type', Manufacturer do not take it
                supplychainnet["nodes"][f"{node_id}"] = Manufacturer(env=env, **node_ex)
                num_manufacturers += 1
            elif node["node_type"].lower() in ["distributor", "warehouse"]:
                supplychainnet["nodes"][f"{node_id}"] = InventoryNode(env=env, **node)
                num_distributors += 1
            elif node["node_type"].lower() in ["retailer", "store", "shop"]:
                supplychainnet["nodes"][f"{node_id}"] = InventoryNode(env=env, **node)
                num_retailers += 1
            else:
                used_ids.remove(node["ID"])
                global_logger.logger.error(f"Invalid node type {node['node_type']}")
                raise ValueError("Invalid node type")
        elif isinstance(node, Node):
            if(node.ID in used_ids):
                global_logger.logger.error(f"Duplicate node ID {node.ID}")
                raise ValueError("Duplicate node ID")
            used_ids.append(node.ID)
            node_id = node.ID
            supplychainnet["nodes"][f"{node_id}"] = node
            if node.node_type.lower() in ["supplier", "infinite_supplier"]:
                num_suppliers += 1
            elif node.node_type.lower() in ["manufacturer", "factory"]:
                num_manufacturers += 1
            elif node.node_type.lower() in ["distributor", "warehouse"]:
                num_distributors += 1
            elif node.node_type.lower() in ["retailer", "store", "shop"]:
                num_retailers += 1
            else:
                used_ids.remove(node.ID)
                global_logger.logger.error(f"Invalid node type {node.node_type}")
                raise ValueError("Invalid node type")
    for link in links:
        if isinstance(link, dict):
            check_duplicate_id(used_ids, link["ID"], "link ID")
            source = None
            sink = None
            nodes = supplychainnet["nodes"].keys()
            if(link["source"] in nodes):
                source_id = link["source"]
                source = supplychainnet["nodes"][f"{source_id}"]
            if(link["sink"] in nodes):
                sink_id = link["sink"]
                sink = supplychainnet["nodes"][f"{sink_id}"]
            if(source is None or sink is None):
                global_logger.logger.error(f"Invalid source or sink node {link['source']} {link['sink']}")
                raise ValueError("Invalid source or sink node")
            exclude_keys = {'source', 'sink'}
            params = {k: v for k, v in link.items() if k not in exclude_keys}
            link_id = params['ID']
            supplychainnet["links"][f"{link_id}"] = Link(env=env,source=source,sink=sink,**params)
        elif isinstance(link, Link):
            if(link.ID in used_ids):
                global_logger.logger.error(f"Duplicate link ID {link.ID}")
                raise ValueError("Duplicate node ID")
            used_ids.append(link.ID)
            supplychainnet["links"][f"{link.ID}"] = link
    for d in demands:
        if isinstance(d, dict):
            check_duplicate_id(used_ids, d["ID"], "demand ID")
            demand_node = None # check for which node the demand is
            nodes = supplychainnet["nodes"].keys()
            if d['demand_node'] in nodes:
                demand_node_id = d['demand_node']
                demand_node = supplychainnet["nodes"][f"{demand_node_id}"]
            if(demand_node is None):
                global_logger.logger.error(f"Invalid demand node {d['demand_node']}")
                raise ValueError("Invalid demand node")
            exclude_keys = {'demand_node','node_type'}
            params = {k: v for k, v in d.items() if k not in exclude_keys}
            demand_id = params['ID']
            supplychainnet["demands"][f"{demand_id}"] = Demand(env=env,demand_node=demand_node,**params)
        elif isinstance(d, Demand):
            if(d.ID in used_ids):
                global_logger.logger.error(f"Duplicate demand ID {d.ID}")
                raise ValueError("Duplicate demand ID")
            used_ids.append(d.ID)
            supplychainnet["demands"][f"{d.ID}"] = d

    supplychainnet["env"] = env
    supplychainnet["num_of_nodes"] = num_suppliers + num_manufacturers + num_distributors + num_retailers
    supplychainnet["num_of_links"] = len(links)
    supplychainnet["num_suppliers"] = num_suppliers
    supplychainnet["num_manufacturers"] = num_manufacturers
    supplychainnet["num_distributors"] = num_distributors
    supplychainnet["num_retailers"] = num_retailers
    return supplychainnet

def simulate_sc_net(supplychainnet, sim_time, logging=True):
    """
    Simulate the supply chain network for a given time period, and calculate performance measures.

    Parameters:
        supplychainnet (dict): A supply chain network.
        sim_time (int): Simulation time.

    Returns:
        supplychainnet (dict): Updated dict with listed performance measures.
    """
    logger = global_logger.logger
    env = supplychainnet["env"]
    
    
    if(sim_time<=env.now):
        logger.warning(f"You have already ran simulation for this network! \n To create a new network use create_sc_net(), or specify the simulation time grater than {env.now} to run it further.")
        logger.info(f"Performance measures for the supply chain network are calculated and returned.")
    elif isinstance(logging, tuple) and len(logging) == 2:
        assert logging[0] < logging[1], "Start logging time should be less than stop logging time"
        assert logging[0] >= 0, "Start logging time should be greater than or equal to 0"
        assert logging[1] <= sim_time, "Stop logging time should be less than or equal to simulation time"        
        log_start = logging[0]
        log_stop = logging[1]
        global_logger.disable_logging()
        env.run(log_start) # Run the simulation
        global_logger.enable_logging()
        env.run(log_stop) # Run the simulation
        global_logger.disable_logging()
        if(sim_time > log_stop):
            env.run(sim_time) # Run the simulation
    elif isinstance(logging, bool) and logging:
        global_logger.enable_logging()
        env.run(sim_time) # Run the simulation
    else:
        global_logger.disable_logging()
        env.run(sim_time) # Run the simulation

    # Let's create some variables to store stats
    total_available_inv = 0
    avg_available_inv = 0
    total_inv_carry_cost = 0
    total_inv_spend = 0
    total_inv_waste = 0
    total_transport_cost = 0
    total_revenue = 0
    total_cost = 0
    total_profit = 0
    total_demand_by_customers = [0, 0] # [orders, products]
    total_fulfillment_received_by_customers = [0, 0] # [orders, products]
    total_demand_by_site = [0, 0] # [orders, products]
    total_fulfillment_received_by_site = [0, 0] # [orders, products]
    total_demand_placed = [0, 0] # [orders, products]
    total_fulfillment_received = [0, 0] # [orders, products]
    total_shortage = [0, 0] # [orders, products]
    total_backorders = [0, 0] # [orders, products]
    
    for key, node in supplychainnet["nodes"].items():
        if("infinite" in node.node_type.lower()): # skip infinite suppliers
            continue
        node.stats.update_stats() # update stats for the node
        total_available_inv += node.inventory.inventory.level
        if len(node.inventory.instantaneous_levels)>0:
            avg_available_inv += sum([x[1] for x in node.inventory.instantaneous_levels])/len(node.inventory.instantaneous_levels) 
        total_inv_carry_cost += node.inventory.carry_cost
        total_inv_spend += node.stats.inventory_spend_cost
        total_inv_waste += node.stats.inventory_waste
        total_transport_cost += node.stats.transportation_cost
        total_cost += node.stats.node_cost
        total_revenue += node.stats.revenue
        total_demand_by_site[0] += node.stats.demand_placed[0]
        total_demand_by_site[1] += node.stats.demand_placed[1]
        total_fulfillment_received_by_site[0] += node.stats.fulfillment_received[0]
        total_fulfillment_received_by_site[1] += node.stats.fulfillment_received[1]
        total_shortage[0] += node.stats.orders_shortage[0]
        total_shortage[1] += node.stats.orders_shortage[1]
        total_backorders[0] += node.stats.backorder[0]
        total_backorders[1] += node.stats.backorder[1]
    for key, node in supplychainnet["demands"].items():
        node.stats.update_stats() # update stats for the node
        total_transport_cost += node.stats.transportation_cost
        total_cost += node.stats.node_cost
        total_revenue += node.stats.revenue
        total_demand_by_customers[0] += node.stats.demand_placed[0] # orders
        total_demand_by_customers[1] += node.stats.demand_placed[1] # products
        total_fulfillment_received_by_customers[0] += node.stats.fulfillment_received[0]
        total_fulfillment_received_by_customers[1] += node.stats.fulfillment_received[1]
        total_shortage[0] += node.stats.orders_shortage[0]
        total_shortage[1] += node.stats.orders_shortage[1]
        total_backorders[0] += node.stats.backorder[0]
        total_backorders[1] += node.stats.backorder[1]
    total_demand_placed[0] = total_demand_by_customers[0] + total_demand_by_site[0]
    total_demand_placed[1] = total_demand_by_customers[1] + total_demand_by_site[1]
    total_fulfillment_received[0] = total_fulfillment_received_by_customers[0] + total_fulfillment_received_by_site[0]
    total_fulfillment_received[1] = total_fulfillment_received_by_customers[1] + total_fulfillment_received_by_site[1]
    total_profit = total_revenue - total_cost
    supplychainnet["available_inv"] = total_available_inv
    supplychainnet["avg_available_inv"] = avg_available_inv
    supplychainnet["inventory_carry_cost"] = total_inv_carry_cost   
    supplychainnet["inventory_spend_cost"] = total_inv_spend
    supplychainnet["inventory_waste"] = total_inv_waste
    supplychainnet["transportation_cost"] = total_transport_cost
    supplychainnet["revenue"] = total_revenue
    supplychainnet["total_cost"] = total_cost
    supplychainnet["profit"] = total_profit
    supplychainnet["demand_by_customers"] = total_demand_by_customers
    supplychainnet["fulfillment_received_by_customers"] = total_fulfillment_received_by_customers
    supplychainnet["demand_by_site"] = total_demand_by_site
    supplychainnet["fulfillment_received_by_site"] = total_fulfillment_received_by_site
    supplychainnet["total_demand"] = total_demand_placed
    supplychainnet["total_fulfillment_received"] = total_fulfillment_received
    supplychainnet["shortage"] = total_shortage
    supplychainnet["backorders"] = total_backorders
    # Calculate average cost per order and per item
    if total_demand_placed[0] > 0:
        supplychainnet["avg_cost_per_order"] = total_cost / total_demand_placed[0]
    else:
        supplychainnet["avg_cost_per_order"] = 0
    if total_demand_placed[1] > 0:
        supplychainnet["avg_cost_per_item"] = total_cost / total_demand_placed[1]
    else:
        supplychainnet["avg_cost_per_item"] = 0
    if isinstance(logging, tuple):
        global_logger.enable_logging()
    max_key_length = max(len(key) for key in supplychainnet.keys()) + 1
    logger.info(f"Supply chain info:")
    for key in sorted(supplychainnet.keys()):
        logger.info(f"{key.ljust(max_key_length)}: {supplychainnet[key]}")
    return supplychainnet

def print_node_wise_performance(nodes_object_list):
    """
    This function prints the performance metrics for each supply chain node provided in the nodes_object_list.

    Parameters:
        nodes_object_list (list): List of supply chain node objects

    Returns: 
        None
    """

    if not nodes_object_list:
        print("No nodes provided.")
        return

    # Pre-fetch statistics from all nodes
    stats_per_node = {node.name: node.stats.get_statistics() for node in nodes_object_list}
    stat_keys = sorted(next(iter(stats_per_node.values())).keys())

    # Determine column widths
    col_width = 25
    header = "Performance Metric".ljust(col_width)
    for name in stats_per_node:
        header += name.ljust(col_width)
    print(header)

    # Print row-wise stats
    for key in stat_keys:
        row = key.ljust(col_width)
        for name in stats_per_node:
            value = stats_per_node[name].get(key, "N/A")
            row += str(value).ljust(col_width)
        print(row)