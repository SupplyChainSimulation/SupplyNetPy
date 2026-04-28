import simpy
import networkx as nx
import matplotlib.pyplot as plt
# Named imports only — no wildcards. ``global_logger`` is internal plumbing and
# is deliberately pulled in by name here rather than re-exported.
from SupplyNetPy.Components.core import (
    Node,
    NodeType,
    Link,
    Supplier,
    InventoryNode,
    Manufacturer,
    Demand,
    global_logger,
)

# Dispatch table: ``NodeType`` → (constructor class, counter key, drop
# ``node_type`` from kwargs?). The enum is the single source of truth for
# which node types exist; adding a new one is a single-site change here plus
# the entry on ``NodeType``. The boolean flag covers ``Manufacturer``, whose
# ``__init__`` does not accept a ``node_type`` parameter (it is hard-coded to
# ``"manufacturer"`` inside the class).
_NODE_DISPATCH = {
    NodeType.INFINITE_SUPPLIER: (Supplier,      "num_suppliers",      False),
    NodeType.SUPPLIER:          (Supplier,      "num_suppliers",      False),
    NodeType.MANUFACTURER:      (Manufacturer,  "num_manufacturers",  True),
    NodeType.FACTORY:           (Manufacturer,  "num_manufacturers",  True),
    NodeType.WAREHOUSE:         (InventoryNode, "num_distributors",   False),
    NodeType.DISTRIBUTOR:       (InventoryNode, "num_distributors",   False),
    NodeType.RETAILER:          (InventoryNode, "num_retailers",      False),
    NodeType.STORE:             (InventoryNode, "num_retailers",      False),
    NodeType.SHOP:              (InventoryNode, "num_retailers",      False),
}

__all__ = [
    "check_duplicate_id",
    "process_info_dict",
    "visualize_sc_net",
    "get_sc_net_info",
    "create_sc_net",
    "simulate_sc_net",
    "get_node_wise_performance",
    "format_node_wise_performance",
    "print_node_wise_performance",
    "Network",
]


def check_duplicate_id(used_ids, new_id, entity_type="ID"):
    """
    Checks if ``new_id`` is already in ``used_ids``. If it is, logs an error
    and raises ``ValueError``; otherwise inserts it.

    Accepts either a ``set`` (preferred — O(1) membership and insert) or a
    ``list`` (kept for backward compatibility with external callers — O(n) on
    both operations). ``create_sc_net`` passes a ``set``; the helper duck-types
    the insert call so existing user code that builds its own ``list`` keeps
    working unchanged.

    Parameters:
        used_ids (set | list): Container of already-used IDs. Mutated in place.
        new_id (str): The new ID to check and insert.
        entity_type (str): Type of the entity for which the ID is being checked
            (e.g., ``"node ID"``, ``"link ID"``).

    Returns:
        None

    Raises:
        ValueError: If ``new_id`` is already in ``used_ids``.
    """
    if new_id in used_ids:
        global_logger.error(f"Duplicate {entity_type} {new_id}")
        raise ValueError(f"Duplicate {entity_type}")
    # ``set`` exposes ``.add``; ``list`` exposes ``.append``. Pick whichever
    # the caller's container actually supports rather than gating on isinstance,
    # so any other ``MutableSet`` / ``MutableSequence`` works too.
    insert = getattr(used_ids, "add", None) or used_ids.append
    insert(new_id)

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
    # Build via list + join instead of repeated ``+=`` concatenation. Each
    # ``+=`` on a Python str allocates a new string and copies the prefix,
    # making the loop O(n^2) in total bytes — a real cost for networks with
    # 100+ nodes whose info dicts each accumulate dozens of lines.
    parts = []
    for key, value in info_dict.items():
        if isinstance(value, object):
            value = str(value)
        if callable(value):
            value = value.__name__
        parts.append(f"{key}: {value}")
        logger.info(f"{key}: {value}")
    return "\n".join(parts) + ("\n" if parts else "")

