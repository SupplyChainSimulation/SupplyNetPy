from SupplyNetPy.Components.logger import GlobalLogger
import simpy
import copy
import random
import numbers

global_logger = GlobalLogger() # create a global logger

def validate_positive(name: str, value):
    """
    Check if the value is positive and raise ValueError if not.

    Parameters:
        name (str): name of the variable
        value: value to check   

    Raises:
        ValueError: if value is not positive
    """
    if value <= 0:
        global_logger.logger.error(f"{name} must be positive.")
        raise ValueError(f"{name} must be positive.")

def validate_non_negative(name: str, value):
    """
    Check if the value is non-negative and raise ValueError if not.

    Parameters:
        name (str): name of the variable
        value: value to check

    Raises:
        ValueError: if value is negative
    """
    if value < 0:
        global_logger.logger.error(f"{name} cannot be negative.")
        raise ValueError(f"{name} cannot be negative.")

def validate_number(name: str, value) -> None:
    """
    Check if the value is a number and raise ValueError if not.

    Parameters:
        name (str): name of the variable
        value: value to check

    Raises:
        ValueError: if value is not a number
    """
    if not isinstance(value, numbers.Number):
        global_logger.logger.error(f"function {name}() must return a number (an int or a float).")
        raise ValueError(f"function {name}() must return a number (an int or a float).")

class NamedEntity:
    """
    Base class for any object with a name to standardize __str__ and __repr__.
    
    Parameters:
        None

    Attributes:
        None

    Functions:
        __str__: returns the name of the object if available, otherwise returns the class name
        __repr__: returns the name of the object if available, otherwise returns the class name
    """
    def __str__(self):
        """Returns the name of the object if available, otherwise returns the class name."""
        return getattr(self, 'name', self.__class__.__name__)

    def __repr__(self):
        """Returns the name of the object if available, otherwise returns the class name."""
        return getattr(self, 'name', self.__class__.__name__)

class InfoMixin:
    """
    Mixin that provides a standard get_info and get_statistics method.
    Override _info_keys to filter attributes. Override _stats_keys to filter statistics.

    Parameters:
        None

    Attributes:
        _info_keys (list): list of keys to include in the info dictionary
        _stats_keys (list): list of keys to include in the statistics dictionary

    Functions:
        get_info: returns a dictionary containing details of the object
        get_statistics: returns a dictionary containing statistics of the object
    """
    _info_keys = []
    _stats_keys = []

    def get_info(self):
        """
        Returns a dictionary containing details of the object.

        Parameters:
            None
        
        Attributes: 
            None        

        Returns:
            dict: dictionary containing details of the object
        """
        if self._info_keys:
            return {key: getattr(self, key, None) for key in self._info_keys}
        return self.__dict__
    
    def get_statistics(self):
        """
        Returns a dictionary containing statistics of the object.

        Parameters:
            None
        
        Attributes: 
            None   

        Returns:
            dict: dictionary containing statistics of the object
        """
        if self._stats_keys:
            return {key: getattr(self, key, None) for key in self._stats_keys}
        return self.__dict__

class RawMaterial(NamedEntity, InfoMixin):
    """
    RawMaterial class represents a raw material in the supply network.

    Parameters:
        ID (str): ID of the raw material (alphanumeric)
        name (str): name of the raw material
        extraction_quantity (float): quantity of the raw material that is extracted in extraction_time
        extraction_time (float): time to extract the raw material 
        mining_cost (float): mining cost of the raw material (per item)
        cost (float): selling cost of the raw material (per item)

    Attributes:
        _info_keys (list): list of keys to include in the info dictionary
        ID (str): ID of the raw material (alphanumeric)
        name (str): name of the raw material
        extraction_quantity (float): quantity of the raw material that can be extracted in extraction_time
        extraction_time (float): time to extract the raw material
        mining_cost (float): mining cost of the raw material (per item)
        cost (float): selling cost of the raw material (per item)

    Functions:
        __init__: initializes the raw material object
    """
    _info_keys = ["ID", "name", "extraction_quantity", "extraction_time", "mining_cost", "cost"]
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

        Attributes:
            ID (str): ID of the raw material (alphanumeric)
            name (str): name of the raw material
            extraction_quantity (float): quantity of the raw material that can be extracted in extraction_time
            extraction_time (float): time to extract the raw material
            mining_cost (float): mining cost of the raw material (per item)
            cost (float): selling cost of the raw material (per item)

        Returns:
            None
        """
        validate_positive("Extraction quantity", extraction_quantity)
        validate_non_negative("Extraction time", extraction_time)
        validate_positive("Cost", cost)

        self.ID = ID # ID of the raw material (alphanumeric)
        self.name = name # name of the raw material
        self.extraction_quantity = extraction_quantity # quantity of the raw material that can be extracted in extraction_time
        self.extraction_time = extraction_time # time to extract the raw material
        self.mining_cost = mining_cost
        self.cost = cost # mining cost of the raw material

class Product(NamedEntity, InfoMixin):
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
    
    Attributes:
        _info_keys (list): list of keys to include in the info dictionary
        ID (str): ID of the product (alphanumeric)
        name (str): name of the product
        manufacturing_cost (float): manufacturing cost of the product
        manufacturing_time (int): time to manufacture the product
        sell_price (float): price at which the product is sold
        buy_price (float): price at which the product is bought
        raw_materials (list): list of raw materials and respective quantity required to manufacture one unit of the product
        units_per_cycle (int): number of units manufactured per cycle    
        
    Functions:
        __init__: initializes the product object
    """
    _info_keys = ["ID", "name", "manufacturing_cost", "manufacturing_time", "sell_price", "buy_price", "raw_materials", "units_per_cycle"]
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

        Attributes:
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
        validate_positive("Manufacturing cost", manufacturing_cost)
        validate_non_negative("Manufacturing time", manufacturing_time)
        validate_positive("Sell price", sell_price)
        validate_non_negative("Buy price", buy_price)
        validate_positive("Units per cycle", units_per_cycle)

        self.ID = ID # ID of the product (alphanumeric)
        self.name = name # name of the product
        self.manufacturing_cost = manufacturing_cost # manufacturing cost of the product
        self.manufacturing_time = manufacturing_time # time (days) to manufacture the product
        self.sell_price = sell_price # price at which the product is sold
        self.buy_price = buy_price # price at which the product is bought, (default: 0). It is used by InventoryNode buy the product at some price and sell it at a higher price.   
        self.raw_materials = raw_materials # list of raw materials and quantity required to manufacture a single product unit
        self.units_per_cycle = units_per_cycle # number of units manufactured per cycle

