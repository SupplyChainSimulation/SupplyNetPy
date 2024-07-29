from SupplyNetPy.Components.logger import GlobalLogger
import simpy
import copy

# global variables
global_logger = GlobalLogger() # create a global logger
env = simpy.Environment() # create a simulation environment

class RawMaterial():
    """
    RawMaterial class represents a raw material in the supply network.

    Parameters:
        ID (str): ID of the raw material (alphanumeric)
        name (str): name of the raw material
        extraction_quantity (float): quantity of the raw material that can be extracted in extraction_time
        extraction_time (float): time to extract the raw material
        cost (float): cost of the raw material (per item)

    Functions:
        __init__: initializes the raw material object
        __str__: returns the name of the raw material
        __repr__: returns the name of the raw material
    """
    def __init__(self, ID: str, name: str, extraction_quantity: float, extraction_time: float, cost: float) -> None:
        """
        Initialize the raw material object.

        Parameters:
            ID (str): ID of the raw material (alphanumeric)
            name (str): name of the raw material
            extraction_quantity (float): quantity of the raw material that can be extracted in extraction_time
            extraction_time (float): time to extract the raw material
            cost (float): cost of the raw material (per item)

        Returns:
            None
        """
        self.ID = ID # ID of the raw material (alphanumeric)
        self.name = name # name of the raw material
        self.extraction_quantity = extraction_quantity # quantity of the raw material that can be extracted in extraction_time
        self.cost = cost # cost of the raw material
        self.extraction_time = extraction_time # time to extract the raw material

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
        return {"ID": self.ID, "name": self.name, "extraction_quantity": self.extraction_quantity, "extraction_time": self.extraction_time, "cost": self.cost}

default_raw_material = RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=30, extraction_time=3, cost=1) # create a default raw material

class Product():
    """
    Product class represents a product in the supply network.

    Parameters:
        ID (str): ID of the product (alphanumeric)
        name (str): name of the product
        manufacturing_cost (float): manufacturing cost of the product
        manufacturing_time (int): time (days) to manufacture the product
        sell_price (float): price at which the product is sold
        buy_price (float): price at which the product is bought
        raw_materials (list): list of raw materials and quantity required to manufacture a single product unit
        units_per_cycle (int): number of units manufactured per manufacturing cycle

    Functions:
        __init__: initializes the product object
        __str__: returns the name of the product
        __repr__: returns the name of the product
    """
    def __init__(self, ID: str, name: str, manufacturing_cost: float, manufacturing_time: int, sell_price: float, raw_materials: list, units_per_cycle: int, buy_price: float = 0) -> None:
        """
        Initialize the product object.

        Parameters:
            ID (str): ID of the product (alphanumeric)
            name (str): name of the product
            manufacturing_cost (float): manufacturing cost of the product
            manufacturing_time (int): time (days) to manufacture the product
            sell_price (float): price at which the product is sold
            buy_price (float): price at which the product is bought
            raw_materials (list): list of raw materials and quantity required to manufacture a single product unit
            units_per_cycle (int): number of units manufactured per cycle

        Returns:
            None
        """
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
        return {"ID": self.ID, "name": self.name, "manufacturing_cost": self.manufacturing_cost, "manufacturing_time": self.manufacturing_time, "sell_price": self.sell_price, "buy_price": self.buy_price, "raw_materials": self.raw_materials, "units_per_cycle": self.units_per_cycle}
    
default_product = Product(ID="P1", name="Product 1", manufacturing_cost=100, manufacturing_time=10, sell_price=200, raw_materials=[{"raw_material": default_raw_material, "quantity": 9}], units_per_cycle=50) # create a default product

