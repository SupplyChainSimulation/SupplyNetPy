from SupplyNetPy.Components import inventory
from SupplyNetPy.Components.logger import GlobalLogger
import random

node_types = ["retailer","distributor","warehouse","manufacturer","supplier"]
tranportation_types = ["road","air","water"]
global_logger = GlobalLogger()

class Link:
    """
    Represents a link between two nodes in the supply chain.
    """
    def __init__(self, from_node, to_node, lead_time, transportation_cost, link_distance,
                 transportation_type="road", products=[], max_load_capacity=0, min_shipment_quantity=0, 
                 probability_of_failure=0, co2_cost=0, edge_reliability=1, edge_resilience=1, edge_criticality=0,
                 iso_log=False,**kwargs):
            """
            Represents a link between two nodes in the supply chain.

            Args:
                from_node (str): The node where the link originates from.
                to_node (str): The node where the link terminates.
                lead_time (float): Time to deliver the shipment from one node to another.
                transportation_cost (float): Cost to transport goods from one node to another.
                link_distance (float): The distance between two nodes (by road/air).
                transportation_type (str): The mode of transportation (e.g., Road, Air).
                products (list): List of products (SKUs) being transported.
                max_load_capacity (float): The maximum quantity that can be shipped.
                min_shipment_quantity (float): The minimum quantity required to start shipment.
                probability_of_failure (float): Probability of unavailability of this link.
                co2_cost (float): Carbon emission cost.
                edge_reliability (float): Reliability of the edge (probability).
                edge_resilience (float): Resilience depends on the reliability of the edge and connected nodes.
                edge_criticality (str): Refers to the importance of the edge.

            Attributes:
                flow (float): Number of products transported via this link over a certain time period.
                co2_cost (float): Carbon emission cost.
                utilization (float): Link utilization over a certain time period.
                total_transport_cost (float): Cumulative transportation cost for shipments made till now.
                average_transport_cost (float): Average transport cost of the link (per day/month/quarter).
            """
        self.from_node = from_node
        self.to_node = to_node
        self.lead_time = lead_time
        self.transportation_cost = transportation_cost
        self.link_distance = link_distance
        self.transportation_type = transportation_type
        self.products = products
        self.max_load_capacity = max_load_capacity
        self.min_shipment_quantity = min_shipment_quantity
        
        self.probability_of_failure = probability_of_failure
        self.co2_cost = co2_cost
        self.edge_reliability = edge_reliability
        self.edge_resilience = edge_resilience
        self.edge_criticality = edge_criticality

        self.total_shipments = 0
        self.flow = []
        self.co2_cost = 0
        self.utilization = []
        self.total_transport_cost = 0
        self.average_transport_cost = []

        global global_logger
        if(iso_log):
            isologger = GlobalLogger(logger_name=f'Link:{self.from_node.node_id}-{self.to_node.node_id}',**kwargs)
            self.logger = isologger.logger
        else:
            self.logger = global_logger.logger


        # validate the link 
        if((self.from_node.node_type.lower() == "supplier" and self.to_node.node_type.lower()=="manufacturer") or
           (self.from_node.node_type.lower() == "manufacturer" and self.to_node.node_type.lower()=="distributor") or
           (self.from_node.node_type.lower() == "manufacturer" and self.to_node.node_type.lower()=="retailer") or
           (self.from_node.node_type.lower() in ["warehouse","distributor"] and self.to_node.node_type.lower()=="retailer")):
                # it is a valid link
                self.logger.info(f": A link from '{self.from_node.name}' to '{self.to_node.name}' is created.")
        else:
            raise ValueError(f"Cannot create a direct link from {self.from_node.node_type} to {self.to_node.node_type}!")
        
        # add/append myself in the list of suppliers of the 'to_node'
        self.to_node.supplier_list.append(self)

        # check for lead_time
        if(self.lead_time<0):
            raise ValueError(f"Link from node {self.from_node.name} to {self.to_node.name}: Link lead time cannot be negative!")
        
        # check for transportation_cost
        if(self.transportation_cost<0):
            raise ValueError(f"Link from node {self.from_node.name} to {self.to_node.name}: Transportation Cost cannot be negative!")
        
        # check for link_distance
        if(self.link_distance<=0):
            raise ValueError(f"Link from node {self.from_node.name} to {self.to_node.name}: Distance cannot be zero or negative!")
    
        global tranportation_types
        # check for transportation_type
        if(self.transportation_type not in tranportation_types):
            raise ValueError(f"Link from node {self.from_node.name} to {self.to_node.name}: Transportation type {self.transportation_type} not avaiable!")
        
        # check for max_load_capacity
        if(self.max_load_capacity<0):
            raise ValueError(f"Link from node {self.from_node.name} to {self.to_node.name}: Maximum load capcity cannot be negative!")
        
        # check for min_shipment_quantity
        if(self.min_shipment_quantity<0):
            raise ValueError(f"Link from node {self.from_node.name} to {self.to_node.name}: Minimum Shipment Quantity cannot be negative!")
        
        if(self.from_node.reorder_level<self.to_node.inventory.capacity):
            self.logger.warning(f"{self.from_node.node_id}: Reorder level ({self.from_node.reorder_level}) is too low to keep up with capacity of {self.to_node.name} (cap={self.to_node.inventory.capacity})! This can lead to a deadlock!")
            #raise ValueError(f"Reorder level of {self.from_node.name} ({self.from_node.reorder_level}) is too low to keep up with capacity of {self.to_node.name} (cap={self.to_node.inventory.capacity})! This can lead to a deadlock!")
    
    def get_info(self):
        """
        Displays link information
        """
        self.logger.info(f"Link from: {self.from_node.name}")
        self.logger.info(f"to: {self.to_node.name}")
        self.logger.info(f"Lead time: {self.lead_time}")
        self.logger.info(f"Tranportation cost: {self.transportation_cost}")
        self.logger.info(f"Distance: {self.link_distance} Km")
        self.logger.info(f"Transport type: {self.transportation_type}")
        self.logger.info(f"Load capacity: {self.max_load_capacity}")
        self.logger.info(f"Min shipment quantity: {self.min_shipment_quantity}")
        
        self.logger.info(f"Link failuer probability: {self.probability_of_failure}")
        self.logger.info(f"CO2 cost: {self.co2_cost}")
        self.logger.info(f"Reliability: {self.edge_reliability}")
        self.logger.info(f"Resilience: {self.edge_resilience}")
        self.logger.info(f"Criticality: {self.edge_criticality}")

        return f"Link from: {self.from_node.name}, to: {self.to_node.name}\n Lead time: {self.lead_time}\n Tranportation cost: {self.transportation_cost} \n Tranportation cost: {self.transportation_cost} \n Distance: {self.link_distance} Km \n Transport type: {self.transportation_type} \n Load capacity: {self.max_load_capacity} \n Min shipment quantity: {self.min_shipment_quantity} \n Link failuer probability: {self.probability_of_failure} \n CO2 cost: {self.co2_cost} \n Reliability: {self.edge_reliability} \n Resilience: {self.edge_resilience} \n Criticality: {self.edge_criticality} "
              
    def calculate_stats(self, timenow):
        """
        This function calculates performance measures of the link
        Attributes:
        - timenow (env.now): current time in simulation
        """
        self.total_shipments += 1
        self.flow.append([timenow, self.total_shipments/timenow]) # number of shipments per unit time
        self.utilization.append([timenow, self.lead_time*self.total_shipments/timenow]) # (units of time taken to make shipments)/(total time)
        self.total_transport_cost += self.transportation_cost # it is assumed that cost per shipment is constant and does not depend on number of units shipped - this can be changed
        self.average_transport_cost.append([timenow, self.total_transport_cost/(self.total_shipments)])

    def get_stats(self):
        """
        Print performance measures of this link.
        """
        self.logger.info(f"Performance measures for link: from {self.from_node.name} to {self.to_node.name}:")
        self.logger.info(f"Total shipments made: {self.total_shipments}")
        self.logger.info(f"Link flow [time, flow (#shipments/day)]: {self.flow[-1]}")
        self.logger.info(f"Link utilization [time, utilization(%)]: {self.utilization[-1]} ")
        self.logger.info(f"Total transport cost: {self.total_transport_cost} Rs")
        self.logger.info(f"Average transport cost [time, average cost]: {self.average_transport_cost[-1]} Rs")

        return f"Performance measures for link: from {self.from_node.name} to {self.to_node.name}: \n Total shipments made: {self.total_shipments} \n Link flow [time, flow (#shipments/day)]: {self.flow[-1]} \n Link utilization [time, utilization(%)]: {self.utilization[-1]} \n Total transport cost: {self.total_transport_cost} Rs \n Average transport cost [time, average cost]: {self.average_transport_cost[-1]} Rs"