# Tier ordering for ``multipartite_layout`` (§8). Map every NodeType to a
# horizontal column so the layout reads left-to-right as raw → finished, which
# is the natural reading order for a supply chain. ``spectral_layout`` (the
# previous default) often degenerates for small directed graphs and can
# produce embeddings that overlap suppliers and retailers; the tiered layout
# avoids that and is also more interpretable.
_TIER_INDEX = {
    "infinite_supplier": 0,
    "supplier": 0,
    "manufacturer": 1,
    "factory": 1,
    "warehouse": 2,
    "distributor": 2,
    "retailer": 3,
    "store": 3,
    "shop": 3,
    "demand": 4,
}


def visualize_sc_net(supplychainnet):
    """
    Visualize the supply chain network as a graph.

    Uses :func:`networkx.multipartite_layout` keyed by node tier so the
    drawing reads left-to-right (suppliers → manufacturers → distributors →
    retailers → demand). The previous default ``spectral_layout`` often
    produced degenerate embeddings for small directed graphs (§8).

    Parameters:
        supplychainnet (dict): The supply chain network containing nodes and edges.

    Returns:
        None
    """
    G = nx.DiGraph()
    nodes = supplychainnet["nodes"]
    edges = supplychainnet["links"]

    # Tier each node by its NodeType so multipartite_layout can column it.
    # ``demands`` are not in ``nodes`` but are still useful to visualise; add
    # them as the right-most tier with edges from their demand_node.
    for node_id, node in nodes.items():
        tier = _TIER_INDEX.get(str(node.node_type).lower(), 2)
        G.add_node(node_id, subset=tier, level=node.node_type)

    for edge_id, edge in edges.items():
        G.add_edge(edge.source.ID, edge.sink.ID, weight=round(edge.lead_time(), 2))

    for demand_id, demand in supplychainnet.get("demands", {}).items():
        G.add_node(demand_id, subset=_TIER_INDEX["demand"], level="demand")
        target = getattr(demand, "demand_node", None)
        if target is not None and target.ID in nodes:
            G.add_edge(target.ID, demand_id)

    pos = nx.multipartite_layout(G, subset_key="subset")
    nx.draw(G, pos, node_color='#CCCCCC', with_labels=True, arrows=True)
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
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
    logger = global_logger
    global_logger.enable_logging(log_to_screen=True)
    # Accumulate into a list and join once at the end — O(n) instead of the
    # quadratic ``sc_info += ...`` chain (str is immutable; every ``+=``
    # allocates a new string and copies the prefix).
    parts = ["Supply chain configuration: "]
    info_keys = ['num_of_nodes', 'num_of_links', 'num_suppliers','num_manufacturers', 'num_distributors', 'num_retailers']
    for key in info_keys:
        if key in supplychainnet.keys():
            parts.append(f"{key}: {supplychainnet[key]}")
            logger.info(f"{key}: {supplychainnet[key]}")
    logger.info(f"Nodes in the network: {list(supplychainnet['nodes'].keys())}")
    parts.append("Nodes in the network:")
    for node_id, node in supplychainnet["nodes"].items():
        parts.append(process_info_dict(node.get_info(), logger).rstrip("\n"))
    logger.info(f"Edges in the network: {list(supplychainnet['links'].keys())}")
    parts.append("Edges in the network:")
    for edge_id, edge in supplychainnet["links"].items():
        parts.append(process_info_dict(edge.get_info(), logger).rstrip("\n"))
    logger.info(f"Demands in the network: {list(supplychainnet['demands'].keys())}")
    parts.append("Demands in the network:")
    for demand_id, demand in supplychainnet["demands"].items():
        parts.append(process_info_dict(demand.get_info(), logger).rstrip("\n"))
    keys = supplychainnet.keys() - {'nodes', 'links', 'demands', 'env', 'num_of_nodes', 'num_of_links', 'num_suppliers','num_manufacturers', 'num_distributors', 'num_retailers'}
    parts.append("Supply chain network performance:")
    logger.info("Supply chain network performance:")
    for key in sorted(keys):
        parts.append(f"{key}: {supplychainnet[key]}")
        logger.info(f"{key}: {supplychainnet[key]}")
    return "\n".join(parts) + "\n"

