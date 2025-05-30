from SupplyNetPy.Components.logger import GlobalLogger
import simpy
import copy
import random
# global variables
global_logger = GlobalLogger() # create a global logger

class RawMaterial():
    """
    RawMaterial class represents a raw material in the supply network.

    Parameters:
        ID (str): ID of the raw material (alphanumeric)
        name (str): name of the raw material
        extraction_quantity (float): quantity of the raw material that is extracted in extraction_time
        extraction_time (float): time to extract the raw material 
        mining_cost (float): mining cost of the raw material (per item)
        cost (float): selling cost of the raw material (per item)

    Functions:
        __init__: initializes the raw material object
        __str__: returns the name of the raw material
        __repr__: returns the name of the raw material
        get_info: returns a dictionary containing details of the raw material

    """
    def __init__(self, ID: str, 
                 name: str, 
                 extraction_quantity: float, 
                 extraction_time: float, 
                 mining_cost: float,
                 cost: float) -> None:
        """
        Initialize the raw material object.

        Parameters:
            ID (str): ID of the raw material (alphanumeric)
            name (str): name of the raw material
            extraction_quantity (float): quantity of the raw material that can be extracted in extraction_time
            extraction_time (float): time to extract the raw material
            mining_cost (float): mining cost of the raw material (per item)
            cost (float): selling cost of the raw material (per item)

        Returns:
            None
        """
        if(extraction_quantity <= 0):
            global_logger.logger.error("Extraction quantity cannot be zero or negative.")
            raise ValueError("Extraction quantity cannot be negative.")
        if(extraction_time < 0):
            global_logger.logger.error("Extraction time cannot be negative.")
            raise ValueError("Extraction time cannot be negative.")
        if(cost <= 0):
            global_logger.logger.error("Cost cannot be zero or negative.")
            raise ValueError("Cost cannot be negative.")

        self.ID = ID # ID of the raw material (alphanumeric)
        self.name = name # name of the raw material
        self.extraction_quantity = extraction_quantity # quantity of the raw material that can be extracted in extraction_time
        self.extraction_time = extraction_time # time to extract the raw material
        self.mining_cost = mining_cost
        self.cost = cost # mining cost of the raw material

    def __str__(self):
        """
        Return the name of the raw material.

        Returns:
            str: The name of the raw material.
        """
        return self.name

    def __repr__(self):
        """
        Return the name of the raw material.

        Returns:
            str: The name of the raw material.
        """
        return self.name
    
    def get_info(self):
        """
        Get the details of the raw material.

        Returns:
            dict: dictionary containing details of the raw material
        """
        return {"ID": self.ID, 
                "name": self.name, 
                "extraction_quantity": self.extraction_quantity, 
                "extraction_time": self.extraction_time, 
                "mining_cost": self.mining_cost,
                "cost": self.cost}

class Product():
    """
    Product class represents a product in the supply network.

    Parameters:
        ID (str): ID of the product (alphanumeric)
        name (str): name of the product
        manufacturing_cost (float): manufacturing cost of the product
        manufacturing_time (int): time to manufacture the product
        sell_price (float): price at which the product is sold
        buy_price (float): price at which the product is bought
        raw_materials (list): list of raw materials and respective quantity required to manufacture one unit of the product
        units_per_cycle (int): number of units manufactured per manufacturing cycle

    Functions:
        __init__: initializes the product object
        __str__: returns the name of the product
        __repr__: returns the name of the product
        get_info: returns a dictionary containing details of the product
    """
    def __init__(self, ID: str, 
                 name: str, 
                 manufacturing_cost: float, 
                 manufacturing_time: int, 
                 sell_price: float, 
                 raw_materials: list, 
                 units_per_cycle: int, 
                 buy_price: float = 0) -> None:
        """
        Initialize the product object.

        Parameters:
            ID (str): ID of the product (alphanumeric)
            name (str): name of the product
            manufacturing_cost (float): manufacturing cost of the product
            manufacturing_time (int): time to manufacture the product
            sell_price (float): price at which the product is sold
            buy_price (float): price at which the product is bought
            raw_materials (list): list of raw materials and respective quantity required to manufacture one unit of the product
            units_per_cycle (int): number of units manufactured per cycle
        
        Returns:
            None
        """
        if(manufacturing_cost <= 0):
            global_logger.logger.error("Manufacturing cost cannot be zero or negative.")
            raise ValueError("Manufacturing cost cannot be negative.")
        if(manufacturing_time < 0):
            global_logger.logger.error("Manufacturing time cannot be negative.")
            raise ValueError("Manufacturing time cannot be negative.")
        if(sell_price <= 0):
            global_logger.logger.error("Sell price cannot be zero or negative.")
            raise ValueError("Sell price cannot be negative.")
        if(buy_price < 0):
            global_logger.logger.error("Buy price cannot be negative.")
            raise ValueError("Buy price cannot be negative.")
        if(units_per_cycle <= 0):
            global_logger.logger.error("Units per cycle cannot be zero or negative.")
            raise ValueError("Units per cycle cannot be negative.")

        self.ID = ID # ID of the product (alphanumeric)
        self.name = name # name of the product
        self.manufacturing_cost = manufacturing_cost # manufacturing cost of the product
        self.manufacturing_time = manufacturing_time # time (days) to manufacture the product
        self.sell_price = sell_price # price at which the product is sold
        self.buy_price = buy_price # price at which the product is bought, (default: 0). It is used by InventoryNode buy the product at some price and sell it at a higher price.   
        self.raw_materials = raw_materials # list of raw materials and quantity required to manufacture a single product unit
        self.units_per_cycle = units_per_cycle # number of units manufactured per cycle

    def __str__(self):
        """
        Get the string representation of the product.

        Returns:
            str: The name of the product.
        """
        return self.name

    def __repr__(self):
        """
        Get the string representation of the product.

        Returns:
            str: The name of the product.
        """
        return self.name
    
    def get_info(self):
        """
        Get the details of the product.

        Returns:
            dict: dictionary containing details of the product
        """
        return {"ID": self.ID, 
                "name": self.name, 
                "manufacturing_cost": self.manufacturing_cost, 
                "manufacturing_time": self.manufacturing_time, 
                "sell_price": self.sell_price, 
                "buy_price": self.buy_price, 
                "raw_materials": self.raw_materials, 
                "units_per_cycle": self.units_per_cycle}

default_raw_material = RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=30, extraction_time=3, mining_cost=0.3, cost=1) # create a default raw material
default_product = Product(ID="P1", name="Product 1", manufacturing_cost=50, manufacturing_time=3, sell_price=341, raw_materials=[{"raw_material": default_raw_material, "quantity": 3}], units_per_cycle=30) # create a default product