class Node:
    """
    Represents a base class for all supply chain nodes.
    This class provides common attributes and methods that are shared by all types of supply chain nodes,
    such as retailers, suppliers, distributors and manufacturers.
    """
    def __init__(self, env, name, node_id, node_type, location,
                 supply_reliability=1, node_resilience=1, node_criticality=1, inventory=None,
                 iso_log=False,**kwargs):
        """
        Initialize the supply chain Node.
        Parameters:
        - env : SimPy Environment variable
        - name (str): The name of the supply chain node.
        - node_id (int): The unique identifier for the supply chain node.
        - node_type (str): The type of the supply chain node (e.g., retailer, supplier, manufacturer).
        - location (str): The location of the supply chain node.
        - supply_reliability (float): The probability of supply reliability, which depends on the number of 
                                      demand and supply nodes connected.
        - node_resilience (float): The resilience of the node, which depends on the reliability of its supply.
        - node_criticality (str): The criticality of the node, referring to its importance in the supply chain flow.
        - inventory (Inventory): inventory held by this supply chain node

        Performance Measures (output):
        - total_sale (int): number of units sold
        - throughput (float): number of units sold per unit time (per hour/day/month)
        - average_sale (float): average number of units sold (per day/month/quarter)
        - net_profit (float): net profit generated (total)
        - average_net_profit (float): average net profit generated (per day/month/quarter)
        - node_cost (float): cost of manufacturing, moving, loading, unloading, sorting etc.
        """
        self.env = env
        self.name = name
        self.node_id = node_id
        self.node_type = node_type
        self.location = location
        
        self.supply_reliability = supply_reliability
        self.node_resilience = node_resilience
        self.node_criticality = node_criticality

        self.inventory = inventory
        self.ordered = False

        self.total_sale = 0
        self.throughput = 0
        self.average_sale = []
        self.profit = 0
        self.average_profit = []
        self.node_cost = 0

        global global_logger
        if(iso_log):
            isologger = GlobalLogger(logger_name=f'node:{self.name}',**kwargs)
            self.logger = isologger.logger
        else:
            self.logger = global_logger.logger

        global node_types
        # check for node type
        if(self.node_type.lower() not in node_types):
            raise ValueError(f"Node type {self.node_type} not supported for node {self.name}!")
    
    def get_info(self):
        """
        Displays node information and its parameter values
        """
        self.logger.info(f"Name: {self.name}")
        self.logger.info(f"ID: {self.node_id}")
        self.logger.info(f"Type: {self.node_type}")
        self.logger.info(f"Location: {self.location}")
        self.logger.info(f"Reliability: {self.supply_reliability}")
        self.logger.info(f"Resilience: {self.node_resilience}")
        self.logger.info(f"Criticality: {self.node_criticality}")
        self.logger.info(f"Inventory capacity: {self.inventory.capacity}") # type: ignore
        self.logger.info(f"Inventory holding cost: {self.inventory.holding_cost}") # type: ignore
        self.logger.info(f"Inventory reorder level: {self.inventory.reorder_level}") # type: ignore
        self.logger.info(f"Inventory reorder period: {self.inventory.reorder_period}") # type: ignore
        self.logger.info(f"Inventory type: {self.inventory.inventory_type}") # type: ignore
        self.logger.info(f"Inventory replenishment policy: {self.inventory.replenishment_policy}") # type: ignore

        return f"Name: {self.name} \n ID: {self.node_id} \n Type: {self.node_type} \n Location: {self.location} \n Reliability: {self.supply_reliability} \n Resilience: {self.node_resilience} \n Criticality: {self.node_criticality} \n Inventory capacity: {self.inventory.capacity} \n Inventory holding cost: {self.inventory.holding_cost} \n Inventory reorder level: {self.inventory.reorder_level} \n Inventory reorder period: {self.inventory.reorder_period} \n   Inventory type: {self.inventory.inventory_type} \n Inventory replenishment policy: {self.inventory.replenishment_policy}" # type: ignore

    def calculate_stats(self,timenow):
        """
        Calculate performance measures for this node
        """
        self.throughput = self.total_sale/timenow
        self.average_sale = self.total_sale/timenow
        if(self.node_type=="retailer"):
            self.profit = self.total_sale*self.inventory.products[0].profit # type: ignore
            self.average_profit = self.profit/timenow
        else:
            self.profit = 0
            self.average_profit = 0

    def get_stats(self):
        """
        Print performance measures of this node.
        """
        self.logger.info(f"Performance measures of node '{self.name}'")
        self.logger.info(f"Throughput: {self.throughput}")
        self.logger.info(f"Total units sold:{self.total_sale} units")
        self.logger.info(f"Average Sale: {self.average_sale} units/day")
        self.logger.info(f"Inventory holding costs = {sum(self.inventory.stats_inventory_hold_costs)}") # type: ignore
        self.logger.info(f"Profit: {self.profit} Rs")
        self.logger.info(f"Average profit: {self.average_profit} Rs/day")

        return  f"Performance measures of node '{self.name}' \n Throughput: {self.throughput} \n Total units sold:{self.total_sale} units \n Average Sale: {self.average_sale} units/day \n Inventory holding costs = {sum(self.inventory.stats_inventory_hold_costs)} \n Profit: {self.profit} Rs \n Average profit: {self.average_profit} Rs/day" # type: ignore

    def monitor_inventory(self,env,suppliers_list):
        """
        Monitor the inventory accourding to the replenishment policy.
        Parameters:
        env : Simpy env
        suppliers_list (list) = List of links to this node (this node's suppliers)
        """
        # check if this node is connected in the network!
        if(self.node_type!="supplier" and len(suppliers_list)==0):
            self.logger.warning(f": {self.env.now:.4f}: ({self.node_id}): has no suppliers!")
            while(True):
                # calculate today's inventory holding cost
                todays_hold_cost = self.inventory.holding_cost*self.inventory.level() # type: ignore
                self.inventory.stats_inventory_hold_costs.append(todays_hold_cost)  # type: ignore
                # wait for a day
                yield self.env.timeout(1)
                self.logger.info(f": {self.env.now:.4f}: ({self.node_id}): inventory level = {self.inventory.level()}.") # type: ignore
            #raise ValueError(f"Node {self.name} ({self.node_id}) is not connected in the SC network!!")
        
        # node behaviour if the replenishment policy is sS
        if(self.inventory.replenishment_policy=="sS"): # type: ignore
            while(True):
                # calculate today's inventory holding cost
                todays_hold_cost = self.inventory.holding_cost*self.inventory.level() # type: ignore
                self.inventory.stats_inventory_hold_costs.append(todays_hold_cost)  # type: ignore
                # wait for a day
                yield self.env.timeout(1)
                # check inventory levels and any previously pending orders
                if(self.inventory.level()<self.inventory.reorder_level and not self.ordered):  # type: ignore
                    # place an order 
                    order_quantity = self.inventory.capacity - self.inventory.level()  # type: ignore
                    # randomly select a supplier
                    if(len(suppliers_list)>1):
                        supplier_link = suppliers_list[random.randint(0,len(suppliers_list)-1)]
                    else:
                        supplier_link = suppliers_list[0]
                    self.env.process(self.place_order(env,supplier_link,order_quantity))
                    self.ordered = True
                self.logger.info(f": {self.env.now:.4f}: ({self.node_id}): inventory level = {self.inventory.level()}.") # type: ignore

    def place_order(self, env, supplier_link, quantity, product=None):
        """
        Place an order to a supplier, and receive shipment
        Parameters:
        - supplier_link (Link): The supplier link to place the order with.
        - product (Product): The product to be ordered.
        - quantity (int): The quantity of the product to be ordered.
        """
        self.logger.info(f": {self.env.now:.4f}: ({self.node_id}): Placing order to '{supplier_link.from_node.name}'...")
        # Get product units from supplier's Inventory
        if(quantity<=supplier_link.from_node.inventory.level()):
            self.logger.info(f": {self.env.now:.4f}: ({self.node_id}): placed an order to '{supplier_link.from_node.name}' for {quantity} units.")
            supplier_link.from_node.inventory.get(quantity)
            supplier_link.from_node.total_sale += quantity # update stats for supplier node
            # shipment is on the road, wait for 'lead_time' to receive it
            yield self.env.timeout(supplier_link.lead_time)
            self.logger.info(f": {self.env.now:.4f}: ({self.node_id}): got {quantity} units from '{supplier_link.from_node.name}'.")
            self.inventory.put(quantity) # type: ignore
            self.ordered = False
            # calculate stats for the link
            supplier_link.calculate_stats(env.now)
        else:
            self.logger.info(f": {self.env.now:.4f}: ({self.node_id}): {quantity} units not avaliable at '{supplier_link.from_node.name}'. Order not placed!")
            self.ordered = False