def create_sc_net(nodes: list, links: list, demands: list, env:simpy.Environment = None):
    """
    This functions inputs the nodes, links and demand netlists and creates supply chain nodes, links and demand objects.
    It then creates a supply chain network by putting all the objects in a dictionary.

    Each of ``nodes``, ``links``, and ``demands`` must be homogeneous — either
    entirely dicts (netlist style) or entirely pre-built domain objects
    (``Node`` / ``Link`` / ``Demand`` instances). Mixing the two within a single
    list is rejected, because a fresh ``simpy.Environment`` created for the
    dict items would not match the one the object items were built against.
    When any list contains pre-built objects, ``env`` must be passed explicitly
    and each object's own ``env`` must match it.

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
        ValueError: If any of ``nodes`` / ``links`` / ``demands`` mixes dicts and pre-built domain objects.
        ValueError: If a pre-built object's ``env`` does not match the provided ``env``.
        ValueError: If an invalid node type is encountered.
        ValueError: If an invalid source or sink node is specified in a link.
        ValueError: If an invalid demand node is specified in a demand.

    Returns:
        dict: A dictionary representing the supply chain network.
    """
    # Reject mixed dict-and-object lists up-front. Scanning every element means
    # we no longer fall for the old first-element-only trap: a list like
    # ``[dict, Node_instance, ...]`` used to pass the env-required check
    # (because ``nodes[0]`` was a dict) and then silently fall into the
    # ``isinstance(node, Node)`` branch at a later index with a fresh env,
    # dropping the object's real env on the floor.
    def _check_homogeneous(items, obj_cls, list_name):
        has_dict = any(isinstance(x, dict) for x in items)
        has_obj = any(isinstance(x, obj_cls) for x in items)
        if has_dict and has_obj:
            global_logger.error(
                f"{list_name} list mixes dicts and {obj_cls.__name__} instances."
            )
            raise ValueError(
                f"{list_name} list mixes dicts and {obj_cls.__name__} instances; "
                f"use all dicts or all {obj_cls.__name__} instances."
            )

    _check_homogeneous(nodes, Node, "nodes")
    _check_homogeneous(links, Link, "links")
    _check_homogeneous(demands, Demand, "demands")

    # ``env`` is required whenever ANY list contains a pre-built domain object,
    # regardless of the element's position. Scanning each list (rather than
    # indexing [0]) also avoids an IndexError on legitimately empty lists.
    any_object = (
        any(isinstance(x, Node) for x in nodes)
        or any(isinstance(x, Link) for x in links)
        or any(isinstance(x, Demand) for x in demands)
    )
    if any_object and env is None:
        global_logger.error("Please provide SimPy Environment object env")
        raise ValueError("A SimPy Environment object is required!")
    if len(nodes)==0 or len(links)==0 or len(demands)==0:
        global_logger.error("Nodes, links, and demands cannot be empty")
        raise ValueError("Nodes, links, and demands cannot be empty")
    if(env is None):
        env = simpy.Environment()

    # When the user supplied both ``env`` and pre-built objects, each object's
    # own ``env`` must match — otherwise the returned supplychainnet would
    # combine processes from two different environments and nothing would run
    # consistently. The old code simply ignored the object's env; this check
    # surfaces the mismatch loudly.
    def _check_env_match(items, obj_cls, list_name):
        for i, x in enumerate(items):
            if isinstance(x, obj_cls) and getattr(x, "env", None) is not env:
                global_logger.error(
                    f"{list_name}[{i}] ({getattr(x, 'ID', '<no ID>')}) was built against a "
                    f"different simpy.Environment than the one passed to create_sc_net."
                )
                raise ValueError(
                    f"{list_name}[{i}] env does not match the env passed to create_sc_net."
                )

    _check_env_match(nodes, Node, "nodes")
    _check_env_match(links, Link, "links")
    _check_env_match(demands, Demand, "demands")
    supplychainnet = {"nodes":{},"links":{},"demands":{}} # create empty supply chain network
    # Set rather than list: ``in`` is O(1) and ``.add``/``.remove`` are O(1) too,
    # so building a network with N nodes is O(N) instead of O(N^2). The
    # ``check_duplicate_id`` helper duck-types its insert call, so passing a
    # set just works.
    used_ids = set()
    # Counters keyed by the category name used in ``_NODE_DISPATCH``. A dict
    # replaces the four separate ``num_*`` locals so dispatch is a single
    # ``counters[category] += 1`` instead of an if/elif ladder.
    counters = {"num_suppliers": 0, "num_manufacturers": 0, "num_distributors": 0, "num_retailers": 0}
    for node in nodes:
        if isinstance(node, dict):
            check_duplicate_id(used_ids, node["ID"], "node ID")
            node_id = node["ID"]
            try:
                nt = NodeType(node["node_type"])
            except ValueError:
                used_ids.remove(node["ID"])
                global_logger.error(f"Invalid node type {node['node_type']}")
                raise ValueError("Invalid node type")
            cls, counter_key, drop_node_type = _NODE_DISPATCH[nt]
            # ``Manufacturer.__init__`` does not accept ``node_type`` — every
            # other constructor does. The ``drop_node_type`` flag is the one
            # place this asymmetry is encoded.
            kwargs = {k: v for k, v in node.items() if not (drop_node_type and k == "node_type")}
            supplychainnet["nodes"][f"{node_id}"] = cls(env=env, **kwargs)
            counters[counter_key] += 1
        elif isinstance(node, Node):
            check_duplicate_id(used_ids, node.ID, "node ID")
            node_id = node.ID
            supplychainnet["nodes"][f"{node_id}"] = node
            try:
                nt = NodeType(node.node_type)
            except ValueError:
                used_ids.remove(node.ID)
                global_logger.error(f"Invalid node type {node.node_type}")
                raise ValueError("Invalid node type")
            counters[_NODE_DISPATCH[nt][1]] += 1
    for link in links:
        if isinstance(link, dict):
            check_duplicate_id(used_ids, link["ID"], "link ID")
            source = None
            sink = None
            node_ids = supplychainnet["nodes"].keys()
            if(link["source"] in node_ids):
                source_id = link["source"]
                source = supplychainnet["nodes"][f"{source_id}"]
            if(link["sink"] in node_ids):
                sink_id = link["sink"]
                sink = supplychainnet["nodes"][f"{sink_id}"]
            if(source is None or sink is None):
                global_logger.error(f"Invalid source or sink node {link['source']} {link['sink']}")
                raise ValueError("Invalid source or sink node")
            exclude_keys = {'source', 'sink'}
            params = {k: v for k, v in link.items() if k not in exclude_keys}
            link_id = params['ID']
            supplychainnet["links"][f"{link_id}"] = Link(env=env,source=source,sink=sink,**params)
        elif isinstance(link, Link):
            check_duplicate_id(used_ids, link.ID, "link ID")
            supplychainnet["links"][f"{link.ID}"] = link
    for d in demands:
        if isinstance(d, dict):
            check_duplicate_id(used_ids, d["ID"], "demand ID")
            demand_node = None # check for which node the demand is
            node_ids = supplychainnet["nodes"].keys()
            if d['demand_node'] in node_ids:
                demand_node_id = d['demand_node']
                demand_node = supplychainnet["nodes"][f"{demand_node_id}"]
            if(demand_node is None):
                global_logger.error(f"Invalid demand node {d['demand_node']}")
                raise ValueError("Invalid demand node")
            exclude_keys = {'demand_node','node_type'}
            params = {k: v for k, v in d.items() if k not in exclude_keys}
            demand_id = params['ID']
            supplychainnet["demands"][f"{demand_id}"] = Demand(env=env,demand_node=demand_node,**params)
        elif isinstance(d, Demand):
            check_duplicate_id(used_ids, d.ID, "demand ID")
            supplychainnet["demands"][f"{d.ID}"] = d

    supplychainnet["env"] = env
    supplychainnet["num_of_nodes"] = sum(counters.values())
    supplychainnet["num_of_links"] = len(links)
    supplychainnet.update(counters)
    return supplychainnet