class PerishableInventory(simpy.Container):
    """
    Represents a perishable inventory in the supply network. It inherits from simpy.Container.

    Parameters:
        env (simpy.Environment): simulation environment
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        shelf_life (int): shelf life of the product
        replenishment_policy (str): replenishment policy for the inventory

    Functions:
        __init__: initializes the perishable inventory object
        put: overrides the put method of simpy.Container
        get: overrides the get method of simpy.Container
        remove_expired: removes expired products from the perishable inventory
    """

    def __init__(self, env: simpy.Environment, 
                 capacity: int, 
                 initial_level: int, 
                 shelf_life: int, 
                 replenishment_policy: str) -> None:
        """
        Initialize the perishable inventory object.

        Parameters:
            env (simpy.Environment): simulation environment
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            shelf_life (int): shelf life of the product
            replenishment_policy (str): replenishment policy for the inventory

        Attributes:
            env (simpy.Environment): simulation environment
            shelf_life (int): shelf life of the product
            replenishment_policy (str): replenishment policy for the inventory
            waste (list): list to store wasted products
            perish_queue (list): list to store perishable products in the format of (manufacturing date, amount)
            logger (GlobalLogger): global logger
        
        Returns:
            None
        """
        if(shelf_life <= 0):
            global_logger.logger.error("Shelf life cannot be zero or negative.")
            raise ValueError("Shelf life cannot be negative.")
        if(replenishment_policy not in ["sS", "periodic"]):
            global_logger.logger.error(f"Invalid replenishment policy. {replenishment_policy} is not yet available.")
            raise ValueError(f"Invalid replenishment policy. {replenishment_policy} is not yet available.")

        super().__init__(env, capacity, initial_level)
        self.env = env # simulation environment
        self.shelf_life = shelf_life # shelf life of the product
        self.replenishment_policy = replenishment_policy # replenishment policy for the inventory
        self.waste = [] # list to store wasted products
        self.perish_queue = [(0,initial_level)] # list to store perishable products
        self.logger = global_logger.logger # global logger
        self.env.process(self.remove_expired()) # start the process to remove expired products

    def put(self,amount:int,manufacturing_date:int):
        """
        Overriding the put method of simpy.Container.
        Records the amount and manufacturing date in the perish_queue.

        Parameters:
            amount (int): The amount to put in the inventory.
            manufacturing_date (int): The manufacturing date of the product.

        Returns:
            None
        """
        # insert the (manufacturing date, amount) in perish_queue in sorted order
        inserted = False
        for i in range(len(self.perish_queue)):
            if self.perish_queue[i][0] > manufacturing_date:
                self.perish_queue.insert(i, (manufacturing_date, amount))
                inserted = True
                break
        if(not inserted):
            self.perish_queue.append((manufacturing_date, amount))
        super().put(amount)
    
    def get(self, amount):
        """
        Overriding the get method of simpy.Container.
        Removes the specified amount from the perish_queue.

        Parameters:
            amount (int): The amount to get from the inventory.

        Returns:
            tuple: A tuple containing the 'get' event and the manufacturing date list.
        """
        if(amount==0):
            return
        man_date_ls = [] # manufacturing date list (similar to perish_queue)
        x_amount = amount
        while x_amount>0: # get the amount from the perish queue, old products first
            if(len(self.perish_queue)>0):
                if(self.perish_queue[0][1] <= x_amount):
                    man_date_ls.append((self.perish_queue[0][0],self.perish_queue[0][1]))
                    x_amount -= self.perish_queue[0][1]
                    self.perish_queue.pop(0)
                else:
                    man_date_ls.append((self.perish_queue[0][0], x_amount))
                    self.perish_queue[0] = (self.perish_queue[0][0], self.perish_queue[0][1] - x_amount) 
                    x_amount = 0
            else:
                break
        return super().get(amount), man_date_ls
    
    def remove_expired(self):
        """
        Remove expired products from the perishable inventory.

        Parameters:
            None

        Returns:    
            None
        """
        while True:
            yield self.env.timeout(1)
            # remove the expired products
            while len(self.perish_queue)>0 and self.env.now - self.perish_queue[0][0] >= self.shelf_life:
                self.logger.info(f"{self.env.now:.4f}:{self.perish_queue[0][1]} units expired.")
                self.waste.append((self.env.now, self.perish_queue[0][1])) # add to wasted products
                self.perish_queue.pop(0) # remove from perish queue
                if(self.waste[-1][1]>0):
                    super().get(self.waste[-1][1]) # remove from the inventory
                self.logger.info(f"Current inventory levels:{self.level}")
                

class Inventory():
    """
    Inventory class represents an inventory in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        shelf_life (int): shelf life of the product
        replenishment_policy (str): replenishment policy for the inventory
        type (str): type of the inventory (non-perishable/perishable)

    Functions:
        __init__: initializes the inventory object
        get_info: returns a dictionary containing details of the inventory
        record_inventory_levels: records inventory levels every day
    """
    def __init__(self, env: simpy.Environment, 
                 capacity: int, 
                 initial_level: int, 
                 replenishment_policy: str,
                 shelf_life: int = 0,
                 type: str = "non-perishable") -> None:
        """
        Initialize the inventory object.

        Parameters:
            env (simpy.Environment): simulation environment
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            replenishment_policy (str): replenishment policy for the inventory
            type (str): type of the inventory (non-perishable/perishable)
            shelf_life (int): shelf life of the product
        
        Attributes:
            env (simpy.Environment): simulation environment
            capacity (int): maximum capacity of the inventory
            init_level (int): initial inventory level
            level (int): current inventory level
            inventory (simpy.Container): inventory container
            replenishment_policy (str): replenishment policy for the inventory
            instantaneous_levels (list): list to store inventory levels at regular intervals
            inventory_spend (list): list to store inventory replenishment costs. Every record contains (time of order, cost of order)

        Returns:
            None
        """
        if(initial_level > capacity):
            global_logger.logger.error("Initial level cannot be greater than capacity.")
            raise ValueError("Initial level cannot be greater than capacity.")
        if(initial_level < 0):
            global_logger.logger.error("Initial level cannot be negative.")
            raise ValueError("Initial level cannot be negative.")
        if(capacity <= 0):
            global_logger.logger.error("Capacity cannot be zero or negative.")
            raise ValueError("Capacity cannot be negative.")
        if(replenishment_policy not in ["sS", "periodic"]):
            global_logger.logger.error(f"Invalid replenishment policy. {replenishment_policy} is not yet available.")
            raise ValueError(f"Invalid replenishment policy. {replenishment_policy} is not yet available.")

        self.env = env # simulation environment
        self.capacity = capacity # maximum capacity of the inventory
        self.init_level = initial_level # initial inventory level
        self.level = initial_level # initial inventory level
        self.inventory = simpy.Container(env=self.env,capacity=self.capacity, init=self.init_level) # create an inventory
        self.type = type
        if(self.type=="perishable"):
            self.inventory = PerishableInventory(env=self.env, capacity=self.capacity, initial_level=self.init_level, shelf_life=shelf_life, replenishment_policy=replenishment_policy)
        self.replenishment_policy = replenishment_policy # replenishment policy for the inventory
        self.instantaneous_levels = []
        self.inventory_spend = [] # inventory replenishment costs. Calculated as (order size) * (product buy cost). Every record contains (time of order, cost of order)
        self.env.process(self.record_inventory_levels()) # start recording the inventory levels
    
    def get_info(self):
        """
        Get the details of the inventory.

        Returns:
            dict: dictionary containing details of the inventory
        """
        return {"capacity": self.capacity, "level": self.level, "replenishment_policy": self.replenishment_policy}
    
    def record_inventory_levels(self):
        """
        This method records the inventory levels at regular intervals.

        Returns:
            None
        """
        yield self.env.timeout(0.9999) # wait for the end of the day
        self.instantaneous_levels.append([self.env.now, self.inventory.level]) # record the initial inventory level
        while True:
            yield self.env.timeout(1) # record inventory levels at the end of every day/period
            self.instantaneous_levels.append([self.env.now, self.inventory.level])

class Node():
    """
    Node class represents a node in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the node (alphanumeric)
        name (str): name of the node
        node_type (str): type of the node
        failure_p (float): node failure probability
        node_recovery_time (callable): function to model node recovery time
        isolated_logger (bool): flag to enable/disable isolated logger
        **kwargs: additional keyword arguments for logger (GlobalLogger)
        
    Functions:
        __init__: initializes the node object
        __str__: returns the name of the node
        __repr__: returns the name of the node
        get_info: returns a dictionary containing details of the node
        disruption: disrupt the node
    """
    def __init__(self, env: simpy.Environment, 
                 ID: str, 
                 name: str, 
                 node_type: str, 
                 failure_p:float = 0.0, 
                 node_recovery_time:callable = lambda: 1,
                 isolated_logger: bool = False, 
                 **kwargs) -> None:
        """
        Initialize the node object.

        Parameters:
            env (simpy.Environment): The simulation environment.
            ID (str): The ID of the node (alphanumeric).
            name (str): The name of the node.
            node_type (str): The type of the node.
            isolated_logger (bool, optional): Flag to enable/disable isolated logger. Defaults to False.
            **kwargs: Additional keyword arguments for the logger.
        
        Attributes:
            env (simpy.Environment): simulation environment
            ID (str): ID of the node (alphanumeric)
            name (str): name of the node
            node_type (str): type of the node
            node_failure_p (float): node failure probability
            node_status (str): status of the node (active/inactive)
            node_recovery_time (callable): function to model node recovery time
            logger (GlobalLogger): logger object
            inventory_cost (float): total inventory cost
            transportation_cost (list): list to store transportation costs. Every record contains (time of order, cost of order)
            node_cost (float): total node cost
            profit (float): profit per unit (sell price - buy price)
            net_profit (float): net profit of the node (total profit - node cost)
            products_sold (int): products/raw materials sold by this node in the current cycle/period/day
            total_products_sold (int): total product units sold by this node
            total_profit (float): total profit (profit per item * total_products_sold)
            
        Returns:
            None
        """
        if(node_type.lower() not in ["infinite_supplier","supplier", "manufacturer", "warehouse", "distributor", "inventory", "retailer", "demand"]):
            global_logger.logger.error(f"Invalid node type. Node type: {node_type}")
            raise ValueError("Invalid node type.")
        
        self.ID = ID  # ID of the node (alphanumeric)
        self.name = name  # name of the node
        self.node_type = node_type  # type of the node (supplier, manufacturer, warehouse, distributor, retailer, demand)
        self.env = env  # simulation environment
        self.node_failure_p = failure_p  # node failure probability
        self.node_status = "active"  # node status (active/inactive)
        self.node_recovery_time = node_recovery_time  # callable function to model node recovery time
        self.logger = global_logger.logger  # global logger
        if isolated_logger:  # if individual logger is required
            self.logger = GlobalLogger(logger_name=self.name, **kwargs).logger  # create an isolated logger

        # performance metrics for node
        self.inventory_cost = 0  # total inventory cost
        self.transportation_cost = [] # list to store transportation costs. Every record contains (time of order, cost of order)
        self.node_cost = 0  # total node cost (initial cost (establishment) + inventory cost + transportation cost)
        self.profit = 0  # profit per item
        self.net_profit = 0  # net profit (total profit - node cost)
        self.products_sold = 0 # products/raw materials sold by this node in the current cycle/period/day
        self.total_products_sold = 0 # total product units sold by this node
        self.total_profit = 0 # total profit (profit per item * total_products_sold)

        if(self.node_failure_p>0): # start self disruption if failure probability > 0
            self.env.process(self.disruption()) 

    def __str__(self):
        """
        Returns the name of the node.

        Returns:
            str: The name of the node.
        """
        return self.name

    def __repr__(self):
        """
        Returns the name of the node.

        Returns:
            str: The name of the node.
        """
        return self.name
    
    def get_info(self):
        """
        Get the details of the node.

        Returns:
            dict: dictionary containing details of the node
        """
        return {"ID": self.ID, "name": self.name, "node_type": self.node_type}
    
    def disruption(self):
        """
        This method disrupts the node by changing the node status to "inactive" and
        recovers it after the specified recovery time.

        Returns:
            None
        """
        while True:
            yield self.env.timeout(1)
            # disrupt the node with a probability node_failure_p
            if(random.random() < self.node_failure_p):
                self.node_status = "inactive"
                # self.logger.warning(f"{self.env.now}:{self.ID}: Node disrupted.")
                # recover the node after node_recovery_time
                yield self.env.timeout(self.node_recovery_time())
                self.node_status = "active"
                # self.logger.warning(f"{self.env.now}:{self.ID}: Node recovered from disruption.")
            