class Retailer(Node):
    """
    Represents a Retailer node in the supply chain.
    This class inherits from the Node class and adds specific parameters related to retailing.
    Parameters:
    - inventory (Inventory): The inventory associated with the retailer.
    """
    def __init__(self, env, name, node_id, location, products,
                 inv_capacity, inv_holding_cost, reorder_level, inv_replenishment_policy = "sS",
                 supply_reliability=1, node_resilience=1, node_criticality=1, **kwargs):
        """
        Initialize the Retailer.
        Parameters:
        - supplier_list (list): List of suppliers to this Retailer node
        """
        self.env = env
        self.supplier_list = []
        self.reorder_level = reorder_level
        self.inventory = inventory.Inventory(env, capacity=inv_capacity, holding_cost=inv_holding_cost,
                                               reorder_level=self.reorder_level, replenishment_policy=inv_replenishment_policy, products=products) 
        super().__init__(env=env, name=name, node_id=node_id, node_type="retailer", location=location, supply_reliability=supply_reliability,
                         node_resilience=node_resilience,node_criticality=node_criticality, inventory=self.inventory, **kwargs)

        self.env.process(super().monitor_inventory(env,self.supplier_list))
    
    # Retailer's responsibilities
    # (1) inventory management
    # (2) track real demand

class Distributor(Node):
    """
    Represents a Distributor node in the supply chain.
    This class inherits from the Node class and adds specific parameters related to warehousing.
    Parameters:
    - inventory (Inventory): The inventory associated with the distributor.
    """
    def __init__(self, env, name, node_id, location, products,
                 inv_capacity, inv_holding_cost, reorder_level, inv_replenishment_policy = "sS",
                 supply_reliability=1, node_resilience=1, node_criticality=1, **kwargs):
        """
        Initialize the Distributor.
        Parameters:
        - supplier_list (list): List of suppliers to this Distributor node
        """
        self.env = env
        self.supplier_list = []
        self.reorder_level = reorder_level
        self.inventory = inventory.Inventory(env, capacity=inv_capacity, holding_cost=inv_holding_cost, reorder_level = self.reorder_level,
                                               replenishment_policy=inv_replenishment_policy, products=products) # type: ignore
        
        super().__init__(env=env, name=name, node_id=node_id, node_type="Distributor", location=location, supply_reliability=supply_reliability, 
                         node_resilience=node_resilience, node_criticality=node_criticality, inventory=self.inventory, **kwargs)

        self.env.process(super().monitor_inventory(env,self.supplier_list))
    
    # Distributor's responsibilities
    # (1) Warehouse management (e.g. loading/unloading, sorting, order assembly)
    # (2) inventory management