def simulate_sc_net(supplychainnet, sim_time, logging=True, log_window=None):
    """
    Simulate the supply chain network for a given time period, and calculate performance measures.

    Parameters:
        supplychainnet (dict): A supply chain network.
        sim_time (int): Simulation time.
        logging (bool): Whether to enable logging for the whole run. Defaults
            to ``True``. Mutually exclusive with ``log_window`` — pass
            ``log_window`` to confine logging to a sub-interval instead.
        log_window (tuple[float, float], optional): ``(start, stop)`` window
            during which logging is enabled; the simulation runs silently
            outside the window. Splits the prior overloaded-tuple use of
            ``logging`` into a dedicated parameter (§6.2).

    Returns:
        supplychainnet (dict): Updated dict with listed performance measures.
    """
    logger = global_logger
    env = supplychainnet["env"]

    # Back-compat shim: the original API allowed ``logging=(start, stop)`` to
    # request a window. Honour that spelling but route it onto ``log_window``
    # so the rest of this function only sees one shape per parameter.
    if isinstance(logging, tuple) and len(logging) == 2:
        if log_window is not None:
            logger.warning("simulate_sc_net: both logging=tuple and log_window= were provided; log_window takes precedence.")
        else:
            logger.warning("simulate_sc_net: logging=(start, stop) is deprecated; use log_window=(start, stop) instead.")
            log_window = logging
        logging = True

    if(sim_time<=env.now):
        logger.warning(f"You have already ran simulation for this network! \n To create a new network use create_sc_net(), or specify the simulation time grater than {env.now} to run it further.")
        logger.info(f"Performance measures for the supply chain network are calculated and returned.")
    elif log_window is not None:
        assert isinstance(log_window, tuple) and len(log_window) == 2, "log_window must be a (start, stop) tuple"
        assert log_window[0] < log_window[1], "log_window start should be less than stop"
        assert log_window[0] >= 0, "log_window start should be greater than or equal to 0"
        assert log_window[1] <= sim_time, "log_window stop should be less than or equal to simulation time"
        log_start, log_stop = log_window
        global_logger.disable_logging()
        env.run(log_start)
        global_logger.enable_logging()
        env.run(log_stop)
        global_logger.disable_logging()
        if(sim_time > log_stop):
            env.run(sim_time)
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
        if(node.node_type == NodeType.INFINITE_SUPPLIER): # skip infinite suppliers
            continue
        node.stats.update_stats() # update stats for the node
        total_available_inv += node.inventory.level
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
        total_shortage[0] += node.stats.shortage[0]
        total_shortage[1] += node.stats.shortage[1]
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
        total_shortage[0] += node.stats.shortage[0]
        total_shortage[1] += node.stats.shortage[1]
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
    if log_window is not None:
        global_logger.enable_logging()
    max_key_length = max(len(key) for key in supplychainnet.keys()) + 1
    logger.info(f"Supply chain info:")
    for key in sorted(supplychainnet.keys()):
        logger.info(f"{key.ljust(max_key_length)}: {supplychainnet[key]}")
    return supplychainnet