class Link():
    """
    Link class represents a link in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the link (alphanumeric)
        source (Node): source node of the link
        sink (Node): sink node of the link
        cost (float): cost of transportation over the link
        lead_time (callable): lead time of the link
        link_failure_p (float): link failure probability
        link_recovery_time (callable): function to model link recovery time
        
    Functions:
        __init__: initializes the link object
        __str__: returns the name of the link
        __repr__: returns the name of the link
        get_info: returns a dictionary containing details of the link
        disruption: disrupt the link
    """

    def __init__(self, env: simpy.Environment, 
                 ID: str, 
                 source: Node, 
                 sink: Node, 
                 cost: float, # transportation cost
                 lead_time: callable,
                 link_failure_p: float = 0.0,
                 link_recovery_time: callable = lambda: 1) -> None:
        """
        Initialize the link object.

        Parameters:
            env (simpy.Environment): simulation environment
            ID (str): ID of the link (alphanumeric)
            source (Node): source node of the link
            sink (Node): sink node of the link
            cost (float): cost of transportation over the link
            lead_time (function): a function to model stochastic lead time
            link_failure_p (float): link failure probability
            link_recovery_time (callable): function to model link recovery time

        Attributes:
            status (str): status of the link (active/inactive)
        
        Returns:
            None
        """
        if(lead_time == None):
            global_logger.logger.error("Lead time cannot be None. Provide a function to model stochastic lead time.")
            raise ValueError("Lead time cannot be None. Provide a function to model stochastic lead time.")
        if(cost <= 0):
            global_logger.logger.error("Cost cannot be zero or negative.")
            raise ValueError("Cost cannot be negative.")
        if(source == sink):
            global_logger.logger.error("Source and sink nodes cannot be the same.")
            raise ValueError("Source and sink nodes cannot be the same.")
        if(source.node_type == "demand"):
            global_logger.logger.error("Demand node cannot be a source node.")
            raise ValueError("Demand node cannot be a source node.")
        if(sink.node_type == "supplier"):
            global_logger.logger.error("Supplier node cannot be a sink node.")
            raise ValueError("Supplier node cannot be a sink node.")
        if(source.node_type == "supplier" and sink.node_type == "supplier"):
            global_logger.logger.error("Supplier nodes cannot be connected.")
            raise ValueError("Supplier nodes cannot be connected.")
        if(source.node_type == "supplier" and sink.node_type == "demand"):
            global_logger.logger.error("Supplier node cannot be connected to a demand node.")
            raise ValueError("Supplier node cannot be connected to a demand node.")

        self.env = env  # simulation environment
        self.ID = ID  # ID of the link (alphanumeric)
        self.source = source  # source node of the link
        self.sink = sink  # sink node of the link
        self.cost = cost  # cost of the link
        self.lead_time = lead_time  # lead time of the link
        self.link_failure_p = link_failure_p  # link failure probability
        self.status = "active"  # link status (active/inactive)
        self.link_recovery_time = link_recovery_time  # link recovery time

        self.sink.suppliers.append(self)  # add the link as a supplier link to the sink node
        if(self.link_failure_p>0): # disrupt the link if link_failure_p > 0
            self.env.process(self.disruption())

        if("supplier" not in self.source.node_type): # if the source node is not a supplier, set the buy price of the sink node to the sell price of the source node
            self.sink.buy_price = self.source.sell_price
            self.sink.profit = self.sink.sell_price - self.sink.buy_price
            if(self.source.product):
                self.sink.buy_price = self.source.product.sell_price # set the buy price of the sink node to the buy price of the source node
                self.sink.profit = self.sink.sell_price - self.sink.buy_price
    def __str__(self):
        """
        Return the name of the link.

        Returns:
            str: The name of the link.
        """
        return self.ID

    def __repr__(self):
        """
        Return the name of the link.

        Returns:
            str: The name of the link.
        """
        return self.ID

    def get_info(self):
        """
        Get the details of the link.

        Returns:
            dict: dictionary containing details of the link
        """
        return {"ID": self.ID, 
                "source": self.source, 
                "sink": self.sink, 
                "transportation cost": self.cost, 
                "lead_time": self.lead_time}
    
    def disruption(self):
        """
        This method disrupts the link by changing the link status to "inactive" and recovers it after the specified recovery time.

        Returns:
            None
        """
        while True:
            yield self.env.timeout(1)
            # disrupt the link with a probability link_failure_p
            if(random.random() < self.link_failure_p):
                self.status = "inactive"
                #self.logger.warning(f"{self.env.now}:{self.ID}: Link disrupted.")
                # recover the link after link_recovery_time
                yield self.env.timeout(self.link_recovery_time())
                self.status = "active"