default_raw_material = RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=30, extraction_time=3, mining_cost=0.3, cost=1) # create a default raw material
default_product = Product(ID="P1", name="Product 1", manufacturing_cost=50, manufacturing_time=3, sell_price=341, raw_materials=[{"raw_material": default_raw_material, "quantity": 3}], units_per_cycle=30) # create a default product

class ReplenishmentPolicy(InfoMixin):
    """
    Base class for replenishment policies. This class can be extended to implement specific replenishment policies.
    
    Parameters:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy
    
    Attributes:
        _info_keys (list): list of keys to include in the info dictionary
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy
    
    functions:
        __init__: initializes the replenishment policy object
        run: this method should be overridden by subclasses to implement the specific replenishment policy logic
    """
    _info_keys = ["node", "params"]
    def __init__(self, env: simpy.Environment, 
                 node: object, 
                 params: dict) -> None:
        """
        Initialize the replenishment policy object.
        
        Parameters:
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy

        Attributes:
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy
            
        Returns:
            None
        """
        self.env = env  # simulation environment
        self.node = node  # node to which this policy applies
        self.params = params  # parameters for the replenishment policy
    
    def run(self):
        """
        This method should be overridden by subclasses to implement the specific replenishment policy logic.
        """
        pass

class SSReplenishment(ReplenishmentPolicy):
    """
    sS Replenishment Policy: If the inventory level falls below the reorder point (s), an order is placed to replenish the inventory up to the order-up-to level (S).
    
    Parameters:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy (s, S)

    Attributes:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy (s, S)
    
    Functions:
        run: replenishes the inventory based on the sS policy
    """
    def run(self):
        """
        Replenishes the inventory based on the sS policy.

        Parameters:
            None

        Attributes: 
            name (str): replenishment policy name
            _info_keys (list): list of keys to include in the info dictionary

        Returns:
            None    
        """
        self.name = "min-max replenishment (s S)"
        self._info_keys.append("name")
        s, S = self.params['s'], self.params['S']  # get the reorder point and order-up-to level
        yield self.env.timeout(0.999)  # wait for the end of the day
        while True:
            self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.inventory.level}")
            if(self.node.inventory.inventory.level <= s):
                order_quantity = S - self.node.inventory.inventory.level  # calculate the order quantity
                if order_quantity > 0:  # if order quantity is positive
                    for supplier in self.node.suppliers: # choose a supplier based on availability
                        if supplier.source.inventory.inventory.level >= order_quantity and self.node.order_placed == False: # if sufficient quantity is available at the supplier
                            self.node.order_placed = True # place the order
                            self.env.process(self.node.place_order(supplier, order_quantity))  # place the order
                    if(not self.node.order_placed): # if order could not be placed
                        self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}:Product not available at suppliers. Required quantity:{order_quantity}.")                    
            yield self.env.timeout(1)

class SSWithSafetyReplenishment(ReplenishmentPolicy):
    """
    sS with Safety Replenishment: If the inventory level falls below the reorder point (s) plus safety stock, an order is placed to replenish the inventory up to the order-up-to level (S).
    
    Parameters:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy (s, S, safety_stock)

    Attributes:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy (s, S, safety_stock)
    
    Functions:
        run: replenishes the inventory based on the sS with safety policy
    """
    def run(self):
        """
        Replenishes the inventory based on the sS with safety policy.

        Parameters:
            None
        
        Attributes:
            name (str): replenishment policy name
            _info_keys (list): list of keys to include in the info dictionary
        
        Returns:
            None
        """
        self.name = "min-max with safety stock replenishment (s, S, safety_stock)"
        self._info_keys.append("name")
        s, S, safety_stock = self.params['s'], self.params['S'], self.params['safety_stock']  # get the reorder point, order-up-to level and safety stock
        yield self.env.timeout(0.999)  # wait for the end of the day
        while True:
            self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.inventory.level}")
            if(self.node.inventory.inventory.level <= (s + safety_stock)):  # check if inventory level is below reorder point + safety stock
                order_quantity = S - self.node.inventory.inventory.level  # calculate the order quantity
                if order_quantity > 0:  # if order quantity is positive
                    for supplier in self.node.suppliers: # choose a supplier based on availability
                        if supplier.source.inventory.inventory.level >= order_quantity and self.node.order_placed == False: # if sufficient quantity is available at the supplier
                            self.node.order_placed = True # place the order
                            self.env.process(self.node.place_order(supplier, order_quantity))  # place the order
                    if(not self.node.order_placed): # if order could not be placed
                        self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}:Product not available at suppliers. Required quantity:{order_quantity}.")                    
            yield self.env.timeout(1)

class RQReplenishment(ReplenishmentPolicy):
    """
    Reorder Quantity (RQ) Replenishment Policy: If the inventory level falls below the reorder point (R), an order is placed to replenish the inventory by a fixed quantity (Q).
    
    Parameters:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy (R, Q)
    
    Attributes:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy (R, Q)
    
    Functions:
        run: replenishes the inventory based on the RQ policy
    """
    def run(self):
        """
        Replenishes the inventory based on the RQ policy.

        Parameters:
            None

        Attributes:
            name (str): replenishment policy name
            _info_keys (list): list of keys to include in the info dictionary

        Returns:
            None            
        """
        self.name = "RQ replenishment (R, Q)"
        self._info_keys.append("name")
        R, Q = self.params['R'], self.params['Q']  # get the reorder point and order quantity
        yield self.env.timeout(0.999)  # wait for the end of the day
        while True:
            self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.inventory.level}")
            if(self.node.inventory.inventory.level <= R):  # check if inventory level is below reorder point
                if(self.node.order_placed == False):  # if order is not already placed
                    for supplier in self.node.suppliers: # choose a supplier based on availability
                        if(supplier.source.inventory.inventory.level >= Q):
                            self.node.order_placed = True  # place the order
                            self.env.process(self.node.place_order(supplier, Q))  # place the order
                    if(not self.node.order_placed): # if order could not be placed
                        self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}:Product not available at suppliers. Required quantity:{Q}.")
            yield self.env.timeout(1)

class PeriodicReplenishment(ReplenishmentPolicy):
    """
    Periodic Replenishment Policy: Replenishes the inventory at regular intervals (T) by a fixed quantity (Q).
    
    Parameters:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy (T, Q)

    Attributes:
        env (simpy.Environment): simulation environment
        node (object): node to which this policy applies
        params (dict): parameters for the replenishment policy (T, Q)
    
    Functions:
        run: replenishes the inventory based on the periodic policy
    """
    def run(self):
        """
        Replenishes the inventory based on the periodic policy.

        Parameters:
            None

        Attributes:
            name (str): replenishment policy name
            _info_keys (list): list of keys to include in the info dictionary

        Returns:
            None
        """
        self.name = "Periodic replenishment (T, Q)"
        self._info_keys.append("name")
        T, Q = self.params['T'], self.params['Q']  # get the period and quantity
        yield self.env.timeout(0.999)  # wait for the end of the day
        while True:
            self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.inventory.level}")
            for supplier in self.node.suppliers: # choose a supplier to replenish the inventory based on the availablity of the product
                if(supplier.source.inventory.inventory.level > Q):
                    self.order_placed = True
                    self.env.process(self.node.place_order(supplier, Q))
                    break
            if(self.order_placed == False): # required quantity not available at any suppliers (order cannot be placed)
                self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}:Product not available at suppliers. Required quantity:{Q}.")
            yield self.env.timeout(T)

