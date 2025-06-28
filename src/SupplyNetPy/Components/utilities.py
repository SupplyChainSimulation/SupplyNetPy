import simpy
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
#from SupplyNetPy.Components.core import *
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
        node_info_dict = node.get_info()
        for key, value in node_info_dict.items():
            if type(value)==list:
                list_vals = 0
                if(len(value)>0):
                    list_vals = f"{value[0]} ... "
                    value = np.array(value)
                sc_info += f"{key}: (list) len = {len(value)}, sum = {sum(value)}, [{list_vals}]\n"
                logger.info(f"{key}: (list) len = {len(value)}, sum = {sum(value)}, [{list_vals}]")
            else:    
                sc_info += f"{key}: {value}\n"
                logger.info(f"{key}: {value}")
    logger.info(f"Edges in the network: {list(supplychainnet['links'].keys())}")
    sc_info += "Edges in the network:\n"
    for edge_id, edge in supplychainnet["links"].items():
        edge_info_dict = edge.get_info()
        for key, value in edge_info_dict.items():
            if type(value)==list:
                list_vals = 0
                if(len(value)>0):
                    list_vals = f"{value[0]} ... "
                    value = np.array(value)
                sc_info += f"{key}: (list) len = {len(value)}, sum = {sum(value)}, [{list_vals}]\n"
                logger.info(f"{key}: (list) len = {len(value)}, sum = {sum(value)}, [{list_vals}]")
            else:    
                sc_info += f"{key}: {value}\n"
                logger.info(f"{key}: {value}")
    logger.info(f"Demands in the network: {list(supplychainnet['demands'].keys())}")                
    sc_info += "Demands in the network:\n"
    for demand_id, demand in supplychainnet["demands"].items():
        demand_info_dict = demand.get_info()
        for key, value in demand_info_dict.items():
            if type(value)==list:
                list_vals = 0
                if(len(value)>0):
                    list_vals = f"{value[0]} ... "
                    value = np.array(value)
                sc_info += f"{key}: (list) len = {len(value)}, sum = {sum(value)}, [{list_vals}]\n"
                logger.info(f"{key}: (list) len = {len(value)}, sum = {sum(value)}, [{list_vals}]")
            else:    
                sc_info += f"{key}: {value}\n"
                logger.info(f"{key}: {value}")    
    keys = supplychainnet.keys() - {'nodes', 'links', 'demands', 'env', 'num_of_nodes', 'num_of_links', 'num_suppliers','num_manufacturers', 'num_distributors', 'num_retailers'}
    sc_info += "Supply chain network performance:\n"
    logger.info("Supply chain network performance:")
    for key in keys:
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

    Returns:
        dict: A dictionary representing the supply chain network.
    """
    if (isinstance(nodes[0],Node) or isinstance(links[0],Link) or isinstance(demands[0],Demand)) and env is None:
        global_logger.logger.error("Please provide SimPy Environment object env")
        raise ValueError("A SimPy Environment object is required!")
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
            if(node["ID"] in used_ids):
                global_logger.logger.error(f"Duplicate node ID {node['ID']}")
                raise ValueError("Duplicate node ID")
            used_ids.append(node["ID"])
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
            if(link["ID"] in used_ids):
                global_logger.logger.error(f"Duplicate link ID {link['ID']}")
                raise ValueError("Duplicate node ID")
            used_ids.append(link["ID"])
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
            if(d["ID"] in used_ids):
                global_logger.logger.error(f"Duplicate demand ID {d['ID']}")
                raise ValueError("Duplicate demand ID")
            used_ids.append(d["ID"])
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

def simulate_sc_net(supplychainnet, sim_time):
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
    else:
        env.run(sim_time) # Run the simulation
    # Let's create some variables to store stats
    total_available_inv = 0
    avg_available_inv = 0
    total_inv_carry_cost = 0
    total_inv_spend = 0
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
    supplychainnet["total_available_inv"] = total_available_inv
    supplychainnet["avg_available_inv"] = avg_available_inv
    supplychainnet["total_inv_carry_cost"] = total_inv_carry_cost   
    supplychainnet["total_inv_spend"] = total_inv_spend
    supplychainnet["total_transport_cost"] = total_transport_cost
    supplychainnet["total_revenue"] = total_revenue
    supplychainnet["total_cost"] = total_cost
    supplychainnet["total_profit"] = total_profit
    supplychainnet["total_demand_by_customers"] = total_demand_by_customers
    supplychainnet["total_fulfillment_received_by_customers"] = total_fulfillment_received_by_customers
    supplychainnet["total_demand_by_site"] = total_demand_by_site
    supplychainnet["total_fulfillment_received_by_site"] = total_fulfillment_received_by_site
    supplychainnet["total_demand"] = total_demand_placed
    supplychainnet["total_fulfillment_received"] = total_fulfillment_received
    supplychainnet["total_shortage"] = total_shortage
    supplychainnet["total_backorders"] = total_backorders
    # Calculate average cost per order and per item
    if total_demand_placed[0] > 0:
        supplychainnet["avg_cost_per_order"] = total_cost / total_demand_placed[0]
    else:
        supplychainnet["avg_cost_per_order"] = 0
    if total_demand_placed[1] > 0:
        supplychainnet["avg_cost_per_item"] = total_cost / total_demand_placed[1]
    else:
        supplychainnet["avg_cost_per_item"] = 0
    
    logger.info(f"Supply chain performance measures:")
    for key, value in supplychainnet.items():
        logger.info(f"{key}: {value}")
    return supplychainnet