class Supplier(Node):
    """
    Supplier class represents a supplier in the supply network.

    Parameters:
        node_type (str): type of the node
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        inventory_holding_cost (float): inventory holding cost
        raw_material (RawMaterial): raw material supplied by the supplier
        **kwargs: any additional keyword arguments for the Node class and logger

    Functions:
        __init__: initializes the supplier object
        __str__: returns the name of the supplier
        __repr__: returns the name of the supplier
        behavior: supplier behavior
        calculate_statistics: calculate statistics for the supplier
        get_info: returns a dictionary containing details of the supplier
        get_statistics: get statistics for the supplier

    Behavior:
        The supplier keeps extracting raw material whenever the inventory is not full. Assume that a supplier can extract a single type of raw material.
    """
    def __init__(self,
                 node_type: str = "supplier",
                 capacity: int = 0, 
                 initial_level: int = 0, 
                 inventory_holding_cost:float = 1, 
                 raw_material: RawMaterial = default_raw_material, 
                 **kwargs) -> None:
        """
        Initialize the supplier object.

        Parameters:
            node_type (str): type of the node (supplier/infinite_supplier)
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            inventory_holding_cost (float): inventory holding cost
            raw_material (RawMaterial): raw material supplied by the supplier
            **kwargs: any additional keyword arguments for the Node class and logger

        Attributes:
            raw_material (RawMaterial): raw material supplied by the supplier
            inventory (Inventory): inventory of the supplier
            inventory_holding_cost (float): inventory holding cost
            total_raw_materials_mined (int): total raw materials mined/extracted
            total_material_cost (float): total cost of the raw materials mined/extracted
            total_raw_materials_sold (int): total raw materials sold
            
        Returns:
            None
        """
        if(inventory_holding_cost <= 0):
            global_logger.logger.error("Inventory holding cost cannot be zero or negative.")
            raise ValueError("Inventory holding cost cannot be negative.")

        super().__init__(node_type=node_type,**kwargs)
        self.raw_material = raw_material # raw material supplied by the supplier. By default, it is the default raw material.
        if(self.node_type!="infinite_supplier"):
            self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, replenishment_policy="sS")
            if(self.raw_material):
                self.env.process(self.behavior()) # start the behavior process
            else:
                self.logger.error(f"{self.ID}:Raw material not provided for this supplier. Recreate it with a raw material.")
                raise ValueError("Raw material not provided.")
        else:
            self.inventory = Inventory(env=self.env, capacity=float('inf'), initial_level=float('inf'), replenishment_policy="sS")
        self.inventory_holding_cost = inventory_holding_cost # inventory holding cost
        self.profit = self.raw_material.cost - self.raw_material.mining_cost

        # performance metrics (listed only for the supplier, rest common are created and initiated by __init__ of the base class)
        self.total_raw_materials_mined = 0 # total raw materials mined/extracted
        self.total_material_cost = 0 # total cost of the raw materials mined/extracted
        self.total_raw_materials_sold = 0 # total raw materials sold
        self.env.process(self.calculate_statistics()) # calculate statistics

    def __str__(self):
        """
        Get the string representation of the supplier.

        Parameters:
            None

        Returns:
            str: name of the supplier
        """
        return self.name
    
    def __repr__(self):
        """
        Get the string representation of the supplier.

        Parameters:
            None

        Returns:
            str: name of the supplier
        """
        return self.name
    
    def get_info(self):
        """
        Get the details of the supplier.

        Parameters:
            None

        Returns:
            dict: dictionary containing details of the supplier
        """
        info = {"ID": self.ID, 
                "name": self.name, 
                "type": self.node_type, 
                "inventory": self.inventory.get_info()}
        if(self.raw_material):
            info["raw_material"] = self.raw_material.get_info()    
        return info
    
    def calculate_statistics(self):
        """
        Calculate and record everyday node level statistics for the supplier.

        Parameters:
            None

        Returns:
            None
        """
        yield self.env.timeout(0.99999) # wait for the end of the day       
        while True:
            if(self.node_type!="infinite_supplier"): # calculate inventory cost only if the node is not an infinite supplier
                self.inventory_cost += self.inventory_holding_cost * self.inventory.inventory.level
            if(self.raw_material):
                self.total_material_cost = self.total_raw_materials_mined * self.raw_material.cost
            self.node_cost = self.total_material_cost + self.inventory_cost + sum([x[1] for x in self.transportation_cost])
            self.total_profit = self.profit * self.total_products_sold
            self.net_profit = self.total_profit - self.node_cost
            yield self.env.timeout(1)

    def get_statistics(self):
        """
        Get statistics for the supplier.

        Parameters:
            None

        Returns:
            dict: dictionary containing statistics for the supplier
        """
        return {"total_raw_materials_mined": self.total_raw_materials_mined, 
                "total_material_cost": self.total_material_cost, 
                "total_raw_material_sold":self.total_raw_materials_sold, 
                "inventory_cost": self.inventory_cost, 
                "transportation_cost": sum([x[1] for x in self.transportation_cost]), 
                "total units sold": self.total_products_sold,
                "profit per unit": self.profit, 
                "total profit": self.total_profit,
                "node_cost": self.node_cost,
                "net_profit": self.net_profit}
        
    def behavior(self):
        """
        Supplier behavior: The supplier keeps extracting raw material whenever the inventory is not full.
        Assume that a supplier can extract a single type of raw material.

        Parameters:
            None

        Returns:
            None
        """
        yield self.env.timeout(0.99999)
        while True:
            if(self.inventory.inventory.level < self.inventory.inventory.capacity): # check if the inventory is not full
                yield self.env.timeout(self.raw_material.extraction_time)
                if(self.inventory.inventory.level + self.raw_material.extraction_quantity <= self.inventory.inventory.capacity): # check if the inventory can accommodate the extracted quantity
                    self.inventory.inventory.put(self.raw_material.extraction_quantity)
                    self.total_raw_materials_mined += self.raw_material.extraction_quantity # update statistics
                else: # else put the remaining capacity in the inventory
                    self.inventory.inventory.put(self.inventory.inventory.capacity - self.inventory.inventory.level)
                    self.total_raw_materials_mined += self.inventory.inventory.capacity - self.inventory.inventory.level # update statistics
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Raw material mined/extracted. Inventory level:{self.inventory.inventory.level}")
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Inventory level:{self.inventory.inventory.level}") # log every day/period inventory level
            yield self.env.timeout(1)