class PerishableInventory(simpy.Container):
    """
    Represents a perishable inventory in the supply network. It inherits from simpy.Container.
    
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
        logger (GlobalLogger): logger object
    
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

        Attributes:
            None
        
        Returns:
            None
        """
        if(amount+self.level>self.capacity): # check if amount can be put in inventory, otherwise adjust it
            amount = self.capacity - self.level
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

        Attributes:
            None
       
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

        Attributes:
            None

        Return: 
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
                self.logger.info(f"Current inventory levels:{self.perish_queue}")
                
class Inventory(NamedEntity, InfoMixin):
    """
    Inventory class represents an inventory in the supply network.
    
    Parameters:
        env (simpy.Environment): simulation environment
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        shelf_life (int): shelf life of the product
        replenishment_policy (str): replenishment policy for the inventory
        inv_type (str): type of the inventory (non-perishable/perishable)
    
    Attributes:
        _info_keys (list): list of keys to include in the info dictionary
        _stats_keys (list): list of keys to include in the statistics dictionary
    
    Functions:
        __init__: initializes the inventory object
        get_info: returns a dictionary containing details of the inventory
        record_inventory_levels: records inventory levels every day
    """
    _info_keys = ["capacity", "initial_level", "replenishment_policy", "shelf_life", "type"]
    _stats_keys = ["level", "inventory_spend", "instantaneous_levels"]
    def __init__(self, env: simpy.Environment, 
                 capacity: int, 
                 initial_level: int, 
                 replenishment_policy: ReplenishmentPolicy,
                 shelf_life: int = 0,
                 inv_type: str = "non-perishable") -> None:
        """
        Initialize the inventory object.
        
        Parameters:
            env (simpy.Environment): simulation environment
            capacity (int): maximum capacity of the inventory
            initial_level (int): initial inventory level
            replenishment_policy (ReplenishmentPolicy): replenishment policy for the inventory
            inv_type (str): type of the inventory (non-perishable/perishable)
            shelf_life (int): shelf life of the product
        
        Attributes:
            env (simpy.Environment): simulation environment
            capacity (int): maximum capacity of the inventory
            init_level (int): initial inventory level
            level (int): current inventory level
            inventory (simpy.Container): inventory container
            inv_type (str): type of the inventory (non-perishable/perishable)
            replenishment_policy (ReplenishmentPolicy): replenishment policy for the inventory
            instantaneous_levels (list): list to store inventory levels at regular intervals
            inventory_spend (list): list to store inventory replenishment costs. Every record contains (time of order, cost of order)
        
        Returns:
            None
        """
        if(initial_level > capacity):
            global_logger.logger.error("Initial level cannot be greater than capacity.")
            raise ValueError("Initial level cannot be greater than capacity.")
        
        if replenishment_policy is not None:
            if not isinstance(replenishment_policy, type):
                global_logger.logger.error(f"Replenishment policy must be a class, got {type(replenishment_policy)}")
                raise TypeError(f"replenishment policy must be a class, got {type(replenishment_policy)}")
            if not issubclass(replenishment_policy, ReplenishmentPolicy):
                global_logger.logger.error(f"{replenishment_policy.__name__} must inherit from ReplenishmentPolicy")
                raise TypeError(f"{replenishment_policy.__name__} must inherit from ReplenishmentPolicy")

        if(inv_type not in ["non-perishable", "perishable"]):
            global_logger.logger.error(f"Invalid inventory type. {type} is not yet available.")
            raise ValueError(f"Invalid inventory type. {type} is not yet available.")
        
        validate_positive("Capacity", capacity)
        validate_non_negative("Initial level", initial_level)

        self.env = env # simulation environment
        self.capacity = capacity # maximum capacity of the inventory
        self.init_level = initial_level # initial inventory level
        self.level = initial_level # initial inventory level
        self.inventory = simpy.Container(env=self.env,capacity=self.capacity, init=self.init_level) # create an inventory
        self.inv_type = inv_type
        if(self.inv_type=="perishable"):
            self.inventory = PerishableInventory(env=self.env, capacity=self.capacity, initial_level=self.init_level, shelf_life=shelf_life, replenishment_policy=replenishment_policy)
        self.instantaneous_levels = []
        self.inventory_spend = [] # inventory replenishment costs. Calculated as (order size) * (product buy cost). Every record contains (time of order, cost of order)
        self.env.process(self.record_inventory_levels()) # start recording the inventory levels
    
    def record_inventory_levels(self):
        """
        This method records the inventory levels at regular intervals.

        Parameters:
            None

        Attributes:
            None

        Returns:
            None
        """
        yield self.env.timeout(0.9999) # wait for the end of the day
        self.instantaneous_levels.append([self.env.now, self.inventory.level]) # record the initial inventory level
        while True:
            yield self.env.timeout(1) # record inventory levels at the end of every day/period
            self.instantaneous_levels.append([self.env.now, self.inventory.level])