class MonitoredContainer(simpy.Container):
    """
    Extension of SimPy's Container class with monitoring capabilities.
    This class allows monitoring of the container's level over time.
    It records the inventory level and time at regular intervals
    to analyze and visualize the behavior of the container.
    
    Parameters:
        enable_monitoring (bool): Enable or disable monitoring of the container's level.

    Inherits from:
        simpy.Container

    Attributes:
        leveldata (list): A list to store recorded inventory levels.
        timedata (list): A list to store corresponding timestamps for recorded levels.
        avg_level (float): Time-averaged inventory level.
        last_level (int): Last recorded inventory level.
        last_timestamp (float): Timestamp of the last recorded level change.
    """

    def __init__(self, enable_monitoring, *args, **kwargs):
        """
        Initialize the MonitoredContainer.

        Parameters:
            enable_monitoring (bool): Enable or disable monitoring of the container's level.
            *args, **kwargs: Additional arguments to be passed to the simpy.Container constructor.
        """
        self.enable_monitoring = enable_monitoring
        super().__init__(*args, **kwargs)
        self.leveldata = []
        self.timedata = []

        self.avg_level = 0  # time-averaged inventory level
        self.last_level = super().capacity
        self.last_timestamp = 0

    def record_level(self):
        """
        Record the current level of the container.

        This method is called whenever the container's level changes.
        It records the current level and timestamp, and updates the time-averaged inventory level.
        """
        # update the time-averaged inventory level
        delta_t = self._env.now - self.last_timestamp
        if delta_t > 0:
            self.avg_level = ((self.avg_level * self.last_timestamp) + (delta_t * self.last_level)) / float(self._env.now)
        # record the current level
        self.last_timestamp = self._env.now
        self.last_level = self._level

        if self.enable_monitoring:
            self.leveldata.append(self._level)
            self.timedata.append(self._env.now)

    def _do_put(self, *args, **kwargs):
        """
        Internal method to handle a put operation on the container.

        This method overrides the _do_put method of simpy.Container.
        It records the container's level after the put operation.

        Returns:
            result: Result of the put operation.
        """
        result = super()._do_put(*args, **kwargs)
        self.record_level()
        return result

    def _do_get(self, *args, **kwargs):
        """
        Internal method to handle a get operation on the container.

        This method overrides the _do_get method of simpy.Container.
        It records the container's level after the get operation.

        Returns:
            result: Result of the get operation.
        """
        result = super()._do_get(*args, **kwargs)
        self.record_level()
        return result

class Inventory():
    """
    Inventory class represents an inventory in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        replenishment_policy (str): replenishment policy for the inventory

    Attributes:
        env (simpy.Environment): simulation environment
        capacity (int): maximum capacity of the inventory
        level (int): current inventory level
        replenishment_policy (str): replenishment policy for the inventory
        inventory (MonitoredContainer): monitored container to store the inventory level

    Functions:
        __init__: initializes the inventory object
        __str__: returns the name of the inventory
        __repr__: returns the name of the inventory
    """
    def __init__(self, capacity: int, initial_level: int, replenishment_policy: str, env: simpy.Environment = env) -> None:
        """
        Initialize the inventory object.

        Parameters:
            env (simpy.Environment): simulation environment
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            replenishment_policy (str): replenishment policy for the inventory

        Attributes:
            env (simpy.Environment): simulation environment
            capacity (int): maximum capacity of the inventory
            level (int): current inventory level
            replenishment_policy (str): replenishment policy for the inventory
            inventory (MonitoredContainer): monitored container to store the inventory level

        Returns:
            None
        """
        self.env = env # simulation environment
        self.capacity = capacity # maximum capacity of the inventory
        self.level = initial_level # initial inventory level
        self.replenishment_policy = replenishment_policy # replenishment policy for the inventory
        self.inventory = MonitoredContainer(env=self.env, enable_monitoring=True, capacity=capacity, init=initial_level) # create a monitored container

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class Node():
    """
    Node class represents a node in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the node (alphanumeric)
        name (str): name of the node
        node_type (str): type of the node
        isolated_logger (bool): flag to enable/disable isolated logger
        **kwargs: additional keyword arguments for logger

    Attributes:
        logger (GlobalLogger): logger object
        
    Functions:
        __init__: initializes the node object
        __str__: returns the name of the node
        __repr__: returns the name of the node
    """
    def __init__(self, ID: str, name: str, node_type: str, env: simpy.Environment = env, isolated_logger: bool = False, **kwargs) -> None:
        """
        Initialize the node object.

        Parameters:
            env (simpy.Environment): The simulation environment.
            ID (str): The ID of the node (alphanumeric).
            name (str): The name of the node.
            node_type (str): The type of the node.
            isolated_logger (bool, optional): Flag to enable/disable isolated logger. Defaults to False.
            **kwargs: Additional keyword arguments for the logger.

        Returns:
            None
        """
        self.ID = ID  # ID of the node (alphanumeric)
        self.name = name  # name of the node
        self.node_type = node_type  # type of the node
        self.logger = global_logger.logger  # global logger
        self.env = env  # simulation environment

        if isolated_logger:  # if individual logger is required
            self.logger = GlobalLogger(logger_name=self.name, **kwargs).logger  # create an isolated logger

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