class InventoryNode(Node):
    """
    InventoryNode class represents an inventory node in the supply network.

    Parameters:
        node_type (str): type of the inventory node (retailer or distributor)
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        inventory_holding_cost (float): inventory holding cost
        inventory_type (str): type of the inventory (non-perishable/perishable)
        shelf_life (int): shelf life of the product
        manufacture_date (callable): function to model manufacturing date for product (this function is used in the case when behaviour of a single node is to be modeled)
        replenishment_policy (str): replenishment policy for the inventory
        product_sell_price (float): selling price of the product
        product_buy_price (float): buying price of the product
        policy_param (list): parameters for the replenishment policy
        product (Product): product that the inventory node sells
        **kwargs: any additional keyword arguments for the Node class and logger

    Functions:
        __init__: initializes the inventory node object
        __str__: returns the name of the inventory node
        __repr__: returns the name of the inventory node
        calculate_statistics: calculate statistics for the inventory node
        get_info: returns a dictionary containing details of the inventory node
        get_statistics: get statistics for the inventory node
        periodic_replenishment: monitored inventory replenishment policy (periodic)
        place_order: place an order
        ss_replenishment: monitored inventory replenishment policy (s,S)

    """
    def __init__(self,
                 node_type: str, 
                 capacity: int, 
                 initial_level: int, 
                 inventory_holding_cost:float,
                 inventory_type:str = "non-perishable", 
                 shelf_life:int = 0,
                 manufacture_date:callable = None,
                 replenishment_policy: str = "sS", 
                 product_sell_price: float = 0.0, 
                 product_buy_price: float = 0.0,
                 policy_param: list = [2], 
                 product:Product = None,
                 **kwargs) -> None:
        """
        Initialize the inventory node object.

        Parameters:
            node_type (str): type of the inventory node (retailer or distributor)
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            inventory_holding_cost (float): inventory holding cost
            inventory_type (str): type of the inventory (non-perishable/perishable)
            shelf_life (int): shelf life of the product
            manufacture_date (callable): function to model manufacturing date for product (this function is used in the case when behaviour of a single node is to be modeled)
            replenishment_policy (str): replenishment policy for the inventory
            product_sell_price (float): selling price of the product
            product_buy_price (float): buying price of the product
            policy_param (list): parameters for the replenishment policy
            product (Product): product that the inventory node sells
            **kwargs: any additional keyword arguments for the Node class and logger

        Attributes:
            node_type (str): type of the inventory node (retailer or distributor)
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            inventory_holding_cost (float): inventory holding cost
            suppliers (list): list of supplier links from which the inventory node can replenish inventory
            replenishment_policy (str): replenishment policy for the inventory
            policy_param (list): parameters for the replenishment policy
            inventory (Inventory): inventory object
            product (Product): product that the inventory node sells
            manufacture_date (callable): function to model manufacturing date
            sell_price (float): selling price of the product
            buy_price (float): buying price of the product
            order_placed (bool): flag to check if the order is placed
            product_sold_daily (list): list to store the product sold in the current cycle
            products_sold (int): total product sold in the current cycle
        
        Returns:
            None

        Behavior:
            The inventory node sells the product to the customers. It replenishes the inventory from the suppliers according to the replenishment policy. 
            The inventory node can have multiple suppliers. It chooses a supplier based on the availability of the product at the suppliers.
            The product buy price is set to the supplier's product sell price. The inventory node sells the product at a higher price than the buy price.
        """
        if(capacity <= 0):
            global_logger.logger.error("Inventory capacity cannot be zero or negative.")
            raise ValueError("Capacity cannot be negative.")
        if(initial_level < 0):
            global_logger.logger.error("Initial level cannot be negative.")
            raise ValueError("Initial level cannot be negative.")
        if(inventory_holding_cost <= 0):
            global_logger.logger.error("Inventory holding cost cannot be zero or negative.")
            raise ValueError("Inventory holding cost cannot be negative.")
        if(capacity < initial_level):
            global_logger.logger.error("Initial level cannot be greater than capacity.")
            raise ValueError("Initial level cannot be greater than capacity.")        

        super().__init__(node_type=node_type,**kwargs)
        self.node_type = node_type
        self.capacity = capacity
        self.initial_level = initial_level
        self.inventory_holding_cost = inventory_holding_cost
        self.suppliers = []
        self.replenishment_policy = replenishment_policy
        self.policy_param = policy_param
        self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, type=inventory_type, replenishment_policy=replenishment_policy, shelf_life=shelf_life)
        self.product = copy.deepcopy(product) # product that the inventory node sells
        self.manufacture_date = manufacture_date
        self.sell_price = product_sell_price # set the sell price of the product
        self.buy_price = 0 # set the buy price of the product initially to 0, since buy price will be updated based on the supplier
        if(product_buy_price>0):
            self.buy_price = product_buy_price # set the buy price of the product
        self.profit = self.sell_price - self.buy_price # calculate profit
        if(self.product and product_sell_price!=0):
            self.product.sell_price = product_sell_price
            self.buy_price = self.product.buy_price # set the buy price of the product initially to 0, since buy price will be updated based on the supplier
        self.order_placed = False # flag to check if the order is placed
    
        if(self.replenishment_policy == "sS"):
            self.env.process(self.ss_replenishment(s=self.policy_param[0]))
        elif(self.replenishment_policy == "periodic"):
            self.env.process(self.periodic_replenishment(interval=self.policy_param[0], reorder_quantity=self.policy_param[1]))

        # statistics
        self.products_sold_daily = [] # list to store the product sold in the current cycle
        self.products_sold = 0
        self.env.process(self.calculate_statistics()) # calculate statistics
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    
    def get_info(self):
        """
        Get the details of the inventory node.

        Parameters:
            None

        Returns:
            dict: dictionary containing details of the inventory node
        """
        info = {"ID": self.ID, 
                "name": self.name, 
                "node_type": self.node_type, 
                "inventory": self.inventory.get_info(), 
                "inventory_replenishment_policy": self.replenishment_policy, 
                "policy_param": self.policy_param}
        if(self.product):
            info["product"] = self.product.get_info() 
        return info
    
    def calculate_statistics(self):
        """
        Calculate statistics for the inventory node.

        Parameters:
            None

        Returns:
            None
        """
        self.products_sold = 0 # reset the products sold in the current cycle
        yield self.env.timeout(0.9999)
        while True:
            self.products_sold_daily.append((self.env.now, self.products_sold)) # append the product sold in the current cycle
            self.total_products_sold += self.products_sold
            self.inventory_cost += self.inventory_holding_cost * self.inventory.inventory.level # update the inventory cost
            self.node_cost = self.inventory_cost + sum([x[1] for x in self.transportation_cost]) + sum([x[1] for x in self.inventory.inventory_spend])
            self.total_profit += self.profit * self.products_sold # update the total profit
            self.net_profit = self.total_profit - self.node_cost # update the net profit
            self.products_sold = 0 # reset the products sold in the current cycle
            yield self.env.timeout(1)

    def get_statistics(self):
        """
        Get statistics for the inventory node.

        Parameters:
            None

        Returns:
            dict: dictionary containing statistics for the inventory node
        """
        total_units_sold = sum([x[1] for x in self.products_sold_daily])
        tranport_cost = sum([x[1] for x in self.transportation_cost])
        return {"inventory_cost": self.inventory_cost,
                "transportation_cost": tranport_cost,
                "node_cost": self.node_cost,
                "total_units_sold":total_units_sold,
                "total_product_cost": total_units_sold*self.buy_price,
                "total_revenue": total_units_sold*self.sell_price, 
                "total_profit": self.total_profit}

    def place_order(self, supplier, reorder_quantity):
        """
        Place an order for the product from the suppliers.

        Parameters:
            supplier (Link): The supplier link from which the order is placed.
            reorder_quantity (int): The quantity of the product to reorder.

        Returns:
            None
        """
        if(supplier.source.node_status == "active"):
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing inventory from supplier:{supplier.source.name}, order placed for {reorder_quantity} units.")
            if(supplier.source.inventory.type=="perishable"):
                event, man_date_ls = supplier.source.inventory.inventory.get(reorder_quantity)
                yield event
            else:
                yield supplier.source.inventory.inventory.get(reorder_quantity) # get the product from the supplier inventory
            if(supplier.source.node_type not in ["supplier","infinite_supplier"]): # if the supplier is not a supplier or infinite supplier
                self.buy_price = supplier.source.sell_price # set the sell price of the product to the supplier sell price
                if(self.product): # product buy price may depend on the supplier, if a product is available then update the self buy_price = supplier sell_price
                    self.product.buy_price = supplier.source.sell_price # update the product cost 
            self.profit = self.sell_price - self.buy_price # calculate profit
            self.transportation_cost.append((self.env.now,supplier.cost)) # calculate stats: record order cost (tranportation cost))
            supplier.source.products_sold = reorder_quantity # calculate stats: update the product sold at the supplier
            supplier.source.total_products_sold += reorder_quantity # calculate stats: update the total product sold at the supplier
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.") # log the shipment
            yield self.env.timeout(supplier.lead_time()) # lead time for the order
            if(supplier.source.inventory.type=="perishable" and self.inventory.type=="perishable"): # if supplier also has perishable inventory
                for ele in man_date_ls: # get manufacturing date from the supplier
                    self.inventory.inventory.put(ele[1],ele[0])
            elif(supplier.source.inventory.type=="perishable"): # if supplier has perishable inventory but self inventory is non-perishable
                for ele in man_date_ls: # ignore the manufacturing date
                    self.inventory.inventory.put(ele[1])
            elif(self.inventory.type=="perishable"): # if self inventory is perishable but supplier has non-perishable inventory
                if(self.manufacture_date): # calculate the manufacturing date using the function if provided
                    self.inventory.inventory.put(reorder_quantity,self.manufacture_date(self.env.now))
                else: # else put the product in the inventory with current time as manufacturing date
                    self.inventory.inventory.put(reorder_quantity,self.env.now)
            else:
                self.inventory.inventory.put(reorder_quantity)

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Inventory replenished. Inventory levels:{self.inventory.inventory.level}")
            self.inventory.inventory_spend.append([self.env.now, reorder_quantity*self.buy_price]) # update stats: calculate and update inventory replenishment cost
        else:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Supplier:{supplier.source.name} is disrupted. Order not placed.")
        self.order_placed = False
        
    def ss_replenishment(self, s):
        """
        Monitored inventory replenishment policy (s,S): s represents the reorder point and S represents the inventory capacity. 
        Behavior: Replenish the inventory from the suppliers whenever the inventory level is below the reorder point (s). 

        Parameters:
            s (int): reorder point

        Returns:
            None
        """
        yield self.env.timeout(0.999) # wait till the end of the day to check the inventory status
        while True:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Inventory levels:{self.inventory.inventory.level}")
            if(self.inventory.inventory.level <= s):
                # reorder quantity is calculated based on the remaining capacity of the inventory
                reorder_quantity = self.inventory.inventory.capacity - self.inventory.inventory.level
                if(reorder_quantity>0):
                    # choose a supplier to replenish the inventory based on the availablity of the product
                    # check availablity of the product at suppliers
                    for supplier in self.suppliers:
                        if(supplier.source.inventory.inventory.level >= reorder_quantity and self.order_placed == False):
                            self.order_placed = True
                            self.env.process(self.place_order(supplier, reorder_quantity))
                    if(self.order_placed == False): # required quantity not available at any suppliers (order cannot be placed)
                        # TODO: Backlog order logic can be added here, get whatever is available from this supplier and get remaining of the order from another supplier.
                        # OR wait on the same supplier for the remaining quantity.
                        # Record backlog at the respective suppliers.
                        self.logger.info(f"{self.env.now:.4f}:{self.ID}:Product not available at suppliers. Required quantity:{reorder_quantity}.")
            yield self.env.timeout(1)
            
    def periodic_replenishment(self, interval, reorder_quantity):
        """
        Monitored inventory replenishment policy (periodic): Replenish the inventory from the suppliers at regular intervals. 

        Parameters:
            interval (int): time interval for replenishment

        Returns:
            None
        """
        yield self.env.timeout(0.999) # wait till the end of the day to check the inventory status
        while True:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Inventory levels:{self.inventory.inventory.level}")
            if(self.inventory.inventory.level < self.inventory.inventory.capacity):
                # choose a supplier to replenish the inventory based on the availablity of the product
                # check availablity of the product at suppliers
                for supplier in self.suppliers:
                    if(supplier.source.inventory.inventory.level > reorder_quantity and self.order_placed == False):
                        self.order_placed = True
                        self.env.process(self.place_order(supplier, reorder_quantity))
                if(self.order_placed == False): # required quantity not available at any suppliers (order cannot be placed)
                     # TODO: Backlog order logic can be added here, get whatever is available from this supplier and get remaining of the order from another supplier.
                        # OR wait on the same supplier for the remaining quantity.
                        # Record backlog at the respective suppliers.
                    self.logger.info(f"{self.env.now:.4f}:{self.ID}:Product not available at suppliers. Required quantity:{reorder_quantity}.")
            yield self.env.timeout(interval)