class Node(NamedEntity, InfoMixin):
    """
    Node class represents a node in the supply network.
    
    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): ID of the node (alphanumeric)
        name (str): name of the node
        node_type (str): type of the node
        failure_p (float): node failure probability
        node_disrupt_time (callable): function to model node disruption time
        node_recovery_time (callable): function to model node recovery time
        isolated_logger (bool): flag to enable/disable isolated logger
        **kwargs: additional keyword arguments for logger (GlobalLogger)

    Attributes:
        _info_keys (list): list of keys to include in the info dictionary
        _stats_keys (list): list of keys to include in the statistics dictionary
    
    Functions:
        __init__: initializes the node object
        disruption: disrupt the node
    """
    _info_keys = ["ID", "name", "node_type", "failure_p"]
    _stats_keys = ["node_status", "inventory_cost", "transportation_cost", "node_cost", "profit", "revenue", "net_profit", "products_sold", "total_products_sold", "total_profit", "orders_placed", "orders_shortage"]
    def __init__(self, env: simpy.Environment, 
                 ID: str, 
                 name: str, 
                 node_type: str, 
                 failure_p:float = 0.0, 
                 node_disrupt_time:callable = None,
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
            node_disrupt_time (callable): function to model node disruption time
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
            orders_placed (list): list of orders placed to this node (demand). Each order is a tuple of (time of order, consumer ID, quantity ordered)
            order_shortage (list): list of order shortage. Each record is a tuple of (time of order, consumer ID, quantity ordered, quantity available)

        Returns:
            None
        """
        if(node_type.lower() not in ["infinite_supplier","supplier", "manufacturer", "factory", "warehouse", "distributor", "inventory", "retailer", "demand"]):
            global_logger.logger.error(f"Invalid node type. Node type: {node_type}")
            raise ValueError("Invalid node type.")
        
        self.ID = ID  # ID of the node (alphanumeric)
        self.name = name  # name of the node
        self.node_type = node_type  # type of the node (supplier, manufacturer, warehouse, distributor, retailer, demand)
        self.env = env  # simulation environment
        self.node_failure_p = failure_p  # node failure probability
        self.node_status = "active"  # node status (active/inactive)
        self.node_disrupt_time = node_disrupt_time  # callable function to model node disruption time
        self.node_recovery_time = node_recovery_time  # callable function to model node recovery time
        self.logger = global_logger.logger  # global logger
        if isolated_logger:  # if individual logger is required
            self.logger = GlobalLogger(logger_name=self.name, **kwargs).logger  # create an isolated logger

        # performance metrics for node
        self.inventory_cost = 0 # total inventory cost
        self.transportation_cost = [] # list to store transportation costs. Every record contains (time of order, cost of order)
        self.node_cost = 0 # total node cost (initial cost (establishment) + inventory cost + transportation cost)
        self.profit = 0 # profit per item
        self.revenue = 0 #
        self.net_profit = 0  # net profit (total profit - node cost)
        self.products_sold = 0 # products/raw materials sold by this node in the current cycle/period/day
        self.total_products_sold = 0 # total product units sold by this node
        self.total_profit = 0 # total profit (profit per item * total_products_sold)
        self.orders_placed = [] # list of orders placed to this node (demand). Each order is a tuple of (time of order, consumer ID, quantity ordered)
        self.orders_shortage = [] # list of order shortage. Each record is a tuple of (time of order, consumer ID, quantity ordered, quantity available)

        if(self.node_failure_p>0 or self.node_disrupt_time): # start self disruption if failure probability > 0
            self.env.process(self.disruption()) 
    
    def disruption(self):
        """
        This method disrupts the node by changing the node status to "inactive" and
        recovers it after the specified recovery time.

        Parameters:
            None

        Attributes:
            None

        Returns:
            None
        """
        while True:
            if(self.node_status=="active"):
                if(self.node_disrupt_time): # if node_disrupt_time is provided, wait for the disruption time
                    disrupt_time = self.node_disrupt_time() # get the disruption time
                    validate_number(name="node_disrupt_time", value=disrupt_time) # check if disrupt_time is a number
                    yield self.env.timeout(disrupt_time)
                    self.node_status = "inactive" # change the node status to inactive
                    self.logger.info(f"{self.env.now}:{self.ID}: Node disrupted.")
                elif(random.random() < self.node_failure_p):
                    self.node_status = "inactive"
                    self.logger.info(f"{self.env.now}:{self.ID}: Node disrupted.")
                    yield self.env.timeout(1)
            else:
                recovery_time = self.node_recovery_time() # get the recovery time
                validate_number(name="node_recovery_time", value=recovery_time) # check if disrupt_time is a number
                yield self.env.timeout(recovery_time)
                self.node_status = "active"
                self.logger.info(f"{self.env.now}:{self.ID}: Node recovered from disruption.")
            
class Link(NamedEntity, InfoMixin):
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
        link_disrupt_time (callable): function to model link disruption time
        link_recovery_time (callable): function to model link recovery time
    
    Attributes:
        _info_keys (list): list of keys to include in the info dictionary
        _stats_keys (list): list of keys to include in the statistics dictionary
    
    Functions:
        __init__: initializes the link object
        disruption: disrupt the link
    """
    _info_keys = ["ID", "source", "sink", "cost", "lead_time", "link_failure_p"]
    _stats_keys = ["status"]
    def __init__(self, env: simpy.Environment, 
                 ID: str, 
                 source: Node, 
                 sink: Node, 
                 cost: float, # transportation cost
                 lead_time: callable,
                 link_failure_p: float = 0.0,
                 link_disrupt_time: callable = None,
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
            env (simpy.Environment): simulation environment
            ID (str): ID of the link (alphanumeric)
            source (Node): source node of the link
            sink (Node): sink node of the link
            cost (float): cost of transportation over the link
            lead_time (callable): lead time of the link
            link_failure_p (float): link failure probability
            link_recovery_time (callable): function to model link recovery time
            link_disrupt_time (callable): function to model link disruption time, if provided

        Returns:
            None
        """
        if(lead_time == None):
            global_logger.logger.error("Lead time cannot be None. Provide a function to model stochastic lead time.")
            raise ValueError("Lead time cannot be None. Provide a function to model stochastic lead time.")
        if(source == sink):
            global_logger.logger.error("Source and sink nodes cannot be the same.")
            raise ValueError("Source and sink nodes cannot be the same.")
        if(source.node_type == "demand"):
            global_logger.logger.error("Demand node cannot be a source node.")
            raise ValueError("Demand node cannot be a source node.")
        if("supplier" in sink.node_type):
            global_logger.logger.error("Supplier node cannot be a sink node.")
            raise ValueError("Supplier node cannot be a sink node.")
        if("supplier" in source.node_type and "supplier" in sink.node_type):
            global_logger.logger.error("Supplier nodes cannot be connected.")
            raise ValueError("Supplier nodes cannot be connected.")
        if("supplier" in source.node_type and sink.node_type == "demand"):
            global_logger.logger.error("Supplier node cannot be connected to a demand node.")
            raise ValueError("Supplier node cannot be connected to a demand node.")
        validate_non_negative("Cost", cost)

        self.env = env  # simulation environment
        self.ID = ID  # ID of the link (alphanumeric)
        self.source = source  # source node of the link
        self.sink = sink  # sink node of the link
        self.cost = cost  # cost of the link
        self.lead_time = lead_time  # lead time of the link
        self.link_failure_p = link_failure_p  # link failure probability
        self.status = "active"  # link status (active/inactive)
        self.link_recovery_time = link_recovery_time  # link recovery time
        self.link_disrupt_time = link_disrupt_time  # link disruption time, if provided

        self.sink.suppliers.append(self)  # add the link as a supplier link to the sink node
        if(self.link_failure_p>0 or self.link_disrupt_time): # disrupt the link if link_failure_p > 0
            self.env.process(self.disruption())

        if("supplier" not in self.source.node_type): # if the source node is not a supplier, set the buy price of the sink node to the sell price of the source node
            self.sink.buy_price = self.source.sell_price
            self.sink.profit = self.sink.sell_price - self.sink.buy_price
            if(self.source.product):
                self.sink.buy_price = self.source.product.sell_price # set the buy price of the sink node to the buy price of the source node
                self.sink.profit = self.sink.sell_price - self.sink.buy_price
    
    def disruption(self):
        """
        This method disrupts the link by changing the link status to "inactive" and recovers it after the specified recovery time.

        Parameters:
            None

        Attributes:
            None

        Returns:
            None
        """
        while True:
            if(self.status=="active"):
                if(self.link_disrupt_time): # if link_disrupt_time is provided, wait for the disruption time
                    disrupt_time = self.link_disrupt_time() # get the disruption time
                    validate_number(name="link_disrupt_time", value=disrupt_time) # check if disrupt_time is a number
                    yield self.env.timeout(disrupt_time)
                    self.status = "inactive" # change the link status to inactive
                    self.logger.info(f"{self.env.now}:{self.ID}: Link disrupted.")
                elif(random.random() < self.link_failure_p):
                    self.status = "inactive"
                    self.logger.info(f"{self.env.now}:{self.ID}: Link disrupted.")
                    yield self.env.timeout(1)
            else:
                recovery_time = self.link_recovery_time() # get the recovery time
                validate_number(name="link_recovery_time", value=recovery_time) # check if disrupt_time is a number
                yield self.env.timeout(recovery_time)
                self.status = "active"
                self.logger.info(f"{self.env.now}:{self.ID}: Link recovered from disruption.")

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
    
    Attributes:    
        raw_material (RawMaterial): raw material supplied by the supplier
        inventory (Inventory): inventory of the supplier
        inventory_holding_cost (float): inventory holding cost
        total_raw_materials_mined (int): total raw materials mined/extracted
        total_material_cost (float): total cost of the raw materials mined/extracted
        total_raw_materials_sold (int): total raw materials sold

    Functions:
        __init__: initializes the supplier object
        behavior: supplier behavior
        calculate_statistics: calculate statistics for the supplier

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
        validate_non_negative("Inventory holding cost",inventory_holding_cost)
        super().__init__(node_type=node_type,**kwargs)
        self._info_keys.extend(["capacity", "initial_level", "inventory_holding_cost"])
        self._stats_keys.extend(["total_raw_materials_mined", "total_material_cost", "total_raw_materials_sold"])
        self.raw_material = raw_material # raw material supplied by the supplier, by default, it is default_raw_material.
        if(self.node_type!="infinite_supplier"):
            self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, replenishment_policy=ReplenishmentPolicy)
            if(self.raw_material):
                self.env.process(self.behavior()) # start the behavior process
            else:
                self.logger.error(f"{self.ID}:Raw material not provided for this supplier. Recreate it with a raw material.")
                raise ValueError("Raw material not provided.")
        else:
            self.inventory = Inventory(env=self.env, capacity=float('inf'), initial_level=float('inf'), replenishment_policy=ReplenishmentPolicy)
        self.inventory_holding_cost = inventory_holding_cost # inventory holding cost
        self.profit = self.raw_material.cost - self.raw_material.mining_cost

        # performance metrics (listed only for the supplier, rest common are created and initiated by __init__ of the base class)
        self.total_raw_materials_mined = 0 # total raw materials mined/extracted
        self.total_material_cost = 0 # total cost of the raw materials mined/extracted
        self.total_raw_materials_sold = 0 # total raw materials sold
        self.env.process(self.calculate_statistics()) # calculate statistics
        
    def behavior(self):
        """
        Supplier behavior: The supplier keeps extracting raw material whenever the inventory is not full.
        Assume that a supplier can extract a single type of raw material.

        Parameters:
            None

        Attributes:
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
                    self.total_raw_materials_mined += self.inventory.inventory.capacity - self.inventory.inventory.level # update statistics
                    self.inventory.inventory.put(self.inventory.inventory.capacity - self.inventory.inventory.level)
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Raw material mined/extracted. Inventory level:{self.inventory.inventory.level}")
            else:
                yield self.env.timeout(1)
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Inventory level:{self.inventory.inventory.level}") # log every day/period inventory level
    
    def calculate_statistics(self):
        """
        Calculate and record everyday node level statistics for the supplier.
        
        Parameters:
            None

        Attributes:
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

    Attributes:
        node_type (str): type of the inventory node (retailer or distributor)
        capacity (int): maximum capacity of the inventory
        initial_level (int): initial inventory level
        inventory_holding_cost (float): inventory holding cost
        suppliers (list): list of supplier links from which the inventory node can replenish inventory
        replenishment_policy (ReplenishmentPolicy): replenishment policy for the inventory
        policy_param (dict): parameters for the replenishment policy
        inventory (Inventory): inventory object
        product (Product): product that the inventory node sells
        manufacture_date (callable): function to model manufacturing date
        sell_price (float): selling price of the product
        buy_price (float): buying price of the product
        order_placed (bool): flag to check if the order is placed
        products_sold_daily (list): list to store the product sold in the current cycle
    
    Functions:
        __init__: initializes the inventory node object
        calculate_statistics: calculate statistics for the inventory node
        place_order: place an order
    """
    def __init__(self,
                 node_type: str, 
                 capacity: int, 
                 initial_level: int, 
                 inventory_holding_cost:float,
                 replenishment_policy:ReplenishmentPolicy, 
                 policy_param: dict,
                 inventory_type:str = "non-perishable", 
                 shelf_life:int = 0,
                 manufacture_date:callable = None,
                 product_sell_price: float = 0.0, 
                 product_buy_price: float = 0.0,
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
        
        Returns:
            None

        Behavior:
            The inventory node sells the product to the customers. It replenishes the inventory from the suppliers according to the replenishment policy. 
            The inventory node can have multiple suppliers. It chooses a supplier based on the availability of the product at the suppliers.
            The product buy price is set to the supplier's product sell price. The inventory node sells the product at a higher price than the buy price.
        """
        validate_non_negative("Inventory holding cost", inventory_holding_cost)
        super().__init__(node_type=node_type,**kwargs)
        self._info_keys.extend(["capacity", "initial_level", "inventory_holding_cost", "replenishment_policy", "product_sell_price", "product_buy_price"])
        self.capacity = capacity
        self.initial_level = initial_level
        self.inventory_holding_cost = inventory_holding_cost
        self.suppliers = []
        self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, inv_type=inventory_type, replenishment_policy=replenishment_policy, shelf_life=shelf_life)
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
        if(replenishment_policy):
            self.replenishment_policy = replenishment_policy(env = self.env, node = self, params = policy_param)
            self.env.process(self.replenishment_policy.run())
        # statistics
        self.products_sold_daily = [] # list to store the product sold in the current cycle
        self.products_sold = 0
        self.env.process(self.calculate_statistics()) # calculate statistics
    
    def calculate_statistics(self):
        """
        Calculate statistics for the inventory node.

        Parameters:
            None

        Attributes:
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

    def place_order(self, supplier, reorder_quantity):
        """
        Place an order for the product from the suppliers.

        Parameters:
            supplier (Link): The supplier link from which the order is placed.
            reorder_quantity (int): The quantity of the product to reorder.

        Attributes:
            None
        
        Returns:
            None
        """
        if(supplier.source.node_status == "active"):
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing inventory from supplier:{supplier.source.name}, order placed for {reorder_quantity} units.")
            if(supplier.source.inventory.inv_type=="perishable"):
                event, man_date_ls = supplier.source.inventory.inventory.get(reorder_quantity)
                yield event
            else:
                yield supplier.source.inventory.inventory.get(reorder_quantity) # get the product from the supplier inventory      
            supplier.source.orders_placed.append((self.env.now, self.ID, reorder_quantity)) # record the order placed
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.") # log the shipment
            lead_time = supplier.lead_time() # get the lead time from the supplier
            validate_number(name="lead_time", value=lead_time) # check if lead_time is a number
            yield self.env.timeout(lead_time) # lead time for the order

            if(self.inventory.inventory.level + reorder_quantity > self.inventory.inventory.capacity): # check if the inventory can accommodate the reordered quantity
                reorder_quantity = self.inventory.inventory.capacity - self.inventory.inventory.level # if not, set the reorder quantity to the remaining capacity
            
            if(reorder_quantity <= 0): # if the reorder quantity is less than or equal to 0, do not place the order
                self.order_placed = False
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Inventory replenished. reorder_quantity={reorder_quantity}, Inventory full, order discarded.")
                return
            
            if(supplier.source.node_type not in ["supplier","infinite_supplier"]): # if the supplier is not a supplier or infinite supplier
                self.buy_price = supplier.source.sell_price # set the sell price of the product to the supplier sell price
                if(self.product): # product buy price may depend on the supplier, if a product is available then update the self buy_price = supplier sell_price
                    self.product.buy_price = supplier.source.sell_price # update the product cost 
            self.profit = self.sell_price - self.buy_price # calculate profit
            self.transportation_cost.append((self.env.now,supplier.cost)) # calculate stats: record order cost (tranportation cost))
            supplier.source.products_sold = reorder_quantity # calculate stats: update the product sold at the supplier
            supplier.source.total_products_sold += reorder_quantity # calculate stats: update the total product sold at the supplier

            if(supplier.source.inventory.inv_type=="perishable" and self.inventory.inv_type=="perishable"): # if supplier also has perishable inventory
                for ele in man_date_ls: # get manufacturing date from the supplier
                    self.inventory.inventory.put(ele[1],ele[0])
            elif(supplier.source.inventory.inv_type=="perishable"): # if supplier has perishable inventory but self inventory is non-perishable
                for ele in man_date_ls: # ignore the manufacturing date
                    self.inventory.inventory.put(ele[1])
            elif(self.inventory.inv_type=="perishable"): # if self inventory is perishable but supplier has non-perishable inventory
                if(self.manufacture_date): # calculate the manufacturing date using the function if provided
                    self.inventory.inventory.put(reorder_quantity,self.manufacture_date(self.env.now))
                else: # else put the product in the inventory with current time as manufacturing date
                    self.inventory.inventory.put(reorder_quantity,self.env.now)
            else:
                self.inventory.inventory.put(reorder_quantity)

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Inventory replenished. reorder_quantity={reorder_quantity}, Inventory levels:{self.inventory.inventory.level}")
            self.inventory.inventory_spend.append([self.env.now, reorder_quantity*self.buy_price]) # update stats: calculate and update inventory replenishment cost
        else:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Supplier:{supplier.source.name} is disrupted. Order not placed.")
        self.order_placed = False

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
        order_placed_raw (dict): dictionary to store order status for raw materials
        order_placed (bool): order status for the product
        inventory (Inventory): inventory of the manufacturer
        profit (float): profit per unit sold
        total_products_manufactured (int): total products manufactured
        total_manufacturing_cost (float): total cost of the products manufactured
        revenue (float): revenue from the products sold
        isolated_logger (bool): flag to enable/disable isolated logger
    
    Functions:
        __init__: initializes the manufacturer object
        behavior: manufacturer behavior - consume raw materials, produce the product, and put the product in the inventory
        calculate_statistics: calculate statistics for the manufacturer
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
                 replenishment_policy: ReplenishmentPolicy, 
                 policy_param: dict, 
                 product: Product = default_product, 
                 inventory_type: str = "non-perishable",
                 shelf_life: int = 0,
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
            order_placed_raw (dict): dictionary to store order status for raw materials
            order_placed (bool): order status for the product
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
        self._info_keys.extend(["capacity", "initial_level", "inventory_holding_cost", "replenishment_policy", "product_sell_price"])
        self._stats_keys.extend(["total_products_manufactured", "total_manufacturing_cost", "revenue"]) 
        self.capacity = capacity
        self.initial_level = initial_level
        self.inventory_holding_cost = inventory_holding_cost
        self.product = product # product manufactured by the manufacturer
        self.suppliers = []
        self.product.sell_price = product_sell_price
        self.sell_price = product_sell_price # set the sell price of the product
        
        self.production_cycle = False # production cycle status
        self.raw_inventory_counts = {} # dictionary to store inventory counts for raw products inventory
        self.order_placed_raw = {} # dictionary to store order status
        self.order_placed = False # order status for the product
        self.inventory = Inventory(env=self.env, capacity=self.capacity, initial_level=self.initial_level, inv_type=inventory_type, replenishment_policy=replenishment_policy, shelf_life=shelf_life)
        
        if(replenishment_policy):
            self.replenishment_policy = replenishment_policy(env = self.env, node = self, params = policy_param)
            self.env.process(self.replenishment_policy.run())

        self.product.buy_price = self.product.manufacturing_cost # calculate the total cost of the product, and set the sell price
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
    
    def calculate_statistics(self):
        """
        Calculate statistics for the manufacturer.

        Parameters:
            None

        Attributes:
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

    def manufacture_product(self):
        """
        Manufacture the product.
        This method handles the production of the product, consuming raw materials and adding the manufactured product to the inventory.

        Parameters:
            None

        Attributes:
            None

        Returns:
            None
        """
        max_producible_units = self.product.units_per_cycle
        for raw_material in self.product.raw_materials:
            raw_mat_id = raw_material["raw_material"].ID
            required_amount = raw_material["quantity"]
            current_raw_material_level = self.raw_inventory_counts[raw_mat_id]
            max_producible_units = min(max_producible_units,int(current_raw_material_level/required_amount))
        if((self.inventory.inventory.level + max_producible_units)>self.inventory.inventory.capacity): # check if the inventory can accommodate the maximum producible units
            max_producible_units = self.inventory.inventory.capacity - self.inventory.inventory.level
        if(max_producible_units>0):
            self.production_cycle = True # produce the product
            for raw_material in self.product.raw_materials: # consume raw materials
                raw_mat_id = raw_material["raw_material"].ID
                required_amount = raw_material["quantity"]
                self.raw_inventory_counts[raw_mat_id] -= raw_material["quantity"]*max_producible_units
            yield self.env.timeout(self.product.manufacturing_time) # take manufacturing time to produce the product            
            if(self.inventory.inv_type == "perishable"):
                self.inventory.inventory.put(max_producible_units, manufacturing_date=self.env.now)
            else:
                self.inventory.inventory.put(max_producible_units)
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: {max_producible_units} units manufactured.")
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Product inventory levels:{self.inventory.inventory.level}")
            self.total_products_manufactured += max_producible_units # update statistics
            self.production_cycle = False

    def behavior(self):
        """
        The manufacturer consumes raw materials and produces the product if raw materials are available.
        It maintains inventory levels for both raw materials and the product. Depending on the replenishment policy for product inventory,
        manufacturer decides when to replenish the raw material inventory. The manufacturer can be connected to multiple suppliers.

        Parameters:
            None

        Attributes: 
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
                self.order_placed_raw[supplier.source.raw_material.ID] = False # store order status
                
        if(len(self.suppliers)<len(self.product.raw_materials)):
            global_logger.logger.warning(f"{self.ID}: {self.name}: The number of suppliers are less than the number of raw materials required to manufacture the product! This leads to no products being manufactured.")

        # behavior of the manufacturer: consume raw materials, produce the product, and put the product in the inventory
        yield self.env.timeout(0.99999)
        while True:
            if(len(self.suppliers)>=len(self.product.raw_materials)): # check if required number of suppliers are connected
                if(not self.production_cycle):
                    self.env.process(self.manufacture_product()) # produce the product
            yield self.env.timeout(1)

    def place_order_raw(self, raw_mat_id, supplier, reorder_quantity):
        """
        Place an order for raw materials from the suppliers.
        
        Parameters:
            supplier (Link): The supplier link from which the order is placed.
            reorder_quantity (int): The quantity of the raw material to reorder.
        
        Attributes:
            None

        Returns:    
            None
        """
        if(supplier.source.node_status == "active" and supplier.source.inventory.inventory.level >= reorder_quantity): # check if the supplier is active and has enough inventory
            if(self.raw_inventory_counts[raw_mat_id]>= reorder_quantity): # check if the raw material inventory is sufficient
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Sufficient raw material inventory for {supplier.source.raw_material.name}, no order placed. Current inventory level: {self.raw_inventory_counts}.")
                self.order_placed_raw[raw_mat_id] = False
                self.order_placed = False # set the order status to False
                return

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing raw material:{supplier.source.raw_material.name} from supplier:{supplier.source.ID}, order placed for {reorder_quantity} units. Current inventory level: {self.raw_inventory_counts}.")
            yield supplier.source.inventory.inventory.get(reorder_quantity)
            supplier.source.orders_placed.append((self.env.now, self.ID, reorder_quantity)) # record the order placed
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.")                
            lead_time = supplier.lead_time() # get the lead time from the supplier
            validate_number(name="lead_time", value=lead_time) # check if lead_time is a number
            yield self.env.timeout(lead_time) # lead time for the order
            
            self.transportation_cost.append((self.env.now,supplier.cost)) # update the transportation cost at the supplier
            supplier.source.total_raw_materials_sold += reorder_quantity # update the product sold at the raw material supplier
            supplier.source.total_products_sold += reorder_quantity
            self.order_placed_raw[raw_mat_id] = False
            self.raw_inventory_counts[raw_mat_id] += reorder_quantity                    
            self.inventory.inventory_spend.append([self.env.now, reorder_quantity*supplier.source.raw_material.cost]) # update stats: calculate and update inventory replenishment cost
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Order received from supplier:{supplier.source.name}, inventory levels: {self.raw_inventory_counts}")
            self.order_placed = False # set the order status to False
        elif(supplier.source.node_status != "active"):
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Supplier:{supplier.source.name} is disrupted.")    
        else:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Insufficient inventory at supplier:{supplier.source.name}, order not placed.")
        self.order_placed_raw[raw_mat_id] = False
    
    def place_order(self, supplier, reorder_quantity):
        """
        Place an order for raw materials from the suppliers.
        
        Parameters:
            supplier (Link): Supplier link
            reorder_quantity (int): The quantity of the raw material to reorder.
        
        Attributes:
            None

        Returns:    
            None
        """
        self.order_placed = True # set the order status to True
        for raw_mat in self.product.raw_materials: # place order for all raw materials required to produce the product
            raw_mat_id = raw_mat["raw_material"].ID
            raw_mat_reorder_sz = raw_mat["quantity"]*reorder_quantity
            for supplier in self.suppliers:
                if(supplier.source.raw_material.ID == raw_mat_id and self.order_placed_raw[raw_mat_id] == False): # check if the supplier has the raw material and order is not already placed
                    self.order_placed_raw[raw_mat_id] = True # set the order status to True
                    self.env.process(self.place_order_raw(raw_mat_id, supplier, raw_mat_reorder_sz)) # place the order for the raw material
        yield self.env.timeout(0.1) # wait for the order to be placed

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
    
    Functions:
        __init__: initializes the demand node object
        customer: simulates the customer behavior, ordering products from demand node, consume and return
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

        Parameters:
            order_arrival_model (callable): function that models order arrivals
            order_quantity_model (callable): function that models order quantity
            demand_node (Node): node at which the demand is generated
            tolerance (float): customer tolerance for waiting for the order when required quantity is not available
            delivery_cost (callable): function that models the cost of delivery
            lead_time (callable): function that models the lead time for delivery

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
        if("supplier" in demand_node.node_type):
            global_logger.logger.error("Demand node cannot be a supplier.")
            raise ValueError("Demand node cannot be a supplier.")
            
        super().__init__(node_type="demand",**kwargs)
        self._info_keys.extend(["order_arrival_model", "order_quantity_model", "demand_node", "customer_tolerance", "delivery_cost", "lead_time"])
        self._stats_keys.extend(["total_demand","unsatisfied_demand", "shortage"])
        self.order_arrival_model = order_arrival_model
        self.order_quantity_model = order_quantity_model
        self.demand_node = demand_node
        self.customer_tolerance = tolerance
        self.delivery_cost = delivery_cost
        self.lead_time = lead_time
        self.env.process(self.behavior())

        self.total_demand = 0
        self.products_sold_daily = [] # list to store the product sold everyday
        self.unsatisfied_demand = [] # list to store the unsatisfied demand
        self.shortage = []

    def wait_for_order(self,id,order_quantity):
        """
        Wait for the required number of units based on customer tolerance.
        If the customer tolerance is infinite, the method waits until the order is fulfilled.
        Otherwise, it waits for the specified tolerance time and updates the unsatisfied demand if the order is not fulfilled.
        
        Parameters:
            order_quantity (int): The quantity of the product ordered.

        Attributes:
            id (int): Customer ID for logging purposes.
            order_quantity (int): The quantity of the product ordered.
        
        Returns:
            None
        """
        if(self.customer_tolerance==float('inf')): # wait for the order to arrive
            if(self.demand_node.inventory.inv_type=="perishable"):
                get_event, man_date_ls = self.demand_node.inventory.inventory.get(order_quantity)
                yield get_event
            else:
                yield self.demand_node.inventory.inventory.get(order_quantity)
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, remaining order quantity:{order_quantity} placed.")
            lead_time = self.lead_time() # get the lead time from the demand node
            validate_number(name="lead_time", value=lead_time) # check if lead_time is a number
            yield self.env.timeout(lead_time) # wait for the delivery of the order
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} received. Current inv: {self.demand_node.inventory.inventory.level}")

            # update statistics
            self.products_sold_daily.append((self.env.now, order_quantity))
            self.total_products_sold += order_quantity
            del_cost = self.delivery_cost() # calculate the delivery cost
            validate_number(name="delivery_cost", value=del_cost) # check if delivery_cost is a number
            self.transportation_cost.append([self.env.now, del_cost])
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
                if(self.demand_node.inventory.inv_type=="perishable"):
                    event,  man_dt_ls = self.demand_node.inventory.inventory.get(order_quantity)
                    yield event 
                else:
                    yield self.demand_node.inventory.inventory.get(order_quantity)
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, remaining order quantity:{order_quantity}, available inventory:{self.demand_node.inventory.inventory.level}.")
                lead_time = self.lead_time() # get the lead time from the demand node
                validate_number(name="lead_time", value=lead_time) # check if lead_time is a number
                yield self.env.timeout(lead_time) # wait for the delivery of the order
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} received. Current inv: {self.demand_node.inventory.inventory.level}")
                # update statistics
                self.products_sold_daily.append((self.env.now, order_quantity))
                self.total_products_sold += order_quantity
                del_cost = self.delivery_cost()
                validate_number(name="delivery_cost", value=del_cost)
                self.transportation_cost.append([self.env.now, del_cost])
                self.node_cost += self.transportation_cost[-1][1]
                self.demand_node.products_sold = order_quantity
                return                
        self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, remaining order quantity:{order_quantity} not available! inventory:{self.demand_node.inventory.inventory.level}. No order placed.")
        self.unsatisfied_demand.append((self.env.now, order_quantity))

    def customer(self,id,order_quantity):
        """
        Simulate the customer behavior, ordering products from demand node, consume and return.

        Parameters:
            id (int): Customer ID for logging purposes.
            order_quantity (int): The quantity of the product ordered.

        Attributes:
            id (int): Customer ID for logging purposes.
            order_quantity (int): The quantity of the product ordered.

        Returns:
            None
        """
        if(order_quantity <= self.demand_node.inventory.inventory.level):
            if(self.demand_node.inventory.inv_type=="perishable"):
                get_eve, man_date_ls = self.demand_node.inventory.inventory.get(order_quantity)
                yield get_eve
            else:
                yield self.demand_node.inventory.inventory.get(order_quantity)
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity}, available.")
            lead_time = self.lead_time() # get the lead time from the demand node
            validate_number(name="lead_time", value=lead_time) # check if lead_time is a number
            yield self.env.timeout(lead_time) # wait for the delivery of the order
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} received. Current inv: {self.demand_node.inventory.inventory.level}")
            # update statistics
            self.products_sold_daily.append((self.env.now, order_quantity))
            self.total_products_sold += order_quantity
            del_cost = self.delivery_cost()
            validate_number(name="delivery_cost", value=del_cost) # check if delivery_cost is a number
            self.transportation_cost.append([self.env.now, del_cost])
            self.node_cost += self.transportation_cost[-1][1]
            self.demand_node.products_sold = order_quantity
        elif(self.customer_tolerance>0):
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{order_quantity} not available, inventory level:{self.demand_node.inventory.inventory.level}. Place order for available amount.")  
            order_quantity = order_quantity - self.demand_node.inventory.inventory.level # calculate the remaining quantity to order
            if(self.demand_node.inventory.inventory.level>0): # consume if available
                consumed_quantity = self.demand_node.inventory.inventory.level
                if(self.demand_node.inventory.inv_type=="perishable"):
                    get_eve, man_date_ls = self.demand_node.inventory.inventory.get(self.demand_node.inventory.inventory.level)
                    yield get_eve
                else:
                    yield self.demand_node.inventory.inventory.get(self.demand_node.inventory.inventory.level) # consume available quantity
                lead_time = self.lead_time() # get the lead time from the demand node
                validate_number(name="lead_time", value=lead_time) # check if lead_time is a number
                yield self.env.timeout(lead_time) # wait for the delivery of the order
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{id}:Demand at {self.demand_node}, Order quantity:{consumed_quantity} received. Current inv: {self.demand_node.inventory.inventory.level}")
                # set stats for the demand node
                self.demand_node.products_sold = consumed_quantity
                self.products_sold_daily.append((self.env.now, consumed_quantity))
                self.total_products_sold += consumed_quantity
                del_cost = self.delivery_cost()
                validate_number(name="delivery_cost", value=del_cost)
                self.transportation_cost.append([self.env.now, del_cost])
                self.node_cost += self.transportation_cost[-1][1]
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

        Parameters:
            None
        
        Attributes:
            None
        
        Returns:
            None
        """
        customer_id = 0 # customer ID
        while True:
            order_time = self.order_arrival_model()
            validate_number(name="order_time", value=order_time)
            order_quantity = self.order_quantity_model()
            validate_number(name="order_quantity", value=order_quantity)
            self.total_demand += order_quantity
            self.env.process(self.customer(customer_id, order_quantity)) # spawn a customer process
            customer_id += 1 # increment customer ID
            yield self.env.timeout(order_time) # wait for the next order arrival