class Manufacturer(Node):
    """
    Represents a manufacturer in the supply chain.
    This class inherits from the Node class and adds specific parameters related to manufacturing.
    Parameters:
    - production_cost (float): The cost of production per unit.
    - production_level (int): The current production level of the manufacturer.
    - inventory (Inventory): The inventory associated with the manufacturer.
    """

    def __init__(self, env, name, node_id, location, production_cost, production_level, products,
                 inv_capacity, inv_holding_cost, reorder_level, inv_replenishment_policy = "sS", manufacturing_delay = 0,
                 supply_reliability=1, node_resilience=1, node_criticality=1, **kwargs):
        """
        Initialize the Manufacturer.
        Parameters:
        - production_cost (float): The cost of production per unit.
        - production_level (int): The current production level of the manufacturer.
        - supplier_list (list): List of suppliers to this Manufacturer node
        """
        self.env = env
        self.production_cost = production_cost
        self.production_level = production_level
        self.supplier_list = []
        self.manufacturing_delay = manufacturing_delay
        self.reorder_level = reorder_level
        self.inventory = inventory.Inventory(env, capacity=inv_capacity, holding_cost=inv_holding_cost, reorder_level=self.reorder_level,
                                               replenishment_policy=inv_replenishment_policy,products=products) # type: ignore
        
        super().__init__(env=env, name=name, node_id=node_id, node_type="Manufacturer", location=location, supply_reliability=supply_reliability, 
                         node_resilience=node_resilience, node_criticality=node_criticality, inventory=self.inventory, **kwargs)

        self.env.process(super().monitor_inventory(env,self.supplier_list))
    
    # Manufacturer responsibilities
    # (1) procurement
    # (2) manufacturing
    # (3) inventory management

    # -To do-