class Manufacturer(Node):
    """
    Manufacturer class represents a manufacturer in the supply network.

    Parameters:
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        inventory_holding_cost (float): inventory holding cost
        product_sell_price (float): selling price of the product
        product (Product): product manufactured by the manufacturer
        inventory_type (str): type of the inventory (non-perishable/perishable)
        shelf_life (int): shelf life of the product
        replenishment_policy (str): replenishment policy for the inventory
        policy_param (list): parameters for the replenishment policy
        **kwargs: additional keyword arguments for logger

    Functions:
        __init__: initializes the manufacturer object
        __str__: returns the name of the manufacturer
        __repr__: returns the name of the manufacturer
        behavior: manufacturer behavior - consume raw materials, produce the product, and put the product in the inventory
        calculate_statistics: calculate statistics for the manufacturer
        get_info: returns a dictionary containing details of the manufacturer
        get_statistics: get statistics for the manufacturer
        manufacture_product: manufacture the product
        periodic_replenishment: monitored inventory replenishment policy (periodic)
        place_order: place an order for raw materials
        ss_replenishment: monitored inventory replenishment policy (s,S)
    
    Behavior:
        The manufacturer consumes raw materials and produces the product if raw materials are available.
        It maintains inventory levels for raw materials and the product. Depending on the replenishment policy for product inventory,
        manufacturer decides when to replenish the raw material inventory. The manufacturer can be connected to multiple suppliers.

    Assumptions:
        Manufacturer produce a single product. 
        Manufacturer has separate inventories for raw materials and the product.
        Only the product inventory is monitored according to the replenishment policy, and raw materials inventory is replenished based on it.
        Raw materials inventory is initially empty.
        
    """
    def __init__(self,
                 capacity: int, 
                 initial_level: int, 
                 inventory_holding_cost: float, 
                 product_sell_price: float, 
                 product: Product = default_product, 
                 inventory_type: str = "non-perishable",
                 shelf_life: int = 0,
                 replenishment_policy: str = "sS", 
                 policy_param: list = [], 
                 **kwargs) -> None:
        """
        Initialize the manufacturer object.

        Parameters:
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            inventory_holding_cost (float): inventory holding cost
            product_sell_price (float): selling price of the product
            product (Product): product manufactured by the manufacturer
            inventory_type (str): type of the inventory (non-perishable/perishable)
            shelf_life (int): shelf life of the product
            replenishment_policy (str): replenishment policy for the inventory
            policy_param (list): parameters for the replenishment policy
            **kwargs: additional keyword arguments for logger


        Attributes:
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            inventory_holding_cost (float): inventory holding cost
            product (Product): product manufactured by the manufacturer
            suppliers (list): list of suppliers from which the manufacturer can replenish inventory
            replenishment_policy (str): replenishment policy for the inventory
            policy_param (list): parameters for the replenishment policy
            sell_price (float): selling price of the product
            production_cycle (bool): production cycle status
            raw_inventory_counts (dict): dictionary to store inventory counts for raw products inventory
            order_placed (dict): dictionary to store order status for raw materials
            product_order_placed (bool): order status for the product
            inventory (Inventory): inventory of the manufacturer
            profit (float): profit per unit sold
            total_products_manufactured (int): total products manufactured
            total_manufacturing_cost (float): total cost of the products manufactured
            revenue (float): revenue from the products sold
            isolated_logger (bool): flag to enable/disable isolated logger

        Returns:
            None
        """
        if(inventory_holding_cost <= 0):
            global_logger.logger.error("Inventory holding cost cannot be zero or negative.")
            raise ValueError("Inventory holding cost cannot be negative.")

        super().__init__(node_type="manufacturer",**kwargs)
        self.capacity = capacity
        self.initial_level = initial_level
        self.inventory_holding_cost = inventory_holding_cost
        self.product = product # product manufactured by the manufacturer
        self.suppliers = []
        self.replenishment_policy = replenishment_policy
        self.policy_param = policy_param
        self.product.sell_price = product_sell_price
        self.sell_price = product_sell_price # set the sell price of the product
        
        self.production_cycle = False # production cycle status
        self.raw_inventory_counts = {} # dictionary to store inventory counts for raw products inventory
        self.order_placed = {} # dictionary to store order status
        self.product_order_placed = False # order status for the product
        self.inventory = Inventory(env=self.env, capacity=self.capacity, initial_level=self.initial_level, type=inventory_type, replenishment_policy=self.replenishment_policy, shelf_life=shelf_life)
        
        if(self.replenishment_policy == "sS"):
            self.env.process(self.ss_replenishment(s=self.policy_param[0])) # start the inventory replenishment process
        elif(self.replenishment_policy == "periodic"):
            self.env.process(self.periodic_replenishment(interval=self.policy_param[0], reorder_quantity=self.policy_param[1])) # start the inventory replenishment process

        # calculate the total cost of the product, and set the sell price
        self.product.buy_price = self.product.manufacturing_cost # total cost of the product
        for raw_material in self.product.raw_materials:
            self.product.buy_price += raw_material["raw_material"].cost * raw_material["quantity"] # calculate total cost of the product (per unit)
        
        self.profit = self.product.sell_price - self.product.buy_price # set the sell price as the buy price
        self.env.process(self.behavior()) # start the behavior process

        # performance metrics (listed only for the manufacturer, rest common are created and initiated by __init__ of the base class)
        self.total_products_manufactured = 0 # total products manufactured
        self.total_manufacturing_cost = 0 # total cost of the products manufactured
        self.revenue = 0 # revenue from the products sold
        self.env.process(self.calculate_statistics()) # calculate statistics

        if(self.env == None):
            global_logger.logger.error("Simulation environment not provided.")
            raise ValueError("Simulation environment not provided.")
        
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    
    def get_info(self):
        """
        Get the details of the manufacturer.

        Parameters:
            None

        Returns:
            dict: dictionary containing details of the manufacturer
        """
        info = {"ID": self.ID, "name": self.name, "product": self.product.get_info(), 
                "inventory": self.inventory.get_info(),
                "inventory_replenishment_policy": self.replenishment_policy, 
                "policy_param": self.policy_param}
        return info
    
    def calculate_statistics(self):
        """
        Calculate statistics for the manufacturer.

        Parameters:
            None

        Returns:
            None
        """
        yield self.env.timeout(0.9999)
        while True:
            if(self.product):
                self.total_manufacturing_cost = self.total_products_manufactured * self.product.manufacturing_cost
                self.revenue = self.total_products_sold * self.product.sell_price
            self.inventory_cost += self.inventory_holding_cost * self.inventory.inventory.level
            self.total_profit = self.total_products_sold * self.profit # profit = sell price - buy price (profit per product unit)
            self.node_cost = self.inventory_cost + sum([x[1] for x in self.transportation_cost]) + self.total_manufacturing_cost
            self.net_profit = self.total_profit - self.node_cost
            yield self.env.timeout(1)
    
    def get_statistics(self):
        """
        Get statistics for the manufacturer.

        Parameters:
            None

        Returns:
            dict: dictionary containing statistics for the manufacturer
        """
        return {"total_products_manufactured": self.total_products_manufactured, 
                "total_manufacturing_cost": self.total_manufacturing_cost, 
                "inventory_cost": self.inventory_cost, 
                "tranportation_cost": sum([x[1] for x in self.transportation_cost]), 
                "node_cost": self.node_cost, 
                "total_products_sold": self.total_products_sold, 
                "total_profit": self.total_profit, 
                "revenue": self.revenue, 
                "net_profit": self.net_profit}    

    def manufacture_product(self):
        """
        Manufacture the product.

        This method handles the production of the product, consuming raw materials
        and adding the manufactured product to the inventory.

        Returns:
            None
        """
        max_producible_units = self.product.units_per_cycle
        for raw_material in self.product.raw_materials: # consume raw materials
            raw_mat_id = raw_material["raw_material"].ID
            required_amount = raw_material["quantity"]
            current_raw_material_level = self.raw_inventory_counts[raw_mat_id]
            max_producible_units = min(max_producible_units,int(current_raw_material_level/required_amount))
        if(max_producible_units>0):
            self.production_cycle = True # produce the product
            for raw_material in self.product.raw_materials: # consume raw materials
                raw_mat_id = raw_material["raw_material"].ID
                required_amount = raw_material["quantity"]
                self.raw_inventory_counts[raw_mat_id] -= raw_material["quantity"]*max_producible_units
            yield self.env.timeout(self.product.manufacturing_time) # take manufacturing time to produce the product
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: {max_producible_units} units manufactured.")
            # put the product units in the inventory
            if(self.inventory.inventory.level + max_producible_units <= self.inventory.inventory.capacity): # check if manufactured units can be accomodated
                if(self.inventory.type == "perishable"):
                    self.inventory.inventory.put(max_producible_units, manufacturing_date=self.env.now)
                else:
                    self.inventory.inventory.put(max_producible_units)
            elif(self.inventory.inventory.capacity>self.inventory.inventory.level): # check if current level is below capcacity
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Inventory full.")
                if(self.inventory.type == "perishable"):
                    self.inventory.inventory.put(self.inventory.inventory.capacity - self.inventory.inventory.level, manufacturing_date=self.env.now)
                else:
                    self.inventory.inventory.put(self.inventory.inventory.capacity - self.inventory.inventory.level)
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Product inventory levels:{self.inventory.inventory.level}")
            # update statistics
            self.total_products_manufactured += max_producible_units
            self.production_cycle = False

    def behavior(self):
        """
        The manufacturer consumes raw materials and produces the product if raw materials are available.
        It maintains inventory levels for both raw materials and the product. Depending on the replenishment policy for product inventory,
        manufacturer decides when to replenish the raw material inventory. The manufacturer can be connected to multiple suppliers.
        
        Parameters:
            None

        Returns:
            None
        """
        if(len(self.suppliers)==0):
            global_logger.logger.warning("No suppliers connected to the manufacturer.")

        # create an inventory for storing raw materials as a dictionary. Key: raw material ID, Value: inventory level
        if(len(self.suppliers)>0):
            for supplier in self.suppliers: # iterate over supplier links
                self.raw_inventory_counts[supplier.source.raw_material.ID] = 0 # store initial levels
                #self.raw_inventory_counts[f"{supplier.source.raw_material.ID}_leveldata"] = []
                #self.raw_inventory_counts[f"{supplier.source.raw_material.ID}_timesdata"] = []
                self.order_placed[supplier.source.raw_material.ID] = False # store order status
                
        if(len(self.suppliers)<len(self.product.raw_materials)):
            global_logger.logger.warning(f"{self.ID}: {self.name}: The number of suppliers are less than the number of raw materials required to manufacture the product! This leads to no products being manufactured.")

        # behavior of the manufacturer: consume raw materials, produce the product, and put the product in the inventory
        yield self.env.timeout(0.99999)
        while True:
            if(len(self.suppliers)>=len(self.product.raw_materials)): # check if required number of suppliers are connected
                if(not self.production_cycle):
                    self.env.process(self.manufacture_product()) # produce the product
            yield self.env.timeout(1)

    def place_order(self, raw_material, reorder_quantity):
        """
        Place an order for raw materials from the suppliers.

        Parameters:
            raw_material (str): The ID of the raw material to order.
            reorder_quantity (int): The quantity of the raw material to reorder.

        Returns:
            None
        """
        for supplier in self.suppliers: # check for the supplier of the raw material
            if(supplier.source.raw_material.ID == raw_material):
                if(supplier.source.inventory.inventory.level>=reorder_quantity): # check if the supplier has enough inventory
                    self.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing raw material:{supplier.source.raw_material.name} from supplier:{supplier.source.ID}, order placed for {reorder_quantity} units.")
                    yield supplier.source.inventory.inventory.get(reorder_quantity)
                    self.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.")                
                    # update the transportation cost at the supplier
                    #supplier.source.transportation_cost.append((self.env.now,supplier.cost))
                    self.transportation_cost.append((self.env.now,supplier.cost))
                    # update the product sold at the raw material supplier
                    supplier.source.total_raw_materials_sold += reorder_quantity
                    supplier.source.total_products_sold += reorder_quantity
                    yield self.env.timeout(supplier.lead_time()) # lead time for the order
                    self.order_placed[raw_material] = False
                    self.raw_inventory_counts[raw_material] += reorder_quantity
                    self.logger.info(f"{self.env.now:.4f}:{self.ID}:Order received from supplier:{supplier.source.name}, inventory levels: {self.raw_inventory_counts}")
                    self.inventory.inventory_spend.append([self.env.now, reorder_quantity*supplier.source.raw_material.cost]) # update stats: calculate and update inventory replenishment cost
                else:
                    self.logger.info(f"{self.env.now:.4f}:{self.ID}:Insufficient inventory at supplier:{supplier.source.name}, order not placed.")
                    self.order_placed[raw_material] = False
                #break

    def ss_replenishment(self, s):
        """
        Monitored inventory replenishment policy (s,S): s represents the reorder point and S represents the inventory capacity. 
        Behavior: Replenish the inventory from the suppliers whenever the inventory level is below the reorder point (s). 

        Parameters:
            s (int): reorder point

        Returns:
            None
        """
        yield self.env.timeout(0.9999) # wait till the end of the day to check the inventory status
        while True:
            if(self.inventory.inventory.level<=s and not self.product_order_placed): # product inventory level is below the reorder point
                self.product_order_placed = True
                product_reorder_quantity = self.inventory.inventory.capacity - self.inventory.inventory.level # how many product units to order 
                for raw_material in self.product.raw_materials: # order all raw materials required to produce the product
                    reorder_quantity = product_reorder_quantity * raw_material["quantity"] # calculate the reorder quantity for raw material
                    reorder_quantity = reorder_quantity - self.raw_inventory_counts[raw_material["raw_material"].ID] # calculate the remaining quantity to order
                    if(not self.order_placed[raw_material["raw_material"].ID] and reorder_quantity>0): # check if the order is already placed                        
                        self.order_placed[raw_material["raw_material"].ID] = True # set the order status to True
                        self.env.process(self.place_order(raw_material["raw_material"].ID, reorder_quantity)) # place the order
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Raw materials' inventory levels:{self.raw_inventory_counts}, Product inventory levels:{self.inventory.inventory.level}")
            if(any(self.order_placed.values()) == True):
                self.product_order_placed = True
            if(all(self.order_placed.values()) == False):
                self.product_order_placed = False
            yield self.env.timeout(1)
                

    def periodic_replenishment(self, interval, reorder_quantity):
        """
        Monitored inventory replenishment policy (periodic): Replenish the inventory from the suppliers at regular intervals. 

        Parameters:
            interval (int): time interval for replenishment

        Returns:
            None
        """
        yield self.env.timeout(0.9999) # wait till the end of the day to check the inventory status
        while True:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Raw materials' inventory levels:{self.raw_inventory_counts}, Product inventory levels:{self.inventory.inventory.level}")
            product_reorder_quantity = reorder_quantity # how many product units to order
            for raw_material in self.product.raw_materials: # order all raw materials required to produce the product
                reorder_quantity_raw = product_reorder_quantity * raw_material["quantity"] # calculate the reorder quantity for raw material
                reorder_quantity_raw = reorder_quantity_raw - self.raw_inventory_counts[raw_material["raw_material"].ID] # calculate the remaining quantity to order
                if(not self.order_placed[raw_material["raw_material"].ID] and reorder_quantity_raw>0): # check if the order is already placed
                    self.order_placed[raw_material["raw_material"].ID] = True # set the order status to True
                    self.env.process(self.place_order(raw_material["raw_material"].ID, reorder_quantity_raw)) # place the order
            yield self.env.timeout(interval) # time interval for replenishment