class Link():
    """
    Link class represents a link in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the link (alphanumeric)
        source (Node): source node of the link
        target (Node): target node of the link
        cost (float): cost of transportation over the link
        lead_time (int): lead time of the link

    Functions:
        __init__: initializes the link object
        __str__: returns the name of the link
        __repr__: returns the name of the link
    """

    def __init__(self, ID: str, source: Node, target: Node, cost: float, lead_time: int, env: simpy.Environment = env) -> None:
        """
        Initialize the link object.

        Parameters:
            env (simpy.Environment): simulation environment
            ID (str): ID of the link (alphanumeric)
            source (Node): source node of the link
            target (Node): target node of the link
            cost (float): cost of transportation over the link
            lead_time (int): lead time of the link

        Returns:
            None
        """
        self.env = env  # simulation environment
        self.ID = ID  # ID of the link (alphanumeric)
        self.source = source  # source node of the link
        self.target = target  # target node of the link
        self.cost = cost  # cost of the link
        self.lead_time = lead_time  # lead time of the link

        self.target.suppliers.append(self)  # add the link as a supplier link to the target node

    def __str__(self):
        """
        Return the name of the link.

        Returns:
            str: The name of the link.
        """
        return self.name

    def __repr__(self):
        """
        Return the name of the link.

        Returns:
            str: The name of the link.
        """
        return self.name

class Supplier(Node):
    """
    Supplier class represents a supplier in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the supplier (alphanumeric)
        name (str): name of the supplier
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        inventory_holding_cost (float): inventory holding cost
        raw_material (RawMaterial): raw material supplied by the supplier
        isolated_logger (bool): flag to enable/disable isolated logger
        **krwargs: additional keyword arguments for logger

    Functions:
        __init__: initializes the supplier object
        __str__: returns the name of the supplier
        __repr__: returns the name of the supplier
        calculate_statistics: calculate statistics for the supplier
        get_statistics: get statistics for the supplier
        behavior: supplier behavior

    Behavior:
        The supplier keeps extracting raw material whenever the inventory is not full (infinite supply).
        Assume that a supplier can extract a single type of raw material. By default, it is the default raw material.
    """
    def __init__(self, ID: str, name: str, capacity: int, initial_level: int, inventory_holding_cost:float, raw_material: RawMaterial = default_raw_material,  env: simpy.Environment = env, isolated_logger:bool = False, **kwargs) -> None:
        """
        Initialize the supplier object.

        Parameters:
            env (simpy.Environment): simulation environment
            ID (str): ID of the supplier (alphanumeric)
            name (str): name of the supplier
            raw_material (RawMaterial): raw material supplied by the supplier
            isolated_logger (bool): flag to enable/disable isolated logger
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            
        Returns:
            None
        """
        super().__init__(ID=ID, name=name, node_type="supplier", isolated_logger=isolated_logger, **kwargs)
        self.env = env
        self.raw_material = raw_material # raw material supplied by the supplier. By default, it is the default raw material.
        self.inventory = Inventory(capacity=capacity, initial_level=initial_level, replenishment_policy="continuous")
        self.inventory_holding_cost = inventory_holding_cost # inventory holding cost
        self.env.process(self.behavior()) # start the behavior process

        # statistics
        self.total_raw_materials_mined = 0 # total raw materials mined/extracted
        self.total_material_cost = 0 # total cost of the raw materials mined/extracted
        self.total_raw_materials_sold = 0 # total raw materials sold
        self.profit = 0 # profit from the raw materials mined/extracted
        self.inventory_cost = 0 # total inventory cost
        self.transportation_cost = 0 # total transportation cost
        self.node_cost = 0 # total node cost
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
    
    def calculate_statistics(self):
        """
        Calculate statistics for the supplier.

        Parameters:
            None

        Returns:
            None
        """
        while True:
            yield self.env.timeout(1)
            self.inventory_cost += self.inventory_holding_cost * self.inventory.inventory.level
            self.total_material_cost = self.total_raw_materials_mined * self.raw_material.cost
            self.node_cost = self.total_material_cost + self.inventory_cost + self.transportation_cost

    def get_statistics(self):
        """
        Get statistics for the supplier.

        Parameters:
            None

        Returns:
            dict: dictionary containing statistics for the supplier
        """
        return {"total_raw_materials_mined": self.total_raw_materials_mined, "total_material_cost": self.total_material_cost, "total_raw_material_sold":self.total_raw_materials_sold, "profit": self.profit, "inventory_cost": self.inventory_cost, "transportation_cost": self.transportation_cost, "node_cost": self.node_cost}
    
    def behavior(self):
        """
        Supplier behavior: The supplier keeps extracting raw material whenever the inventory is not full (infinite supply).
        Assume that a supplier can extract a single type of raw material.

        Parameters:
            None

        Returns:
            None
        """
        while True:
            yield self.env.timeout(1)
            if(self.inventory.inventory.level < self.inventory.capacity): # check if the inventory is not full
                yield self.env.timeout(self.raw_material.extraction_time)
                if(self.inventory.inventory.level + self.raw_material.extraction_quantity <= self.inventory.capacity): # check if the inventory can accommodate the extracted quantity
                    self.inventory.inventory.put(self.raw_material.extraction_quantity)
                else: # else put the remaining capacity in the inventory
                    self.inventory.inventory.put(self.inventory.capacity - self.inventory.inventory.level)
                #self.logger.info(f"{self.env.now}:{self.ID}:Raw material mined/extracted. Inventory levels:{self.inventory.inventory.level}")
                # update statistics
                self.total_raw_materials_mined += self.raw_material.extraction_quantity