class Supplier(Node):
    """
    Represents a Supplier node in the supply chain.
    This class inherits from the Node class and adds specific parameters related to providing raw material to manufacturer.
    Parameters:
    - inventory (Inventory): The inventory associated with the retailer.
    """
    def __init__(self, env, name, node_id, location,
                 inv_capacity, inv_holding_cost, reorder_level, inv_replenishment_policy = "sS",
                 supply_reliability=1, node_resilience=1, node_criticality=1, **kwargs):
        """
        Initialize the Supplier.
        Parameters:
        - 
        """
        self.env = env
        self.reorder_level = reorder_level
        self.inventory = inventory.Inventory(env, capacity=inv_capacity, holding_cost=inv_holding_cost,
                                               replenishment_policy=inv_replenishment_policy) # type: ignore
        
        super().__init__(env=env, name=name, node_id=node_id, node_type="Supplier", location=location, supply_reliability=supply_reliability, 
                         node_resilience=node_resilience, node_criticality=node_criticality, inventory=self.inventory, **kwargs)
        self.env.process(self.monitor_inventory(self.env))
    # supplier responsibilities
    # (1) obtain/mine raw material
    # (2) inventory management
    
    # -To do-
    # supplier periodically updates the inventory, making raw material available
    def monitor_inventory(self,env): # monitory daily and refill sa soon as the inv levels drops
        while(True):
            yield self.env.timeout(1)
            if(self.inventory.level()<self.inventory.capacity):
                quantity = self.inventory.capacity - self.inventory.level()
                self.inventory.put(quantity)