def get_node_wise_performance(nodes_object_list):
    """
    Collect per-node performance statistics into a structured form.

    A library should return data, not print it (§6.3) — this function gathers
    each node's ``stats.get_statistics()`` dict and returns the rows as a list
    of dicts keyed by the metric name. Callers that want a tabular display can
    feed the result to ``pandas.DataFrame.from_records``; callers that want
    the previous text dump can pass it to :func:`format_node_wise_performance`
    or :func:`print_node_wise_performance`.

    Parameters:
        nodes_object_list (list): List of supply chain node objects.

    Returns:
        list[dict]: One dict per metric, with the key ``"Performance Metric"``
            holding the metric name and one entry per node holding the value.
            Returns an empty list when ``nodes_object_list`` is empty.
    """
    if not nodes_object_list:
        return []
    stats_per_node = {node.name: node.stats.get_statistics() for node in nodes_object_list}
    stat_keys = sorted(next(iter(stats_per_node.values())).keys())
    rows = []
    for key in stat_keys:
        row = {"Performance Metric": key}
        for name, node_stats in stats_per_node.items():
            row[name] = node_stats.get(key, "N/A")
        rows.append(row)
    return rows


def format_node_wise_performance(nodes_object_list, col_width: int = 25) -> str:
    """
    Format the per-node performance table as a fixed-width text block.

    Pure string helper — does not print. Build with a list and ``"\\n".join``
    to keep the formatter O(n) in total bytes (§5.4).

    Parameters:
        nodes_object_list (list): List of supply chain node objects.
        col_width (int): Width of each column. Defaults to 25.

    Returns:
        str: Multi-line table; an empty string when no nodes are provided.
    """
    if not nodes_object_list:
        return ""
    stats_per_node = {node.name: node.stats.get_statistics() for node in nodes_object_list}
    stat_keys = sorted(next(iter(stats_per_node.values())).keys())
    lines = []
    header_parts = ["Performance Metric".ljust(col_width)]
    for name in stats_per_node:
        header_parts.append(str(name).ljust(col_width))
    lines.append("".join(header_parts))
    for key in stat_keys:
        row_parts = [key.ljust(col_width)]
        for name, node_stats in stats_per_node.items():
            row_parts.append(str(node_stats.get(key, "N/A")).ljust(col_width))
        lines.append("".join(row_parts))
    return "\n".join(lines)