class Manufacturer(Node):
    """
    Manufacturer class represents a manufacturer in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the manufacturer (alphanumeric)
        name (str): name of the manufacturer
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        inventoty_holding_cost (float): inventory holding cost
        product (Product): product manufactured by the manufacturer
        suppliers (list): list of suppliers from which the manufacturer can replenish inventory
        replenishment_policy (str): replenishment policy for the inventory
        policy_param (list): parameters for the replenishment policy
        isolated_logger (bool): flag to enable/disable isolated logger
        **kwargs: additional keyword arguments for logger

    Functions:
        __init__: initializes the manufacturer object
        __str__: returns the name of the manufacturer
        __repr__: returns the name of the manufacturer
        calculate_statistics: calculate statistics for the manufacturer
        get_statistics: get statistics for the manufacturer
        behavior: manufacturer behavior - consume raw materials, produce the product, and put the product in the inventory

    Behavior:
        The manufacturer consumes raw materials and produces the product if raw materials are available, and puts the product in the inventory. 
        It maintains inventory levels for raw materials and the product. Initial raw material inventory is equally distributed to store
        raw materials from suppliers. The raw materials inventory is replenished from the suppliers according to the replenishment policy.
        The profit is calculated as the difference between the sell price and the buy price of the product. By default, the buy price is set 
        as the manufacturing cost of the product, and the sell price is set to 5% more than the buy price.
    """
    def __init__(self, ID: str, name: str, capacity: int, initial_level: int, inventoty_holding_cost:float, product: Product = default_product, suppliers: list = [], replenishment_policy: str = "sS", policy_param: list = [2], env: simpy.Environment = env, isolated_logger: bool = False, **kwargs) -> None:
        """
        Initialize the manufacturer object.

        Parameters:
            env (simpy.Environment): simulation environment
            ID (str): ID of the manufacturer (alphanumeric)
            name (str): name of the manufacturer
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            inventoty_holding_cost (float): inventory holding cost
            product (Product): product manufactured by the manufacturer
            suppliers (list): list of suppliers from which the manufacturer can replenish inventory
            replenishment_policy (str): replenishment policy for the inventory
            policy_param (list): parameters for the replenishment policy
            isolated_logger (bool): flag to enable/disable isolated logger
            **kwargs: additional keyword arguments for logger

        Returns:
            None
        """
        super().__init__(ID=ID, name=name, node_type="manufacturer", isolated_logger=isolated_logger, **kwargs)
        self.env = env
        self.capacity = capacity
        self.product = product
        self.initial_level = initial_level
        self.inventory_holding_cost = inventoty_holding_cost
        self.product = product # product manufactured by the manufacturer
        self.suppliers = suppliers
        self.replenishment_policy = replenishment_policy
        self.policy_param = policy_param

        self.materials_available = True
        self.inventory_counts = {} # dictionary to store inventory counts
        self.order_placed = {} # dictionary to store order status

        self.env.process(self.behavior()) # start the behavior process
        
        if(self.replenishment_policy == "sS"):
            self.env.process(self.ss_replenishment(s=self.policy_param[0])) # start the inventory replenishment process
        elif(self.replenishment_policy == "periodic"):
            self.env.process(self.periodic_replenishment(interval=self.policy_param[0], reorder_quantity=self.policy_param[1])) # start the inventory replenishment process

        # calculate the total cost of the product, and set the sell price
        self.product.buy_price = self.product.manufacturing_cost # total cost of the product
        for raw_material in self.product.raw_materials:
            self.product.buy_price += raw_material["raw_material"].cost * raw_material["quantity"] # calculate total cost of the product (per unit)
        
        self.product.sell_price = self.product.buy_price + 0.05 * self.product.buy_price # set the sell price as the buy price
        self.profit = self.product.sell_price - self.product.buy_price # set the sell price as the buy price

        # statistics
        self.total_products_manufactured = 0 # total products manufactured
        self.total_manufacturing_cost = 0 # total cost of the products manufactured
        self.total_profit = 0 # total profit from the products manufactured
        self.products_sold = 0 # products sold in the current cycle/period
        self.total_products_sold = 0 # total products sold
        self.revenue = 0 # revenue from the products sold
        self.inventory_cost = 0 # total inventory cost
        self.transportation_cost = 0 # total transportation_cost cost
        self.node_cost = 0 # total node cost
        self.net_profit = 0 # net profit
        self.env.process(self.calculate_statistics()) # calculate statistics
        
        
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    
    def calculate_statistics(self):
        """
        Calculate statistics for the manufacturer.

        Parameters:
            None

        Returns:
            None
        """
        while True:
            yield self.env.timeout(1)
            self.inventory_cost += self.inventory.inventory.level * self.inventory_holding_cost
            self.total_manufacturing_cost = self.total_products_manufactured * self.product.manufacturing_cost

            self.revenue = self.total_products_sold * self.product.sell_price
            self.total_profit = self.total_products_sold * self.profit
            
            self.node_cost = self.total_manufacturing_cost + self.inventory_cost + self.transportation_cost
            self.net_profit = self.revenue - self.node_cost
    
    def get_statistics(self):
        """
        Get statistics for the manufacturer.

        Parameters:
            None

        Returns:
            dict: dictionary containing statistics for the manufacturer
        """
        return {"total_products_manufactured": self.total_products_manufactured, "total_manufacturing_cost": self.total_manufacturing_cost, "total_profit": self.total_profit, "products_sold": self.products_sold, "total_products_sold": self.total_products_sold, "revenue": self.revenue, "inventory_cost": self.inventory_cost, "tranportation_cost": self.transportation_cost, "node_cost": self.node_cost, "net_profit": self.net_profit}

    def behavior(self):
        """
        Manufacturer behavior:  Consume raw materials and produce the product if raw materials are available, put the product in the inventory. 
        It maintains inventory levels for raw materials and the product. Initial raw material inventory is equally distributed to store
        raw materials from suppliers. The raw materials inventory is replenished from the suppliers according to the replenishment policy.
        
        Parameters:
            None

        Returns:
            None
        """
        ini_levels = self.initial_level
        # create an inventory for the manufacturer
        if(len(self.suppliers) > 0):
            if(self.initial_level>0):
                # calculate initial inventory levels, by default all suppliers have equal share
                # an alternate way is to take initial levels as input from the user
                ini_levels = self.initial_level/len(self.suppliers)
            else:
                ini_levels = 0
        self.inventory = Inventory(capacity=self.capacity, initial_level=self.initial_level, replenishment_policy=self.replenishment_policy)
        self.inventory_counts = {} # dictionary to store inventory counts
        for supplier in self.suppliers: # iterate over supplier links
            self.inventory_counts[supplier.source.raw_material.ID] = ini_levels # store initial levels
            self.order_placed[supplier.source.raw_material.ID] = False # store order status

        # behavior of the manufacturer: consume raw materials, produce the product, and put the product in the inventory
        while True:
            self.materials_available = True
            # check if raw materials are available
            for raw_material in self.product.raw_materials:
                if(self.inventory_counts[raw_material["raw_material"].ID] < raw_material["quantity"]):
                    self.materials_available = False
                    self.logger.info(f"{self.env.now}:{self.ID}: Raw materials not available.")

            # if raw materials are available then produce the product    
            if(self.materials_available and self.inventory.inventory.level < self.inventory.inventory.capacity):
                # produce the product
                yield self.env.timeout(self.product.manufacturing_time)
                self.logger.info(f"{self.env.now}:{self.ID}:Product manufactured.")
                # consume raw materials
                for raw_material in self.product.raw_materials:
                    self.inventory_counts[raw_material["raw_material"].ID] -= raw_material["quantity"]
                self.logger.info(f"{self.env.now}:{self.ID}: Raw material inventory levels:{self.inventory_counts}")
                # put the product units in the inventory
                if(self.inventory.inventory.level + self.product.units_per_cycle <= self.inventory.inventory.capacity):
                    self.inventory.inventory.put(self.product.units_per_cycle)
                else:
                    self.logger.info(f"{self.env.now}:{self.ID}:Inventory full, product not added.")
                    self.inventory.inventory.put(self.inventory.inventory.capacity - self.inventory.inventory.level)
                self.logger.info(f"{self.env.now}:{self.ID}: Product inventory levels:{self.inventory.inventory.level}")
                # update statistics
                self.total_products_manufactured += self.product.units_per_cycle
            yield self.env.timeout(1)

    def place_order(self, raw_material, reorder_quantity):
        """
        Place an order for raw materials from the suppliers.

        Parameters:
            order_quantity (int): quantity of raw material to order

        Returns:
            None
        """
        for supplier in self.suppliers: # check for the supplier of the raw material
            if(supplier.source.raw_material.ID == raw_material):
                self.logger.info(f"{self.env.now}:{self.ID}:Replenishing raw material:{supplier.source.raw_material.name} from supplier:{supplier.source.name}, order placed for {reorder_quantity} units.")
                yield supplier.source.inventory.inventory.get(reorder_quantity)
                self.logger.info(f"{self.env.now}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.")                
                # update the transportation cost at the supplier
                supplier.source.transportation_cost += supplier.cost
                # update the product sold at the raw material supplier
                supplier.source.total_raw_materials_sold += reorder_quantity
                yield self.env.timeout(supplier.lead_time) # lead time for the order
                self.order_placed[raw_material] = False
                self.inventory_counts[raw_material] += reorder_quantity
                self.logger.info(f"{self.env.now}:{self.ID}:Order received from supplier:{supplier.source.name}, inventory levels: {self.inventory_counts}")

    def ss_replenishment(self, s):
        """
        Monitored inventory replenishment policy (s,S): s represents the reorder point and S represents the inventory capacity. 
        Behavior: Replenish the inventory from the suppliers whenever the inventory level is below the reorder point (s). 

        Parameters:
            s (int): reorder point

        Returns:
            None
        """
        while True:
            yield self.env.timeout(1)
            for raw_material in self.inventory_counts:
                if(self.inventory_counts[raw_material] < s):
                    # how to calculate reorder quantity?
                    # for multiple raw materials, reorder quantity can be different for each raw material
                    # can be based on the proportion of raw materials used to manufacture the product
                    # currently, reorder quantity is calculated based on the remaining capacity of the inventory
                    # every raw material is allocated equal portion of the remaining capacity
                    reorder_quantity = (self.inventory.inventory.capacity - self.inventory.inventory.level)/len(self.suppliers)
                    if(not self.order_placed[raw_material]):
                        self.order_placed[raw_material] = True
                        self.env.process(self.place_order(raw_material, reorder_quantity))

    def periodic_replenishment(self, interval, reorder_quantity):
        """
        Monitored inventory replenishment policy (periodic): Replenish the inventory from the suppliers at regular intervals. 

        Parameters:
            interval (int): time interval for replenishment

        Returns:
            None
        """
        while True:
            yield self.env.timeout(interval) # time interval for replenishment
            for raw_material in self.inventory_counts:
                inventory_available = self.inventory.inventory.capacity - self.inventory.inventory.level
                if(not self.order_placed[raw_material] and inventory_available > reorder_quantity):
                    self.order_placed[raw_material] = True
                    self.env.process(self.place_order(raw_material, reorder_quantity))