class Demand(Node):
    """
    Demand class represents a demand node in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the demand node (alphanumeric)
        name (str): name of the demand node
        order_arrival_model (function): function that models order arrivals
        order_quantity_model (function): function that models order quantity
        demand_node (Node): node at which the demand is generated
        tolerance (float): customer tolerance for waiting for the order when required quantity is not available
        delivery_cost (function): function that models the cost of delivery
        lead_time (function): function that models the lead time for delivery
        **kwargs: additional keyword arguments for Node and GlobalLogger

    Functions:
        __init__: initializes the demand node object
        __str__: returns the name of the demand node
        __repr__: returns the name of the demand node
        customer: simulates the customer behavior, ordering products from demand node, consume and return
        get_info: returns a dictionary containing details of the demand node
        get_statistics: get statistics for the demand node
        wait_for_order: wait for the required number of units based on customer tolerance
        behavior: generates demand by calling the order arrival and order quantity models
    """

    def __init__(self,
                 order_arrival_model: callable, 
                 order_quantity_model: callable, 
                 demand_node: Node,
                 tolerance: float = 0.0,
                 delivery_cost: callable = lambda: 0,
                 lead_time: callable = lambda: 0,
                 **kwargs) -> None:
        """
        Initialize the demand node object.

        Parameters:
            order_arrival_model (function): function that models order arrivals
            order_quantity_model (function): function that models order quantity
            demand_node (Node): node at which the demand is generated
            tolerance (float): customer tolerance for waiting for the order when required quantity is not available
            delivery_cost (function): function that models the cost of delivery
            lead_time (function): function that models the lead time for delivery
            **kwargs: additional keyword arguments for Node and GlobalLogger

        Attributes:
            order_arrival_model (function): function that models order arrivals
            order_quantity_model (function): function that models order quantity
            demand_node (Node): node at which the demand is generated
            customer_tolerance (float): customer tolerance for waiting for the order
            delivery_cost (function): function that models the cost of delivery
            lead_time (function): function that models the lead time for delivery
            total_products_sold (int): total products sold
            unsatisfied_demand (int): unsatisfied demand
            shortage (int): shortage
            
        Returns:
            None
        """
        if(order_arrival_model == None):
            global_logger.logger.error("Order arrival model cannot be None.")
            raise ValueError("Order arrival model cannot be None.")
        if(order_quantity_model == None):
            global_logger.logger.error("Order quantity model cannot be None.")
            raise ValueError("Order quantity model cannot be None.")
        if(demand_node == None):
            global_logger.logger.error("Demand node cannot be None.")
            raise ValueError("Demand node cannot be None.")
        if(demand_node.node_type == "supplier"):
            global_logger.logger.error("Demand node cannot be a supplier.")
            raise ValueError("Demand node cannot be a supplier.")
            
        super().__init__(node_type="demand",**kwargs)
        self.order_arrival_model = order_arrival_model
        self.order_quantity_model = order_quantity_model
        self.demand_node = demand_node
        self.customer_tolerance = tolerance
        self.delivery_cost = delivery_cost
        self.lead_time = lead_time
        self.env.process(self.behavior())

        self.total_demand = 0
        self.product_sold = [] # list to store the product sold everyday
        self.unsatisfied_demand = [] # list to store the unsatisfied demand
        self.shortage = []

    def __str__(self):
        """
        Return the name of the demand node.

        Parameters:
            None

        Returns:
            str: The name of the demand node.
        """
        return self.name
    
    def __repr__(self):
        """
        Return the name of the demand node.

        Parameters:
            None

        Returns:
            str: The name of the demand node.
        """
        return self.name
    
    def get_info(self):
        """
        Get the details of the demand node.

        Parameters:
            None

        Returns:
            dict: dictionary containing details of the demand node
        """
        return {"ID": self.ID, "name": self.name, "demand_node": self.demand_node}
    
    def get_statistics(self):
        """
        Get statistics for the demand node.

        Parameters:
            None

        Returns:
            dict: dictionary containing statistics for the demand node
        """
        return {"total_products_sold": self.total_products_sold, 
                "unsatisfied_demand": self.unsatisfied_demand,
                "shortage": self.shortage}

    def wait_for_order(self,id,order_quantity):
        """
        Wait for the required number of units based on customer tolerance.
        If the customer tolerance is infinite, the method waits until the order is fulfilled.
        Otherwise, it waits for the specified tolerance time and updates the unsatisfied demand if the order is not fulfilled.

        Parameters:
            order_quantity (int): The quantity of the product ordered.

        Returns:
            None
        """
        if(self.customer_tolerance==float('inf')): # wait for the order to arrive
            if(self.demand_node.inventory.type=="perishable"):
                get_event, man_date_ls = self.demand_node.inventory.inventory.get(order_quantity)
                yield get_event
            else:
                yield self.demand_node.inventory.inventory.get(order_quantity)
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, remaining order quantity:{order_quantity} placed.")
            yield self.env.timeout(self.lead_time()) # wait for the delivery of the order
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} received. Current inv: {self.demand_node.inventory.inventory.level}")

            # update statistics
            self.product_sold.append((self.env.now, order_quantity))
            self.total_products_sold += order_quantity
            self.transportation_cost.append([self.env.now, self.delivery_cost()])
            self.node_cost += self.transportation_cost[-1][1]
            self.demand_node.products_sold = order_quantity
            return
        
        wait_time = 0
        while(wait_time<self.customer_tolerance):
            if(self.customer_tolerance<1):
                wait_time += self.customer_tolerance
                yield self.env.timeout(self.customer_tolerance)
            else:
                wait_time += 1
                yield self.env.timeout(1)
            if(order_quantity <= self.demand_node.inventory.inventory.level):
                if(self.demand_node.inventory.type=="perishable"):
                    event,  man_dt_ls = self.demand_node.inventory.inventory.get(order_quantity)
                    yield event 
                else:
                    yield self.demand_node.inventory.inventory.get(order_quantity)
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, remaining order quantity:{order_quantity}, available inventory:{self.demand_node.inventory.inventory.level}.")
                yield self.env.timeout(self.lead_time()) # wait for the delivery of the order
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} received. Current inv: {self.demand_node.inventory.inventory.level}")
                # update statistics
                self.product_sold.append((self.env.now, order_quantity))
                self.total_products_sold += order_quantity
                self.transportation_cost.append([self.env.now, self.delivery_cost()])
                self.node_cost += self.transportation_cost[-1][1]
                self.demand_node.products_sold = order_quantity
                return                
        self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, remaining order quantity:{order_quantity} not available! inventory:{self.demand_node.inventory.inventory.level}. No order placed.")
        self.unsatisfied_demand.append((self.env.now, order_quantity))

    def customer(self,id,order_quantity):
        """
        Simulate the customer behavior, ordering products from demand node, consume and return.

        Returns:
            None
        """
        if(order_quantity <= self.demand_node.inventory.inventory.level):
            if(self.demand_node.inventory.type=="perishable"):
                get_eve, man_date_ls = self.demand_node.inventory.inventory.get(order_quantity)
                yield get_eve
            else:
                yield self.demand_node.inventory.inventory.get(order_quantity)
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity}, available.")
            yield self.env.timeout(self.lead_time()) # wait for the delivery of the order
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} received. Current inv: {self.demand_node.inventory.inventory.level}")
            # update statistics
            self.product_sold.append((self.env.now, order_quantity))
            self.total_products_sold += order_quantity
            self.transportation_cost.append([self.env.now, self.delivery_cost()])
            self.node_cost += self.transportation_cost[-1][1]
            self.demand_node.products_sold = order_quantity
        elif(self.customer_tolerance>0):
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} not available, inventory level:{self.demand_node.inventory.inventory.level}. Place order for available amount.")  
            order_quantity = order_quantity - self.demand_node.inventory.inventory.level # calculate the remaining quantity to order
            if(self.demand_node.inventory.inventory.level>0): # consume if available
                consumed_quantity = self.demand_node.inventory.inventory.level
                if(self.demand_node.inventory.type=="perishable"):
                    get_eve, man_date_ls = self.demand_node.inventory.inventory.get(self.demand_node.inventory.inventory.level)
                    yield get_eve
                else:
                    yield self.demand_node.inventory.inventory.get(self.demand_node.inventory.inventory.level) # consume available quantity
                yield self.env.timeout(self.lead_time()) # wait for the delivery of the order
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{consumed_quantity} received. Current inv: {self.demand_node.inventory.inventory.level}")
                # set stats for the demand node
                self.product_sold.append((self.env.now, self.demand_node.inventory.inventory.level))
                self.total_products_sold += self.demand_node.inventory.inventory.level
                self.transportation_cost.append([self.env.now, self.delivery_cost()])
                self.node_cost += self.transportation_cost[-1][1]
                self.demand_node.products_sold = self.demand_node.inventory.inventory.level
            self.shortage.append((self.env.now, order_quantity)) # record the shortage
            self.env.process(self.wait_for_order(id,order_quantity)) # wait for the remaining quantity to be available
        else:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} not available, inventory level:{self.demand_node.inventory.inventory.level}. No tolerance! No order placed. Shortage:{order_quantity-self.demand_node.inventory.inventory.level}.")
            self.shortage.append((self.env.now, order_quantity-self.demand_node.inventory.inventory.level)) # record the shortage
            self.unsatisfied_demand.append((self.env.now, order_quantity))
    
    def behavior(self):
        """
        Generate demand by calling the order arrival and order quantity models.

        This method simulates the demand generation process, including order placement
        and handling shortages or unsatisfied demand.

        Returns:
            None
        """
        customer_id = 0 # customer ID
        while True:
            order_time = self.order_arrival_model()
            order_quantity = self.order_quantity_model()
            self.total_demand += order_quantity
            self.env.process(self.customer(customer_id, order_quantity)) # spawn a customer process
            customer_id += 1 # increment customer ID
            yield self.env.timeout(order_time) # wait for the next order arrival