def print_node_wise_performance(nodes_object_list):
    """
    Print the per-node performance table to stdout.

    Thin wrapper around :func:`format_node_wise_performance`; kept as a
    library convenience for the existing notebooks/scripts that call it
    directly. Programmatic consumers should prefer
    :func:`get_node_wise_performance` (returns a list of dicts) so the table
    can be rendered however the caller prefers.

    Parameters:
        nodes_object_list (list): List of supply chain node objects.

    Returns:
        None
    """
    if not nodes_object_list:
        print("No nodes provided.")
        return
    print(format_node_wise_performance(nodes_object_list))


# ---------------------------------------------------------------------------
# §6.1: object-oriented wrapper around the netlist dict.
# ---------------------------------------------------------------------------
# ``create_sc_net`` / ``simulate_sc_net`` return / mutate a plain ``dict`` that
# mixes construction metadata (``nodes``, ``links``, ``env``, ``num_*``) with
# simulation results (``revenue``, ``profit``, ``shortage``). The two
# free-functions plus the dict have served the library well, but have the
# downsides flagged in REVIEW.md §6.1: no autocomplete, no typed getters, no
# clean separation between "before run" and "after run". ``Network`` is a thin
# additive wrapper that exposes the same data through attributes / methods,
# while keeping the underlying dict reachable as ``network.as_dict()`` so the
# legacy free-function API and the new OO API stay equivalent.
# ---------------------------------------------------------------------------
class Network:
    """
    Object-oriented wrapper around a SupplyNetPy network.

    ``Network`` owns the supply-chain dict that :func:`create_sc_net` returns
    and that :func:`simulate_sc_net` mutates with KPIs after a run. It exposes
    the construction metadata as plain attributes / dict views and the
    post-simulation KPIs through :attr:`results`, so a caller can tell the
    "before" and "after" states apart without inspecting key names.

    Construction (two interchangeable styles):

    .. code-block:: python

        # Style A — classmethod, takes the same args as create_sc_net.
        net = scm.Network.build(nodes=[...], links=[...], demands=[...])
        net.simulate(sim_time=200)
        print(net.results["profit"])

        # Style B — wrap an existing dict (e.g. produced by legacy code).
        sc = scm.create_sc_net(nodes=[...], links=[...], demands=[...])
        net = scm.Network(sc)
        net.simulate(sim_time=200)

    The wrapper does not duplicate state: ``net.as_dict()`` returns the same
    underlying dict the free-functions read and write, so legacy code that
    keeps a reference to it continues to see the latest values.
    """

    # Keys that ``simulate_sc_net`` writes onto the dict after a run. Used
    # to project the post-run KPIs into ``Network.results`` without having
    # to enumerate them at every call site.
    _RESULT_KEYS = (
        "available_inv", "avg_available_inv", "inventory_carry_cost",
        "inventory_spend_cost", "inventory_waste", "transportation_cost",
        "revenue", "total_cost", "profit", "demand_by_customers",
        "fulfillment_received_by_customers", "demand_by_site",
        "fulfillment_received_by_site", "total_demand",
        "total_fulfillment_received", "shortage", "backorders",
        "avg_cost_per_order", "avg_cost_per_item",
    )

    def __init__(self, supplychainnet: dict) -> None:
        """
        Wrap an existing supply-chain dict.

        Parameters:
            supplychainnet (dict): The dict returned by :func:`create_sc_net`.
                The wrapper holds a reference; mutations made via the legacy
                free-functions remain visible through this object.
        """
        if not isinstance(supplychainnet, dict) or "nodes" not in supplychainnet:
            global_logger.error("Network requires the dict produced by create_sc_net.")
            raise TypeError("Network requires the dict produced by create_sc_net.")
        self._sc = supplychainnet
        self._has_run = False

    @classmethod
    def build(cls, nodes: list, links: list, demands: list, env: simpy.Environment = None) -> "Network":
        """
        Build a network from netlists or pre-built domain objects.

        Identical signature to :func:`create_sc_net`; returns a wrapped
        :class:`Network` instead of the bare dict.

        Returns:
            Network: A network ready to simulate.
        """
        return cls(create_sc_net(nodes=nodes, links=links, demands=demands, env=env))

    # ---- Read-only construction metadata ----------------------------------
    @property
    def env(self) -> simpy.Environment:
        """The SimPy environment driving this network."""
        return self._sc["env"]

    @property
    def nodes(self) -> dict:
        """Mapping ``{node_id: Node}`` for every supplier / manufacturer / inventory node."""
        return self._sc["nodes"]

    @property
    def links(self) -> dict:
        """Mapping ``{link_id: Link}`` for every transportation edge."""
        return self._sc["links"]

    @property
    def demands(self) -> dict:
        """Mapping ``{demand_id: Demand}`` for every demand source."""
        return self._sc["demands"]

    @property
    def node_count(self) -> int:
        """Total number of inventory-bearing nodes (``num_of_nodes`` in the dict)."""
        return self._sc.get("num_of_nodes", 0)

    @property
    def link_count(self) -> int:
        """Total number of links (``num_of_links`` in the dict)."""
        return self._sc.get("num_of_links", 0)

    def node(self, node_id: str):
        """Lookup helper — raises ``KeyError`` if ``node_id`` is unknown."""
        return self._sc["nodes"][node_id]

    def link(self, link_id: str):
        """Lookup helper — raises ``KeyError`` if ``link_id`` is unknown."""
        return self._sc["links"][link_id]

    def demand(self, demand_id: str):
        """Lookup helper — raises ``KeyError`` if ``demand_id`` is unknown."""
        return self._sc["demands"][demand_id]

    # ---- Simulation entry point -------------------------------------------
    def simulate(self, sim_time, logging: bool = True, log_window=None) -> "Network":
        """
        Run the simulation and populate :attr:`results`.

        Mirrors :func:`simulate_sc_net`. Returns ``self`` so calls can chain
        (``Network.build(...).simulate(200)``).

        Parameters:
            sim_time (float): Stop time for ``env.run``.
            logging (bool): Whether logging is enabled for the whole run.
            log_window (tuple[float, float], optional): Window during which
                logging is enabled (logging is disabled outside).

        Returns:
            Network: ``self``.
        """
        simulate_sc_net(self._sc, sim_time, logging=logging, log_window=log_window)
        self._has_run = True
        return self

    # ---- Post-run KPIs ----------------------------------------------------
    @property
    def results(self) -> dict:
        """
        Aggregated KPIs from the most recent :meth:`simulate` call.

        Empty dict before ``simulate`` runs. The values share storage with
        the underlying ``supplychainnet`` dict — :class:`Network` projects
        the result keys here so callers do not have to know which dict keys
        are construction metadata vs run output.
        """
        return {k: self._sc[k] for k in self._RESULT_KEYS if k in self._sc}

    @property
    def has_run(self) -> bool:
        """Whether :meth:`simulate` has been called at least once."""
        return self._has_run

    # ---- Escape hatch -----------------------------------------------------
    def as_dict(self) -> dict:
        """
        Return the underlying ``supplychainnet`` dict.

        Provided for interop with the legacy free-function API; mutations to
        the returned dict are visible on this Network and vice versa.
        """
        return self._sc

    def __repr__(self) -> str:
        suffix = "" if not self._has_run else f", profit={self._sc.get('profit', '?')}"
        return (
            f"<Network nodes={self.node_count} links={self.link_count} "
            f"demands={len(self.demands)}{suffix}>"
        )