class InventoryNode(Node):
    """
    InventoryNode class represents an inventory node in the supply network.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the inventory node (alphanumeric)
        name (str): name of the inventory node
        node_type (str): type of the inventory node (retailer or distributor)
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        inventory_holding_cost (float): inventory holding cost
        suppliers (list): list of supplier links from which the inventory node can replenish inventory
        replenishment_policy (str): replenishment policy for the inventory
        policy_param (list): parameters for the replenishment policy
        product (Product): product that the inventory node sells

    Functions:
        __init__: initializes the inventory node object
        __str__: returns the name of the inventory node
        __repr__: returns the name of the inventory node
        calculate_statistics: calculate statistics for the inventory node
        get_statistics: get statistics for the inventory node
        place_order: place an order for the product from the suppliers
        ss_replenishment: monitored inventory replenishment policy (s,S)
        periodic_replenishment: monitored inventory replenishment policy (periodic)
    """

    def __init__(self, ID: str, name: str, node_type: str, capacity: int, initial_level: int, inventory_holding_cost:float, suppliers: list = [], replenishment_policy: str = "sS", policy_param: list = [2], product:Product = default_product, env: simpy.Environment = env) -> None:
        """
        Initialize the inventory node object.

        Parameters:
            env (simpy.Environment): simulation environment
            ID (str): ID of the inventory node (alphanumeric)
            name (str): name of the inventory node
            inventory (Inventory): inventory object
            node_type (str): type of the inventory node (retailer or distributor)
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            suppliers (list): list of supplier links from which the inventory node can replenish inventory
            replenishment_policy (str): replenishment policy for the inventory
            policy_param (list): parameters for the replenishment policy

        Returns:
            None

        Behavior:
            The inventory node sells the product to the customers. It replenishes the inventory from the suppliers according to the replenishment policy. 
            The inventory node can have multiple suppliers. It chooses a supplier based on the availability of the product at the suppliers.
            The product buy price is set to the sell price of the supplier. The inventory node sells the product at a higher price than the buy price.
            By default, the sell price is set to 5% more than the buy price. The product sell price can be set by the user, if required.
        """
        super().__init__(ID=ID, name=name, node_type=node_type)
        self.env = env
        self.node_type = node_type
        self.capacity = capacity
        self.initial_level = initial_level
        self.inventory_holding_cost = inventory_holding_cost
        self.suppliers = suppliers
        self.replenishment_policy = replenishment_policy
        self.policy_param = policy_param
        self.inventory = Inventory(capacity=capacity, initial_level=initial_level, replenishment_policy=replenishment_policy)
        self.product = copy.deepcopy(product) # product that the inventory node sells
        self.product.sell_price = 0 # set the sell price of the product initially to 0, since buy price will be updated based on the supplier
        self.order_placed = False # flag to check if the order is placed
    
        if(self.replenishment_policy == "sS"):
            self.env.process(self.ss_replenishment(s=self.policy_param[0]))
        elif(self.replenishment_policy == "periodic"):
            self.env.process(self.periodic_replenishment(interval=self.policy_param[0], reorder_quantity=self.policy_param[1]))

        # statistics
        self.total_products_sold = 0 # total products sold
        self.products_sold = 0 # products sold in the current cycle/period/day
        self.total_product_cost = 0 # total cost of the products bought
        self.total_revenue = 0 # total revenue from the products sold
        self.total_profit = 0 # total profit from the products sold
        self.inventory_cost = 0 # total inventory cost
        self.transportation_cost = 0 # total transportation cost
        self.node_cost = 0 # total node cost
        self.net_profit = 0 # net profit
        self.env.process(self.calculate_statistics()) # calculate statistics
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    
    def calculate_statistics(self):
        """
        Calculate statistics for the inventory node.

        Parameters:
            None

        Returns:
            None
        """
        while True:
            # reset the products sold in the current cycle
            self.products_sold = 0
            yield self.env.timeout(1)
            if(self.product.sell_price == 0):
                self.product.sell_price = self.product.buy_price + 0.05 * self.product.buy_price
            self.inventory_cost += self.inventory_holding_cost * self.inventory.inventory.level
            self.total_product_cost += self.products_sold * self.product.buy_price
            self.total_revenue = self.total_products_sold * self.product.sell_price
            self.total_profit = self.total_revenue - self.total_product_cost
            self.node_cost = self.inventory_cost + self.transportation_cost
            self.net_profit = self.total_profit - self.node_cost

    def get_statistics(self):
        """
        Get statistics for the inventory node.

        Parameters:
            None

        Returns:
            dict: dictionary containing statistics for the inventory node
        """
        return {"total_products_sold": self.total_products_sold, "products_sold": self.products_sold, "total_product_cost": self.total_product_cost, "total_revenue": self.total_revenue, "total_profit": self.total_profit, "inventory_cost": self.inventory_cost, "transportation_cost": self.transportation_cost, "node_cost": self.node_cost, "net_profit": self.net_profit}

    def place_order(self, supplier, reorder_quantity):
        """
        Place an order for the product from the suppliers.

        Parameters:
            s (int): reorder point

        Returns:
            None
        """
        self.logger.info(f"{self.env.now}:{self.ID}:Replenishing inventory from supplier:{supplier.source.name}, order placed for {reorder_quantity} units.")
        yield supplier.source.inventory.inventory.get(reorder_quantity) # get the product from the supplier inventory
        # update the product costs
        self.product.buy_price = supplier.source.product.sell_price
        # update the transportation cost at the supplier
        supplier.source.transportation_cost += supplier.cost
        # update the product sold at the supplier
        supplier.source.products_sold = reorder_quantity
        supplier.source.total_products_sold += reorder_quantity
        # log the shipment
        self.logger.info(f"{self.env.now}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.")
        yield self.env.timeout(supplier.lead_time) # lead time for the order
        self.inventory.inventory.put(reorder_quantity)
        self.logger.info(f"{self.env.now}:{self.ID}:Inventory replenished. Inventory levels:{self.inventory.inventory.level}")
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
        while True:
            yield self.env.timeout(1)
            if(self.inventory.inventory.level < s):
                # reorder quantity is calculated based on the remaining capacity of the inventory
                reorder_quantity = self.inventory.inventory.capacity - self.inventory.inventory.level
                # choose a supplier to replenish the inventory based on the availablity of the product
                # check availablity of the product at suppliers
                for supplier in self.suppliers:
                    if(supplier.source.inventory.inventory.level > reorder_quantity and self.order_placed == False):
                        self.order_placed = True
                        env.process(self.place_order(supplier, reorder_quantity))
                if(self.order_placed == False):
                    # required quantity not available at any suppliers
                    # backlog order logic can be added here. 
                    # Get whatever is available, and place the order for the remaining quantity from another supplier and so on.
                    # If the required quantity is still not satisfied, then backlog the order.clear
                    self.logger.info(f"{self.env.now}:{self.ID}:Product not available at suppliers. Required quantity:{reorder_quantity}.")
    
    def periodic_replenishment(self, interval, reorder_quantity):
        """
        Monitored inventory replenishment policy (periodic): Replenish the inventory from the suppliers at regular intervals. 

        Parameters:
            interval (int): time interval for replenishment

        Returns:
            None
        """
        while True:
            yield self.env.timeout(interval)
            if(self.inventory.inventory.level < self.inventory.inventory.capacity):
                # choose a supplier to replenish the inventory based on the availablity of the product
                # check availablity of the product at suppliers
                for supplier in self.suppliers:
                    if(supplier.source.inventory.inventory.level > reorder_quantity and self.order_placed == False):
                        self.order_placed = True
                        env.process(self.place_order(supplier, reorder_quantity))

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

    Functions:
        __init__: initializes the demand node object
        __str__: returns the name of the demand node
        __repr__: returns the name of the demand node
        behavior: generates demand by calling the order arrival and order quantity models
    """

    def __init__(self, ID: str, name: str, order_arrival_model: callable, order_quantity_model: callable, demand_node: Node, product: Product = default_product, env: simpy.Environment = env) -> None:
        """
        Initialize the demand node object.

        Parameters:
            env (simpy.Environment): simulation environment
            ID (str): ID of the demand node (alphanumeric)
            name (str): name of the demand node
            order_arrival_model (function): function that models order arrivals
            order_quantity_model (function): function that models order quantity
            demand_node (Node): node at which the demand is generated

        Returns:
            None
        """
        super().__init__(ID=ID, name=name, node_type="demand")
        self.order_arrival_model = order_arrival_model
        self.order_quantity_model = order_quantity_model
        self.demand_node = demand_node
        self.env = env
        self.env.process(self.behavior())

        self.unsatisfied_demand = 0

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

    def behavior(self):
        """
        Generate demand by calling the order arrival and order quantity models.

        Parameters:
            env (simpy.Environment): simulation environment

        Returns:
            None
        """
        while True:
            order_time = self.order_arrival_model()
            order_quantity = self.order_quantity_model()
            if(order_quantity <= self.demand_node.inventory.inventory.level):
                self.demand_node.inventory.inventory.get(order_quantity)
                self.logger.info(f"{self.env.now}:{self.ID}:Demand at {self.demand_node}, Order quantity:{order_quantity} received, inventory level:{self.demand_node.inventory.inventory.level}.")
                # update statistics
                self.demand_node.products_sold = order_quantity
                self.demand_node.total_products_sold += order_quantity                
            else:
                self.logger.info(f"{self.env.now}:{self.ID}:Demand at {self.demand_node}, Order quantity:{order_quantity} not available, inventory level:{self.demand_node.inventory.inventory.level}.")
                self.unsatisfied_demand += order_quantity            
            yield self.env.timeout(order_time)

if __name__ == "__main__": 
    # create a supplier
    supplier1 = Supplier(ID="S1", name="Supplier 1", capacity=1000, initial_level=1000, inventory_holding_cost=1)
    raw_material2 = RawMaterial(ID="RM2", name="Raw Material 2", extraction_quantity=20, extraction_time=2, cost=15)
    supplier2 = Supplier(ID="S2", name="Supplier 2", capacity=1000, initial_level=1000, inventory_holding_cost=1, raw_material=raw_material2)
    # create a manufacturer
    default_product.raw_materials = [{"raw_material": default_raw_material, "quantity": 9}, {"raw_material": raw_material2, "quantity": 5}]
    manufacturer1 = Manufacturer(ID="M1", name="Manufacturer 1", capacity=500, initial_level=300, inventoty_holding_cost=3, replenishment_policy="sS", policy_param=[200])
    link_sup1_man1 = Link(ID="L1", source=supplier1, target=manufacturer1, cost=5, lead_time=3)
    link_sup2_man1 = Link(ID="L2", source=supplier2, target=manufacturer1, cost=7, lead_time=2)
    distributor1 = InventoryNode(ID="D1", name="Distributor 1", node_type="distributor", capacity=300, initial_level=50, inventory_holding_cost=3, replenishment_policy="sS", policy_param=[30])
    link_man1_dis1 = Link(ID="L3", source=manufacturer1, target=distributor1, cost=50, lead_time=2)
    demand_dis = Demand(ID="demand_D1", name="Demand 1", order_arrival_model=lambda: 1, order_quantity_model=lambda: 5, demand_node=distributor1)
    print("Simulation started.")
    #  run the simulation
    env.run(until=100)
    # get statistics
    print(supplier1.get_statistics())
    print(supplier2.get_statistics())
    print(manufacturer1.get_statistics())
    print(distributor1.get_statistics())