class Demand:
    """
    To model supply chain demand as a distribution.
    """
    def __init__(self,env,arr_dist,arr_params,node,demand_dist,demand_params,iso_log=False,**kwargs):
        """
        Create demand to the supply chain as per given distribution.
        Parameters:
        - arrival_distribution (str): Distribution to model demand (e.g. Poisson, Geometric, Triangle).
        - arrival_distribution_param (list): List of input parameters for distribution (e.g. arrival rate (lambda))
        """
        self.env = env
        self.distribution = arr_dist
        self.distribution_params = arr_params
        self.demand_node = node
        self.demand_distribution = demand_dist
        self.demand_params = demand_params
        self.customer_id = 0

        self.stats_customer_returned = 0

        global global_logger
        if(iso_log):
            isologger = GlobalLogger(logger_name=f'node:{self.name}',**kwargs) # type: ignore
            self.logger = isologger.logger
        else:
            self.logger = global_logger.logger

    def get_info(self):
        """
        Displays demand information
        """
        self.logger.info(f"This demand is generated for node {self.demand_node.name}.")
        self.logger.info(f"Customer arrival is modeled by {self.distribution} distribution.")
        self.logger.info(f"The distribution parameters are {self.distribution_params}.")
        self.logger.info(f"Per customer demand is modeled using {self.demand_distribution} distribution.")
        self.logger.info(f"parameters are: {self.demand_params}")
        
        return f"This demand is generated for node {self.demand_node.name}. \n Customer arrival is modeled by {self.distribution} distribution. \n The distribution parameters are {self.distribution_params}. \n Per customer demand is modeled using {self.demand_distribution} distribution. \n parameters are: {self.demand_params}"

    def customer_demand(self,env):
        """
        Model customer demand accourding to given distribution. 
        For example, if demand distribution is "Uniform" between LOW number of units and HIGH
        number of units then a customer orders N units choosen uniformly from range [LOW,HIGH]
        """
        self.customer_id += 1
        if(self.demand_distribution=="Uniform"):
            low = self.demand_params[0]
            high = self.demand_params[1]
            customer_demand = random.randint(low,high)
            self.logger.info(f": {self.env.now:.4f}: (Customer {self.customer_id}): ordering {customer_demand} units from {self.demand_node.name}.")
            if(customer_demand<self.demand_node.inventory.level()):
                yield self.demand_node.inventory.get(customer_demand)
                self.demand_node.total_sale += customer_demand # update stats for demand_node
                self.logger.info(f": {self.env.now:.4f}: (Customer {self.customer_id}): got {customer_demand} units from {self.demand_node.name}.")
            else:
                self.logger.info(f": {self.env.now:.4f}: (Customer {self.customer_id}): {customer_demand} units not available at {self.demand_node.name}!")
                self.stats_customer_returned += 1

    def poisson_arrivals(self, env):
        """
        Model customers' arrival at demand_node as Poisson process.
        """
        while(True):
            lam = self.distribution_params[0]
            self.env.process(self.customer_demand(env))
            t = random.expovariate(lambd=lam)
            yield env.timeout(t)

def createSC(products,nodes,links,demands):
    num_suppliers = 0
    num_manufacturers = 0
    num_distributors = 0
    num_retailers = 0
    for node in nodes:
        if node.node_type.lower() == "supplier":
            num_suppliers += 1
        if node.node_type.lower() == "manufacturer":
            num_manufacturers += 1
        if node.node_type.lower() == "distributor":
            num_distributors += 1
        if node.node_type.lower() == "retailer":
            num_retailers += 1

    supplychainnet = {"num_of_nodes":len(nodes),
                      "num_suppliers":num_suppliers,
                      "num_manufacturers":num_manufacturers,
                      "num_distributors":num_distributors,
                      "num_retailers":num_retailers,
                      "num_of_edges":len(links),
                      "nodes":nodes,
                      "edges":links, 
                      "demand":demands,
                      "products": products}
    return supplychainnet