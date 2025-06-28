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
        raise ValueError(f"function {name}() must be a number (an int or a float).")
        

class NamedEntity:
    """
    The `NamedEntity` class provides a standardized way to display meaningful names for objects in the supply chain model. When printed or displayed, the object will show its `name` (if defined), otherwise its `ID`, or the class name as a fallback. This improves the readability and interpretability of simulation outputs by ensuring objects are easily identifiable.
    
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
        return getattr(self, 'name', getattr(self, 'ID', self.__class__.__name__))

    def __repr__(self):
        """Returns the name of the object if available, otherwise returns the class name."""
        return getattr(self, 'name', getattr(self, 'ID', self.__class__.__name__))


class InfoMixin:
    """
    The `InfoMixin` class allows objects to easily provide their key details and statistics as dictionaries. This helps in quickly summarizing, logging, or analyzing object data in a structured and consistent way across the simulation.

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

class Statistics(InfoMixin):
    """
    The `Statistics` class tracks and summarizes key performance indicators for each node in the supply chain. It monitors essential metrics such as demand, inventory levels, shortages, backorders, costs, revenue, and profit. The class supports both automatic periodic updates and manual updates through the `update_stats` method, which can be called at any point in the simulation to immediately record changes. By maintaining detailed, node-specific statistics, this class provides valuable insights into supply chain efficiency, product flow, and financial outcomes in real time.

    Parameters:
        node (object): The node for which statistics are tracked.
        periodic_update (bool, optional): Whether to update statistics periodically. Default is False.
        period (float, optional): Time interval for periodic updates. Default is 1.

    Attributes:
        node (object): The node to which this statistics object belongs.
        name (str): Name of the statistics object.
        demand_placed (list): Orders and quantities placed by this node.
        fulfillment_received (list): Orders and quantities received by this node.
        demand_received (list): Orders and quantities demanded at this node.
        demand_fulfilled (list): Orders and quantities fulfilled by this node.
        orders_shortage (list): Orders and quantities that faced shortage.
        backorder (list): Backorders at this node.
        inventory_level (float): Current inventory level.
        inventory_waste (float): Inventory waste.
        inventory_carry_cost (float): Inventory carrying cost.
        inventory_spend_cost (float): Inventory replenishment cost.
        transportation_cost (float): Transportation cost.
        node_cost (float): Total cost at this node.
        revenue (float): Revenue generated by this node.
        profit (float): Profit generated by this node.
        _info_keys (list): Keys to include in the info dictionary.
        _stats_keys (list): Keys to include in the statistics dictionary.

    Functions:
        __init__: Initializes the statistics object.
        reset: Resets all statistics to initial values.
        update_stats: Updates statistics based on provided values.
        update_stats_periodically: Periodically updates statistics during simulation.
    """



    def __init__(self, node:object, periodic_update:bool=False, period:float=1):
        """
        Initialize the statistics object.
        Parameters:
            node (object): The node for which statistics are tracked.
            periodic_update (bool, optional): Whether to update statistics periodically. Default is False.
            period (float, optional): Time interval for periodic updates. Default is 1.

        Returns:
            None
        """

        self._info_keys = ["name"]
        self._stats_keys = ["demand_placed", "fulfillment_received", "demand_received", "demand_fulfilled", "orders_shortage", "backorder", "inventory_level", "inventory_waste", "inventory_carry_cost", "inventory_spend_cost", "transportation_cost", "node_cost", "revenue", "profit"]
        self.node = node # the node to which this statistics object belongs
        self.name = f"{self.node.ID} statistics"
        self.demand_placed = [0,0] # demand placed by this node [total orders placed, total quantity]
        self.fulfillment_received = [0,0] # fulfillment received by this node
        self.demand_received = [0,0] # demand received by this node (demand at this node)
        self.demand_fulfilled = [0,0] # demand fulfilled by this node (demand that was served by this node)
        self.orders_shortage = [0,0] # shortage of products at this node 
        self.backorder = [0,0] # any backorders at this node
        self.inventory_level = 0 # current inventory level at this node
        self.inventory_waste = 0 # inventory waste at this node
        self.inventory_carry_cost = 0 # inventory carrying cost at this node
        self.inventory_spend_cost = 0 # inventory replenishment cost at this node
        self.transportation_cost = 0 # transportation cost at this node
        self.node_cost = 0 # total cost at this node
        self.revenue = 0 # revenue generated by this node
        self.profit = 0 # profit generated by this node (revenue - total cost)

        if(periodic_update):
            self.node.env.process(self.update_stats_periodically(period=period))
    
    def reset(self):
        """ 
        Reset the statistics to their initial values.

        Parameters:
            None

        Attributes:
            None

        Returns:
            None
        """
        for key, value in vars(self).items():
            if isinstance(value, list):
                if "_keys" in key:
                    continue
                setattr(self, key, [0,0])
            elif isinstance(value, (int, float)):
                setattr(self, key, 0)

    def update_stats(self,**kwargs):
        """
        Update the statistics with the given keyword arguments.

        Parameters:
            **kwargs: keyword arguments containing the statistics to update

        Attributes:
            None

        Returns:
            None
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                attr = getattr(self, key)
                if isinstance(attr, list): # value = [v1,v2]
                    attr[0] += value[0]
                    attr[1] += value[1]
                    setattr(self, key, attr) # update the attribute with the new value
                else:
                    attr += value
                    setattr(self, key, attr) # update the attribute with the new value
            else:
                global_logger.logger.warning(f"{self.node.ID}: (Updaing stats) Attribute {key} not found in Statistics class.")
        if hasattr(self.node, 'inventory'):
            if self.node.inventory.inventory.capacity != float('inf'):
                self.inventory_level = self.node.inventory.inventory.level if hasattr(self.node, 'inventory') else 0
                self.node.inventory.update_carry_cost()
                self.inventory_carry_cost = self.node.inventory.carry_cost
                self.inventory_waste = self.node.inventory.waste if hasattr(self.node.inventory, 'waste') else 0
        total_cost = 0
        for key,value in vars(self).items():
            if key == "node_cost": # exclude node_cost from the total cost calculation
                continue
            if "cost" in key: # consider all cost attributes
                total_cost += value
        self.node_cost = total_cost
        self.revenue = self.demand_received[1] * self.node.sell_price if hasattr(self.node, 'sell_price') else 0
        self.profit = self.revenue - self.node_cost

    def update_stats_periodically(self, period):
        """
        Update the statistics periodically.
        
        Parameters:
            period (float): period for periodic update of statistics

        Attributes:
            None

        Returns:
            generator: a generator that yields after the specified period
        """
        while True:
            yield self.node.env.timeout(period)
            self.update_stats()

class RawMaterial(NamedEntity, InfoMixin):
    """
    The `RawMaterial` class represents the basic input resources in a supply chain model. It defines key properties of a raw material, including extraction rate, extraction time, mining cost, and selling price. This class helps model the sourcing and extraction processes in the network, providing the foundation for simulating how raw materials flow through the supply chain.

    Parameters:
        ID (str): ID of the raw material.
        name (str): Name of the raw material.
        extraction_quantity (float): Quantity extracted per extraction cycle.
        extraction_time (float): Time required to extract the specified quantity.
        mining_cost (float): Mining cost per item.
        cost (float): Selling price per item.

    Attributes:
        _info_keys (list): Keys to include in the info dictionary.
        _stats_keys (list): Keys to include in the statistics dictionary.
        ID (str): ID of the raw material.
        name (str): Name of the raw material.
        extraction_quantity (float): Quantity extracted per extraction cycle.
        extraction_time (float): Time required for extraction.
        mining_cost (float): Mining cost per item.
        cost (float): Selling price per item.

    Functions:
        __init__: Initializes the raw material object.
    """


    def __init__(self, 
                 ID: str, 
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
            extraction_quantity (float): quantity of the raw material that is extracted in extraction_time
            extraction_time (float): time to extract 'extraction_quantity' units of raw material
            mining_cost (float): mining cost of the raw material (per item)
            cost (float): selling cost of the raw material (per item)

        Attributes:
            _info_keys (list): list of keys to include in the info dictionary
            _stats_keys (list): list of keys to include in the statistics dictionary
            ID (str): ID of the raw material (alphanumeric)
            name (str): name of the raw material
            extraction_quantity (float): quantity of the raw material that is extracted in extraction_time
            extraction_time (float): time to extract 'extraction_quantity' units of raw material
            mining_cost (float): mining cost of the raw material (per item)
            cost (float): selling cost of the raw material (per item)

        Returns:
            None
        """
        validate_positive("Extraction quantity", extraction_quantity)
        validate_non_negative("Extraction time", extraction_time)
        validate_positive("Cost", cost)
        self._info_keys = ["ID", "name", "extraction_quantity", "extraction_time", "mining_cost", "cost"]
        self._stats_keys = []        
        self.ID = ID # ID of the raw material (alphanumeric)
        self.name = name # name of the raw material
        self.extraction_quantity = extraction_quantity # quantity of the raw material that is extracted in extraction_time
        self.extraction_time = extraction_time # time to extract 'extraction_quantity' units of raw material
        self.mining_cost = mining_cost # mining cost of the raw material (per item)
        self.cost = cost # selling cost of the raw material (per item)

class Product(NamedEntity, InfoMixin):
    """
    
    The `Product` class models a finished good in the supply chain. It defines essential properties such as manufacturing cost, manufacturing time, selling price, and the raw materials required to produce it. The class supports both buying and manufacturing workflows, allowing nodes to either purchase the product directly or produce it using defined raw material combinations. Products are typically manufactured in batches, with each batch size and cycle time configurable, making it easy to model real-world production processes.

    Parameters:
        ID (str): ID of the product.
        name (str): Name of the product.
        manufacturing_cost (float): Manufacturing cost per unit.
        manufacturing_time (int): Time to manufacture one batch.
        sell_price (float): Selling price per unit.
        raw_materials (list): List of (raw material object, quantity) tuples required for one unit.
        batch_size (int): Number of units manufactured per cycle.
        buy_price (float, optional): Buying price per unit (default is 0).

    Attributes:
        _info_keys (list): Keys to include in the info dictionary.
        _stats_keys (list): Keys to include in the statistics dictionary.
        ID (str): ID of the product.
        name (str): Name of the product.
        manufacturing_cost (float): Manufacturing cost per unit.
        manufacturing_time (int): Manufacturing time for one batch.
        sell_price (float): Selling price per unit.
        buy_price (float): Buying price per unit.
        raw_materials (list): List of (raw material, quantity) tuples required for one unit.
        batch_size (int): Units manufactured per cycle.

    Functions:
        __init__: Initializes the product object.
    """


    def __init__(self, 
                 ID: str, 
                 name: str, 
                 manufacturing_cost: float, 
                 manufacturing_time: int, 
                 sell_price: float, 
                 raw_materials: list, 
                 batch_size: int, 
                 buy_price: float = 0) -> None:
        """
        Initialize the product object.

        Performs input validation for positive and non-negative values, and ensures raw materials are provided.

        Parameters:
            ID (str): ID of the product (alphanumeric)
            name (str): Name of the product
            manufacturing_cost (float): Manufacturing cost of the product per unit
            manufacturing_time (int): Time to manufacture one batch of products
            sell_price (float): Price at which the product is sold
            buy_price (float, optional): Price at which the product is bought (default is 0)
            raw_materials (list): List of tuples containing (raw material object, quantity required) to manufacture one unit of the product
            batch_size (int): Number of units manufactured per manufacturing cycle

        Attributes:
            _info_keys (list): List of keys to include in the info dictionary
            _stats_keys (list): List of keys to include in the statistics dictionary
            ID (str): ID of the product
            name (str): Name of the product
            manufacturing_cost (float): Manufacturing cost per unit
            manufacturing_time (int): Time to manufacture one batch
            sell_price (float): Selling price of the product
            buy_price (float): Buying price of the product (default is 0)
            raw_materials (list): List of (raw material, quantity) required for one unit
            batch_size (int): Number of units produced per manufacturing cycle

        Returns:
            None

        Raises:
            ValueError: If validations fail for positive values, non-negative values, or empty raw materials list.
        """

        validate_positive("Manufacturing cost", manufacturing_cost)
        validate_non_negative("Manufacturing time", manufacturing_time)
        validate_positive("Sell price", sell_price)
        validate_non_negative("Buy price", buy_price)
        validate_positive("Units per cycle", batch_size)
        if raw_materials is None or len(raw_materials) == 0:
            global_logger.logger.error("Raw materials cannot be empty.")
            raise ValueError("Raw materials cannot be empty.")
        self._info_keys = ["ID", "name", "manufacturing_cost", "manufacturing_time", "sell_price", "buy_price", "raw_materials", "batch_size"]
        self._stats_keys = []
        self.ID = ID # ID of the product (alphanumeric)
        self.name = name # name of the product
        self.manufacturing_cost = manufacturing_cost # manufacturing cost of the product (per unit)
        self.manufacturing_time = manufacturing_time # time (days) to manufacture 'batch_size' units of product
        self.sell_price = sell_price # price at which the product is sold
        self.buy_price = buy_price # price at which the product is bought, (default: 0). It is used by InventoryNode buy the product at some price and sell it at a higher price.   
        self.raw_materials = raw_materials # list of raw materials and quantity required to manufacture a single product unit
        self.batch_size = batch_size # number of units manufactured per cycle


class InventoryReplenishment(InfoMixin):
    """
    
    The `InventoryReplenishment` class defines the abstract structure for inventory replenishment policies within SupplyNetPy. It provides a common interface for managing how nodes place replenishment orders during the simulation.

    This class is not intended for direct use. It must be subclassed to implement specific replenishment strategies, such as (s, S), reorder point–quantity (RQ), or periodic review policies.

    The `run` method should be overridden to define the replenishment logic for the policy. The class integrates with the SimPy environment to support time-driven inventory management. The `inventory_drop` event is used to signal stock depletion, enabling the replenishment process to respond to changes in inventory levels in real time.

    Parameters:
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Parameters for the replenishment policy.

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Parameters for the replenishment policy.

    Functions:
        __init__: Initializes the base replenishment policy object.
        run: Placeholder method to be overridden by subclasses.
    """



    def __init__(self, 
                 env: simpy.Environment, 
                 node: object, 
                 params: dict) -> None:
        """
        Initialize the replenishment policy object.
        
        Parameters:
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy

        Attributes:
            _info_keys (list): list of keys to include in the info dictionary
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy
            
        Returns:
            None
        """
        self._info_keys = ["node", "params"]
        self.env = env  # simulation environment
        self.node = node  # node to which this policy applies
        self.params = params  # parameters for the replenishment policy

    def run(self):
        """
        This method should be overridden by subclasses to implement the specific replenishment policy logic.
        """
        pass


class SSReplenishment(InventoryReplenishment, NamedEntity):
    """
    Implements the (s, S) min-max inventory replenishment policy with optional safety stock support.

    When the inventory level falls to or below the reorder point (s), an order is placed to replenish stock up to the order-up-to level (S). If safety stock is provided, both the reorder point and the order-up-to level are adjusted accordingly. The policy supports both event-driven and periodic inventory checks, with an optional initial review delay. Supplier selection is automatically managed using the node’s supplier selection policy.

    Parameters:
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Replenishment policy parameters (s, S) and optional parameters (safety_stock, first_review_delay, period).

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Replenishment policy parameters.
        name (str): Replenishment policy name.
        first_review_delay (float): Delay before the first inventory check begins.
        period (float): Time interval for periodic inventory checks.

    Functions:
        __init__: Initializes the replenishment policy object.
        run: Monitors inventory and places orders based on the (s, S) policy.
    """


    def __init__(self, env, node, params):
        """ 
        Initialize the replenishment policy object.

        Parameters:
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy (s, S)

        Attributes:
            _info_keys (list): list of keys to include in the info dictionary
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy (s, S)
            name (str): replenishment policy name
            first_review_delay (float): delay before the first inventory check is performed
            period (float): period for periodic inventory check

        Returns:
            None
        """
        validate_non_negative("Reorder point (s)", params['s']) # this assertion ensures that the reorder point is positive
        validate_positive("Order-up-to level (S)", params['S']) # this assertion ensures that the order-up-to level is non-negative
        super().__init__(env, node, params)
        self._info_keys.extend(["name","first_review_delay","period"])
        self.name = "min-max replenishment (s, S)"
        self.first_review_delay = params.get('first_review_delay', 0)
        self.period = params.get('period',0)
    
    def run(self):
        """
        Replenishes the inventory based on the sS policy.

        Parameters:
            None

        Attributes: 
            s (float): reorder point
            S (float): order-up-to level

        Returns:
            None    
        """
        s, S = self.params['s'], self.params['S']  # get the reorder point and order-up-to level
        if s > S:
            self.node.logger.logger.error("Reorder point (s) must be less than or equal to order-up-to level (S).")
            raise ValueError("Reorder point (s) must be less than or equal to order-up-to level (S).")

        if 'safety_stock' in self.params: # check if safety_stock is specified
            validate_positive("Safety stock", self.params['safety_stock'])
            self.name = "min-max with safety replenishment (s, S, safety_stock)"
            s += self.params['safety_stock']
            S += self.params['safety_stock']

        if(self.first_review_delay>0): # if first review delay is specified, wait for the specified time before starting the replenishment process
            yield self.env.timeout(self.first_review_delay)

        while True: # run the replenishment process indefinitely
            self.node.logger.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.inventory.level}")
            if (self.node.inventory.inventory.level <= s) and (not self.node.ongoing_order):
                order_quantity = S - self.node.inventory.inventory.level  # calculate the order quantity                
                supplier = self.node.selection_policy.select(order_quantity) # select a supplier based on the supplier selection policy
                self.node.ongoing_order = True
                self.env.process(self.node.process_order(supplier, order_quantity))                    
            
            if self.period==0: # if periodic check is OFF
                yield self.node.inventory_drop  # wait for the inventory to be dropped
                self.node.inventory_drop = self.env.event()  # reset the event for the next iteration
            elif(self.period): # if periodic check is ON
                yield self.env.timeout(self.period)

class RQReplenishment(InventoryReplenishment):
    """
    Implements a Reorder Quantity (RQ) Inventory Replenishment Policy.

    This policy continuously monitors inventory levels and places a replenishment order when the inventory 
    falls to or below the reorder point (R). The replenishment quantity is fixed at Q units per order.

    The inventory can be checked continuously (event-based) if 'period' is set to 0 (default) and periodically if a positive 'period' is provided.
    An optional first review delay can be configured to introduce a delay before the first inventory check begins.

    Supplier selection is managed automatically using the node's supplier selection policy. If the selected 
    supplier does not have sufficient inventory, the shortage is recorded.

    Parameters:
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Parameters for the replenishment policy: R, Q, and optional parameters(fist_review_delay, period).

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Replenishment policy parameters (R, Q, optional delays and period).
        name (str): Replenishment policy name.
        first_review_delay (float): Delay before the first inventory check begins.
        period (float): Time interval for periodic inventory checks. If 0, continuous checking is used.

    Functions:
        __init__: Initializes the RQ replenishment policy object.
        run: Continuously monitors inventory and places replenishment orders when the reorder point is reached.
    """
    
    def __init__(self, env, node, params):
        """ 
        Initialize the RQ replenishment policy object.

        Parameters:
            env (simpy.Environment): Simulation environment.
            node (object): Node to which this policy applies.
            params (dict): Replenishment policy parameters.

        Attributes:
            _info_keys (list): List of keys to include in the info dictionary.
            env (simpy.Environment): Simulation environment.
            node (object): Node to which this policy applies.
            params (dict): Replenishment policy parameters (R, Q, optional delays and period).
            name (str): Replenishment policy name.
            first_review_delay (float): Delay before the first inventory check begins.
            period (float): Time interval for periodic inventory checks. If 0, continuous checking is used.

        Returns:
            None
        """
        validate_non_negative("Reorder point (R)", params['R']) # this assertion ensures that the reorder point is non-negative
        validate_positive("Order quantity (Q)", params['Q'])  # this assertion ensures that the order quantity is positive
        super().__init__(env, node, params)
        self._info_keys.extend(["name", "first_review_delay", "period"])  # add the keys to the info dictionary
        self.name = "RQ replenishment (R, Q)"
        self.first_review_delay = params.get('first_review_delay', 0)
        self.period = params.get('period', 0)
        
    def run(self):
        """
        Continuously monitors the inventory and places replenishment orders when the inventory level 
        falls to or below the reorder point (R).

        If a periodic review interval is provided, inventory is checked at that interval.
        Otherwise, the system waits for inventory drop events to trigger the next check.

        Parameters:
            None

        Returns:
            None
        """
        R, Q = self.params['R'], self.params['Q']

        if self.first_review_delay > 0:
            yield self.env.timeout(self.first_review_delay)

        while True:
            self.node.logger.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels: {self.node.inventory.inventory.level}")
            
            if (self.node.inventory.inventory.level <= R) and (not self.node.ongoing_order):
                supplier = self.node.selection_policy.select(Q)
                self.node.ongoing_order = True
                self.env.process(self.node.process_order(supplier, Q))

            if self.period == 0:
                yield self.node.inventory_drop
                self.node.inventory_drop = self.env.event()
            else:
                yield self.env.timeout(self.period)


class PeriodicReplenishment(InventoryReplenishment):
    """
    Implements a time-based inventory replenishment policy where a fixed quantity `Q` is ordered at regular intervals `T`.

    This policy ensures consistent inventory reviews and replenishment, independent of the current stock level. 
    Supports an optional initial review delay before starting periodic checks.

    Supplier selection is automatically managed using the node’s defined supplier selection policy. 
    Shortages are recorded if the supplier does not have enough stock.

    Parameters:
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Dictionary containing replenishment parameters: T, Q, and optional parameters (first_review_delay).

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Parameters for the replenishment policy.
        name (str): Replenishment policy name.
        first_review_delay (float): Delay before the first inventory check.

   Functions:
    __init__: Initializes the replenishment policy object.
    run: Continuously manages periodic replenishment by placing orders of size `Q` every `T` time units.

    """

    def __init__(self, env, node, params):
        """ 
        Initialize the replenishment policy object.

        Parameters:
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy (T, Q)

        Attributes:
            _info_keys (list): list of keys to include in the info dictionary
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy (T, Q)
            name (str): replenishment policy name
            first_review_delay (float): delay before the first inventory check is performed

        Returns:
            None
        """
        validate_non_negative("Replenishment period (T)", params['T'])  # this assertion ensures that the replenishment period is non-negative
        validate_positive("Replenishment quantity (Q)", params['Q'])  # this assertion ensures that the replenishment quantity is positive
        super().__init__(env, node, params)
        self._info_keys.extend(["name", "first_review_delay"])  # add the keys to the info dictionary
        self.name = "Periodic replenishment (T, Q)"
        self.first_review_delay = params.get('first_review_delay', 0)

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
        T, Q = self.params['T'], self.params['Q']  # get the period and quantity
        if(self.first_review_delay > 0):
            yield self.env.timeout(self.first_review_delay)  # wait for the end of the day
        while True:
            self.node.logger.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.inventory.level}")
            supplier = self.node.selection_policy.select(Q) # select a supplier based on the supplier selection policy
            self.node.ongoing_order = True
            self.env.process(self.node.process_order(supplier, Q))
            yield self.env.timeout(T) # periodic replenishment, wait for the next period

class SupplierSelectionPolicy(InfoMixin):
    """
    Defines the framework for supplier selection strategies in the supply chain.

    Supports two modes:
    "dynamic": Supplier selection is flexible and can change based on real-time conditions.
    "fixed": Always selects a pre-assigned supplier.

    The policy is applied at the node level, and this class serves as a base for implementing custom supplier selection policies.
    The 'select' method must be overridden in subclasses to define specific supplier selection logic.

    Parameters:
        node (object): Node for which the supplier selection policy is applied.
        mode (str): Supplier selection mode. Must be "dynamic" or "fixed".

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        node (object): Node for which the supplier selection policy is applied.
        mode (str): Supplier selection mode ("dynamic" or "fixed").
        fixed_supplier (object): Fixed supplier if the mode is set to "fixed".

    Functions:
    __init__: Initializes the supplier selection policy object.
    select: Supplier selection logic to be implemented by subclasses.
    validate_suppliers: Validates that the node has at least one connected supplier.

    """
    def __init__(self, node, mode="dynamic"):
        """
        Initialize the supplier selection policy object.

        Parameters:
            node (object): Node for which the supplier selection policy is applied.
            mode (str): Supplier selection mode ("dynamic" or "fixed").

        Returns:
            None
        """
        if mode not in ["dynamic", "fixed"]:
            global_logger.logger.error(f"Invalid mode: {mode}. Mode must be either 'dynamic' or 'fixed'.")
            raise ValueError("Mode must be either 'dynamic' or 'fixed'.")
        if not isinstance(node, Node):
            global_logger.logger.error("Node must be an instance of Node class.")
            raise TypeError("Node must be an instance of Node class.")
        self._info_keys = ["node", "mode"]
        self.node = node
        self.mode = mode
        self.fixed_supplier = None

    def select(self, order_quantity):
        """
        Supplier selection logic to be implemented by subclasses.

        Parameters:
            order_quantity (float): Quantity to be ordered.

        Returns:
            None
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def validate_suppliers(self):
        """
        Validates that the node has at least one connected supplier.

        Returns:
            None
        """
        if not self.node.suppliers:
            global_logger.logger.error(f"{self.node.ID} must have at least one supplier.")
            raise ValueError(f"{self.node.ID} must have at least one supplier.")

class SelectFirst(SupplierSelectionPolicy):
    """
    Implements a supplier selection policy that always selects the first supplier in the supplier list.

    In dynamic mode, the first supplier is selected at each order event.
    In fixed mode, the first selected supplier is locked for all subsequent orders.

    Parameters:
        node (object): Node to which this supplier selection policy applies.
        mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "fixed").

    Attributes:
        node (object): Node to which this policy applies.
        mode (str): Supplier selection mode.
        fixed_supplier (object): Locked supplier if mode is "fixed".
        name (str): Name of the selection policy.
        _info_keys (list): List of keys to include in the info dictionary.

    Functions:
    __init__: Initializes the selection policy with node and mode.
    select: Selects the first supplier, either dynamically or as a fixed supplier.

    """
    def __init__(self, node, mode="fixed"):
        super().__init__(node, mode)
        self.name = "First fixed supplier"
        self._info_keys.extend(["name"])

    def select(self, order_quantity):
        """
        Selects the first supplier in the supplier list.

        In dynamic mode, the selection is evaluated for each order.
        In fixed mode, the first supplier is locked for all subsequent selections.

        Parameters:
            order_quantity (float): The quantity to order.

        Returns:
            object: The selected supplier.
        """
        self.validate_suppliers()
        selected = self.node.suppliers[0]
        if self.mode == "fixed" and self.fixed_supplier is None:
            self.fixed_supplier = selected
        return self.fixed_supplier if self.mode == "fixed" else selected


class SelectAvailable(SupplierSelectionPolicy):
    """
    Selects the first supplier that has sufficient available inventory to fulfill the requested order quantity.

    If no supplier can fully meet the order, it defaults to the first supplier in the list.
    Supports both dynamic selection (evaluated at each order event) and fixed selection (locks the first selected supplier).

    Parameters:
        node (object): Node to which this supplier selection policy applies.
        mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

    Attributes:
        node (object): Node to which this policy applies.
        mode (str): Supplier selection mode.
        fixed_supplier (object): Locked supplier if mode is "fixed".
        name (str): Name of the selection policy.
        _info_keys (list): List of keys to include in the info dictionary.

    Functions:
    __init__: Initializes the selection policy with node and mode.
    select: Selects the first available supplier with sufficient inventory.

    """
    def __init__(self, node, mode="dynamic"):
        super().__init__(node, mode)
        self.name = "First available supplier"
        self._info_keys.extend(["name"])

    def select(self, order_quantity):
        """
        Selects the first supplier with sufficient available inventory.

        If no supplier can fully meet the requested order quantity, defaults to the first supplier in the list.
        In fixed mode, the first selected supplier is locked for all subsequent orders.

        Parameters:
            order_quantity (float): The quantity to order.

        Returns:
            object: The selected supplier.
        """
        self.validate_suppliers()
        selected = self.node.suppliers[0]
        suppliers = [s for s in self.node.suppliers if s.source.inventory.inventory.level >= order_quantity]
        if suppliers:
            selected = suppliers[0]
        if self.mode == "fixed" and self.fixed_supplier is None:
            self.fixed_supplier = selected
        return self.fixed_supplier if self.mode == "fixed" else selected

class SelectCheapest(SupplierSelectionPolicy):
    """
    Selects the supplier offering the lowest transportation cost for the order.

    The supplier is chosen based on the minimum transportation cost among all connected suppliers.
    Supports both dynamic selection (evaluated at each order event) and fixed selection (locks the first selected supplier).

    Parameters:
        node (object): Node to which this supplier selection policy applies.
        mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

    Attributes:
        node (object): Node to which this policy applies.
        mode (str): Supplier selection mode.
        fixed_supplier (object): Locked supplier if mode is "fixed".
        name (str): Name of the selection policy.
        _info_keys (list): List of keys to include in the info dictionary.

    Functions:
    __init__: Initializes the supplier selection policy.
    select: Selects the supplier with the lowest transportation cost.
    """
    def __init__(self, node, mode="dynamic"):
        super().__init__(node, mode)
        self.name = "Cheapest supplier (Transportation cost)"
        self._info_keys.extend(["name"])

    def select(self, order_quantity):
        """
        Selects the supplier with the lowest transportation cost.

        In fixed mode, the first selected supplier is locked for all subsequent orders.

        Parameters:
            order_quantity (float): The quantity to order.

        Returns:
            object: The selected supplier.
        """
        self.validate_suppliers()
        selected = min(self.node.suppliers, key=lambda s: s.transportation_cost)
        if self.mode == "fixed" and self.fixed_supplier is None:
            self.fixed_supplier = selected
        return self.fixed_supplier if self.mode == "fixed" else selected

    
class SelectFastest(SupplierSelectionPolicy):
    """
    Selects the supplier with the shortest lead time to deliver the product.

    The selection is based on minimizing lead time among all connected suppliers.
    Supports both:
        - Dynamic selection: Evaluated at each order event.
        - Fixed selection: Locks the first selected supplier for all subsequent orders.

    Parameters:
        node (object): Node to which this supplier selection policy applies.
        mode (str, optional): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

    Attributes:
        node (object): Node to which this policy applies.
        mode (str): Supplier selection mode ("dynamic" or "fixed").
        fixed_supplier (object): Locked supplier if mode is "fixed".
        name (str): Name of the selection policy.
        _info_keys (list): List of keys to include in the info dictionary.

    Functions:
        __init__: Initializes the supplier selection policy and sets the selection mode.
        select: Selects the supplier with the shortest lead time based on the configured mode.
    """

    def __init__(self, node, mode="dynamic"):
        super().__init__(node, mode)
        self.name = "Fastest supplier (Lead time)"
        self._info_keys.extend(["name"])

    def select(self, order_quantity):
        """
        Selects the supplier with the shortest lead time.

        In fixed mode, the first selected supplier is locked for all subsequent orders.

        Parameters:
            order_quantity (float): The quantity to order.

        Returns:
            object: The selected supplier.
        """
        self.validate_suppliers()
        selected = min(self.node.suppliers, key=lambda s: s.lead_time())
        if self.mode == "fixed" and self.fixed_supplier is None:
            self.fixed_supplier = selected
        return self.fixed_supplier if self.mode == "fixed" else selected


class Node(NamedEntity, InfoMixin):
    """
    Represents a node in the supply network, such as a supplier, manufacturer, warehouse, distributor, retailer, or demand point.
    Supports automatic disruption and recovery, dynamic logging, and performance tracking.

    Each node can experience disruptions either probabilistically or based on custom-defined disruption and recovery times.
    During disruptions, the node becomes inactive and resumes operations after the specified recovery period.
    Tracks key performance metrics like transportation costs, node-specific costs, profit and net profit, products sold, demand placed, and shortages.

    Supports integration with Replenishment policies: (s, S), RQ, Periodic and Supplier selection policies: Available, Cheapest, Fastest
    Supported node types: "infinite_supplier", "supplier", "manufacturer", "factory", "warehouse", "distributor", "retailer", "store", "demand"

    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): Unique node ID.
        name (str): Node name.
        node_type (str): Type of the node.
        failure_p (float, optional): Probability of node failure.
        node_disrupt_time (callable, optional): Function to generate disruption time.
        node_recovery_time (callable, optional): Function to generate recovery time.
        logging (bool, optional): Flag to enable/disable logging.
        **kwargs: Additional arguments for the logger.

    Attributes:
        env (simpy.Environment): Simulation environment.
        ID (str): Node ID.
        name (str): Node name.
        node_type (str): Type of the node.
        node_failure_p (float): Node failure probability.
        node_status (str): Current node status ("active" or "inactive").
        node_disrupt_time (callable): Disruption time generator.
        node_recovery_time (callable): Recovery time generator.
        logger (GlobalLogger): Logging handler.
        transportation_cost (float): Transportation cost.
        node_cost (float): Node's operating cost.
        profit (float): Profit per unit.
        net_profit (float): Net profit (profit - node cost).
        products_sold (int): Units sold in the current cycle.
        total_products_sold (int): Total units sold.
        total_profit (float): Total profit earned.
        demand_placed (dict): Track demands placed to suppliers.
        order_shortage (list): List of order shortages with timestamp and details.

    Functions:
        __init__: Initializes the node object, validates parameters, and sets up logging and self-disruption if needed.
        disruption: Simulates node disruption and automatic recovery over time.
    """


    def __init__(self, env: simpy.Environment, 
                 ID: str, 
                 name: str, 
                 node_type: str, 
                 failure_p:float = 0.0, 
                 node_disrupt_time:callable = None,
                 node_recovery_time:callable = lambda: 1,
                 logging: bool = True,
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
            transportation_cost (float): transportation cost paid 
            node_cost (float): total node cost
            profit (float): profit per unit (sell price - buy price)
            net_profit (float): net profit of the node (total profit - node cost)
            products_sold (int): products/raw materials sold by this node in the current cycle/period/day
            total_products_sold (int): total product units sold by this node
            total_profit (float): total profit (profit per item * total_products_sold)
            demand_placed (dict): dictionary to store demand placed by this node. Key is supplier ID and value is a list containing total orders placed, total units ordered.
            order_shortage (list): list of order shortage. Each record is a tuple of (time of order, consumer ID, quantity ordered, quantity available)

        Returns:
            None
        """
        if(node_type.lower() not in ["infinite_supplier","supplier", "manufacturer", "factory", "warehouse", "distributor", "retailer", "store", "demand"]):
            global_logger.logger.error(f"Invalid node type. Node type: {node_type}")
            raise ValueError("Invalid node type.")
        if node_disrupt_time is not None:
            validate_number(name="node_disrupt_time", value=node_disrupt_time()) # check if disrupt_time is a number
        if node_recovery_time is not None:
            validate_number(name="node_recovery_time", value=node_recovery_time()) # check if disrupt_time is a number
        self._info_keys = ["ID", "name", "node_type", "failure_p", "node_status", "logging"]
        self._stats_keys = ["node_status", "transportation_cost", "node_cost", "profit", "revenue", "net_profit", "products_sold", "total_products_sold", "total_profit", "demand_placed", "orders_shortage"]
        self.env = env  # simulation environment
        self.ID = ID  # ID of the node (alphanumeric)
        self.name = name  # name of the node
        self.node_type = node_type  # type of the node (supplier, manufacturer, warehouse, distributor, retailer, demand)
        self.node_failure_p = failure_p  # node failure probability
        self.node_status = "active"  # node status (active/inactive)
        self.node_disrupt_time = node_disrupt_time  # callable function to model node disruption time
        self.node_recovery_time = node_recovery_time  # callable function to model node recovery time
    
        self.logger = GlobalLogger(logger_name=self.name, **kwargs)  # create a logger
        if not logging:
            self.logger.disable_logging()  # disable logging if logging is False
        else:
            self.logger.enable_logging()

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
                    validate_positive(name="node_disrupt_time", value=disrupt_time) # check if disrupt_time is positive
                    yield self.env.timeout(disrupt_time)
                    self.node_status = "inactive" # change the node status to inactive
                    self.logger.logger.info(f"{self.env.now}:{self.ID}: Node disrupted.")
                elif(random.random() < self.node_failure_p):
                    self.node_status = "inactive"
                    self.logger.logger.info(f"{self.env.now}:{self.ID}: Node disrupted.")
                    yield self.env.timeout(1)
            else:
                recovery_time = self.node_recovery_time() # get the recovery time
                validate_positive(name="node_recovery_time", value=recovery_time) # check if disrupt_time is positive
                yield self.env.timeout(recovery_time)
                self.node_status = "active"
                self.logger.logger.info(f"{self.env.now}:{self.ID}: Node recovered from disruption.")    
            
class Link(NamedEntity, InfoMixin):
    """
    Represents a transportation connection between two nodes in the supply network.

    Each link carries a transportation cost and lead time. Links can experience disruptions based on 
    a failure probability or a disruption time distribution and will automatically recover after a 
    specified recovery time.


    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): ID of the link.
        source (Node): Source node of the link.
        sink (Node): Sink node of the link.
        cost (float): Transportation cost of the link.
        lead_time (callable): Function returning lead time for the link.
        link_failure_p (float): Probability of random link failure.
        link_disrupt_time (callable): Function returning time to next disruption.
        link_recovery_time (callable): Function returning recovery time after disruption.

    Attributes:
        status (str): Current status of the link ("active" or "inactive").
        env (simpy.Environment): Simulation environment.
        ID (str): ID of the link.
        source (Node): Source node.
        sink (Node): Sink node.
        cost (float): Transportation cost.
        lead_time (callable): Function for stochastic lead time.
        link_failure_p (float): Failure probability.
        link_disrupt_time (callable): Disruption time function.
        link_recovery_time (callable): Recovery time function.

    Functions:
    __init__: Initializes the link object and validates parameters.
    disruption: Simulates link disruption and automatic recovery.

    """

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
        Initialize the Link object representing a transportation connection between two nodes.

        Parameters:
            env (simpy.Environment): The simulation environment.
            ID (str): Unique identifier for the link.
            source (Node): The source node of the link. Cannot be a demand node.
            sink (Node): The sink node of the link. Cannot be a supplier node.
            cost (float): Transportation cost associated with the link. Must be non-negative.
            lead_time (callable): Function returning the stochastic lead time. Cannot be None.
            link_failure_p (float, optional): Probability of random link failure. Default is 0.0.
            link_disrupt_time (callable, optional): Function returning the time to the next disruption. If provided, overrides link_failure_p.
            link_recovery_time (callable, optional): Function returning the time required for link recovery after disruption. Default is a constant 1 unit.

        Attributes:
            env (simpy.Environment): The simulation environment.
            ID (str): The ID of the link.
            source (Node): The source node.
            sink (Node): The sink node.
            name (str): Readable name of the link combining source and sink IDs.
            cost (float): Transportation cost.
            lead_time (callable): Lead time function.
            link_failure_p (float): Link failure probability.
            status (str): Link status ("active" or "inactive").
            link_recovery_time (callable): Link recovery time function.
            link_disrupt_time (callable): Disruption time function.

        Returns:
            None
        """

        self._info_keys = ["ID", "source", "sink", "cost", "lead_time", "link_failure_p"]
        self._stats_keys = ["status"]

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
        if (link_disrupt_time is not None):
            validate_number(name="link_disrupt_time", value=link_disrupt_time()) # check if disrupt_time is a number
        if (link_recovery_time is not None):
            validate_number(name="link_recovery_time", value=link_recovery_time()) # check if disrupt_time is a number

        self.env = env  # simulation environment
        self.ID = ID  # ID of the link (alphanumeric)
        self.source = source  # source node of the link
        self.sink = sink  # sink node of the link
        self.name = f"{self.source.ID} to {self.sink.ID}"  # name of the link
        self.cost = cost  # cost of the link
        self.lead_time = lead_time  # lead time of the link
        self.link_failure_p = link_failure_p  # link failure probability
        self.status = "active"  # link status (active/inactive)
        self.link_recovery_time = link_recovery_time  # link recovery time
        self.link_disrupt_time = link_disrupt_time  # link disruption time, if provided

        self.sink.suppliers.append(self)  # add the link as a supplier link to the sink node
        if(self.link_failure_p>0 or self.link_disrupt_time): # disrupt the link if link_failure_p > 0
            self.env.process(self.disruption())
        # update the selling price and buying price for the sink node based on the source node (sell price at source node = buy price at sink node)
    
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
                    validate_positive(name="link_disrupt_time", value=disrupt_time) # check if disrupt_time is positive
                    yield self.env.timeout(disrupt_time)
                    self.status = "inactive" # change the link status to inactive
                    self.logger.logger.info(f"{self.env.now}:{self.ID}: Link disrupted.")
                elif(random.random() < self.link_failure_p):
                    self.status = "inactive"
                    self.logger.logger.info(f"{self.env.now}:{self.ID}: Link disrupted.")
                    yield self.env.timeout(1)
            else:
                recovery_time = self.link_recovery_time() # get the recovery time
                validate_positive(name="link_recovery_time", value=recovery_time) # check if disrupt_time is positive
                yield self.env.timeout(recovery_time)
                self.status = "active"
                self.logger.logger.info(f"{self.env.now}:{self.ID}: Link recovered from disruption.")

class Inventory(NamedEntity, InfoMixin):
    """
    The Inventory class models stock management within a node in the supply network. 
    It supports both perishable and non-perishable items, enforces capacity limits, 
    tracks on-hand levels, and integrates with replenishment policies. For perishable 
    inventories, it manages product shelf life and automatically removes expired items. 
    The class also records inventory levels and calculates carrying costs over time.

    Parameters:
        env (simpy.Environment): Simulation environment.
        capacity (int): Maximum capacity of the inventory.
        initial_level (int): Initial inventory level.
        node (Node): Node to which this inventory belongs.
        replenishment_policy (InventoryReplenishment): Replenishment policy for the inventory.
        holding_cost (float): Holding cost per unit per time period.
        holding_period (float): Time interval for holding cost calculation.
        shelf_life (int): Shelf life for perishable items.
        inv_type (str): Type of the inventory, either "non-perishable" or "perishable".

    Attributes:
        _info_keys (list): Keys included in the information dictionary.
        _stats_keys (list): Keys included in the statistics dictionary.
        env (simpy.Environment): Simulation environment.
        capacity (int): Maximum inventory capacity.
        init_level (int): Initial inventory level.
        level (int): Current inventory level.
        on_hand (int): Current on-hand inventory.
        inv_type (str): Inventory type ("non-perishable" or "perishable").
        holding_cost (float): Holding cost per unit.
        carry_cost (float): Total accumulated carrying cost.
        carry_period (float): Carrying cost calculation interval.
        replenishment_policy (InventoryReplenishment): Inventory replenishment policy.
        inventory (simpy.Container): SimPy container managing inventory levels.
        last_update_t (float): Last timestamp when carrying cost was updated.
        perish_queue (list): Queue managing perishable items as (manufacturing_date, quantity).
        waste (float): Total quantity of expired items.
        instantaneous_levels (list): Recorded inventory levels over time.
        inventory_spend (dict): Dictionary of inventory spend by supplier ID.
        manufacturing_date (int): Manufacturing date of perishable items (used when adding stock).

    Functions:
        __init__: Initializes the inventory object.
        record_inventory_levels: Records inventory levels at regular time intervals.
        put: Adds items to the inventory, handling perishable item tracking.
        get: Removes items from inventory, using FIFO for perishables.
        remove_expired: Automatically removes expired items from perishable inventory.
        update_carry_cost: Updates carrying cost based on inventory level and holding time.
    """

    def __init__(self, 
                 env: simpy.Environment, 
                 capacity: int, 
                 initial_level: int, 
                 node: Node,
                 replenishment_policy: InventoryReplenishment,
                 holding_cost: float = 0.0,
                 holding_period: float = 1.0,
                 shelf_life: int = 0,
                 inv_type: str = "non-perishable") -> None:
        if not isinstance(node, Node):
            global_logger.logger.error("Node must be an instance of Node class.")
            raise TypeError("Node must be an instance of Node class.")
        self.node = node # node to which this inventory belongs
        if initial_level > capacity:
            self.node.logger.logger.error("Initial level cannot be greater than capacity.")
            raise ValueError("Initial level cannot be greater than capacity.")
        if replenishment_policy is not None:
            if not issubclass(replenishment_policy.__class__, InventoryReplenishment):
                self.node.logger.logger.error(f"{replenishment_policy.__name__} must inherit from InventoryReplenishment")
                raise TypeError(f"{replenishment_policy.__name__} must inherit from InventoryReplenishment")
        if inv_type not in ["non-perishable", "perishable"]:
            self.node.logger.logger.error(f"Invalid inventory type. {inv_type} is not yet available.")
            raise ValueError(f"Invalid inventory type. {inv_type} is not yet available.")
        validate_positive("Capacity", capacity)
        validate_non_negative("Initial level", initial_level)
        validate_non_negative("Inventory holding cost",holding_cost)
        self._info_keys = ["capacity", "initial_level", "replenishment_policy", "holding_cost", "holding_period", "shelf_life", "inv_type"]
        self._stats_keys = ["level", "carry_cost", "inventory_spend", "instantaneous_levels"]
        self.env = env
        self.capacity = capacity
        self.init_level = initial_level
        self.level = initial_level
        self.on_hand = initial_level # current inventory level
        self.inv_type = inv_type
        self.holding_cost = holding_cost
        self.carry_cost = 0 # initial carrying cost based on the initial inventory level
        self.carry_period = holding_period # default carrying cost calculation interval is 1 time unit (day)
        self.replenishment_policy = replenishment_policy
        self.inventory = simpy.Container(env=self.env, capacity=self.capacity, init=self.init_level) # Inventory container setup
        self.last_update_t = self.env.now # last time the carrying cost was updated
        
        if self.inv_type == "perishable":
            self.shelf_life = shelf_life
            self.perish_queue = [(0, initial_level)]
            self.waste = 0
            self.env.process(self.remove_expired())

        self.instantaneous_levels = []
        self.inventory_spend = {} # dictionary to store inventory spend (inventory replenishment cost incurred). Key is supplier ID, value is total replenishment cost
        self.env.process(self.record_inventory_levels())  # record inventory levels at regular intervals

    def record_inventory_levels(self):
        """
        Record inventory levels at regular intervals.
        
        Parameters:
            None
        
        Attributes: 
            None

        Returns:
            None
        """
        while True:
            self.instantaneous_levels.append((self.env.now,self.inventory.level))  # record the current inventory level
            yield self.env.timeout(1)

    def put(self, amount: int, manufacturing_date: int = None):
        """
        Add items to inventory. For perishable items, tracks manufacturing date.

        Parameters:
            amount (int): amount to add
            manufacturing_date (int): only required for perishable inventories
        """
        if self.inventory.capacity == float('inf'):
            return
        
        if amount + self.inventory.level > self.capacity:
            amount = self.capacity - self.inventory.level 
        if amount <= 0:
            return
        if self.inv_type == "perishable":
            if manufacturing_date is None:
                self.node.logger.logger.error("Manufacturing date must be provided for perishable inventory.")
                raise ValueError("Manufacturing date must be provided for perishable inventory.")
            inserted = False
            for i in range(len(self.perish_queue)):
                if self.perish_queue[i][0] > manufacturing_date:
                    self.perish_queue.insert(i, (manufacturing_date, amount))
                    inserted = True
                    break
            if not inserted:
                self.perish_queue.append((manufacturing_date, amount))
        self.update_carry_cost()  # Update carrying cost based on the amount added
        self.inventory.put(amount)
        self.level = self.inventory.level  # Update the current inventory level
        if(not self.node.inventory_raised.triggered):
            self.node.inventory_raised.succeed()  # signal that inventory has been raised

    def get(self, amount: int):
        """
        Remove items from inventory. For perishable items, oldest products are removed first.

        Parameters:
            amount (int): amount to remove

        Returns:
            tuple: (SimPy get event, List of (manufacture_date, quantity)) for perishable items
        """
        if self.inventory.capacity == float('inf'):
            return self.inventory.get(amount), []
        if amount == 0:
            return None, []
        man_date_ls = []
        if self.inv_type == "perishable":    
            x_amount = amount
            while x_amount > 0 and self.perish_queue:
                mfg_date, qty = self.perish_queue[0]
                if qty <= x_amount:
                    man_date_ls.append((mfg_date, qty))
                    x_amount -= qty
                    self.perish_queue.pop(0)
                else:
                    man_date_ls.append((mfg_date, x_amount))
                    self.perish_queue[0] = (mfg_date, qty - x_amount)
                    x_amount = 0
        self.update_carry_cost()
        get_event = self.inventory.get(amount)
        self.level = self.inventory.level  # Update the current inventory level
        self.on_hand -= amount  # Update the on-hand inventory level
        if(self.replenishment_policy):
            if(not self.node.inventory_drop.triggered):
                self.node.inventory_drop.succeed()  # signal that inventory has been dropped
        return get_event, man_date_ls

    def remove_expired(self):
        """
        Remove expired items from perishable inventory.
        """
        while True:
            yield self.env.timeout(1)
            while self.perish_queue and self.env.now - self.perish_queue[0][0] >= self.shelf_life:
                mfg_date, qty = self.perish_queue.pop(0)
                self.logger.logger.info(f"{self.env.now:.4f}: {qty} units expired.")
                self.waste += qty
                if qty > 0:
                    self.get(qty)

    def update_carry_cost(self):
        """
        Update the carrying cost of the inventory based on the current level and holding cost.
        """
        carry_period = self.env.now - self.last_update_t
        self.carry_cost += self.inventory.level * (carry_period) * self.holding_cost  # update the carrying cost based on the current inventory level
        self.last_update_t = self.env.now  # update the last update time

class Supplier(Node):
    """
    The Supplier class represents a supplier in the supply network that continuously 
    extracts raw materials whenever the inventory is not full. Each supplier is associated 
    with a specific raw material and can have either finite or infinite inventory capacity.

    For finite suppliers, raw materials are extracted in batches based on the extraction 
    quantity and extraction time specified by the RawMaterial object. For infinite suppliers, 
    inventory is considered unlimited.

    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): Unique identifier for the supplier.
        name (str): Name of the supplier.
        node_type (str): Type of the node (default is "supplier").
        capacity (int): Maximum capacity of the supplier's inventory.
        initial_level (int): Initial inventory level.
        inventory_holding_cost (float): Holding cost per unit of inventory.
        raw_material (RawMaterial): Raw material provided by the supplier.
        **kwargs: Additional keyword arguments for the Node class and logger.

    Attributes:
        raw_material (RawMaterial): Raw material provided by the supplier.
        inventory (Inventory): Inventory object associated with the supplier.
        inventory_drop (simpy.Event): Event triggered when inventory drops.
        inventory_raised (simpy.Event): Event triggered when inventory is replenished.
        sell_price (float): Selling price of the raw material.
        stats (Statistics): Object for tracking supplier statistics.
        total_raw_materials_mined (int): Total quantity of raw materials mined (recorded in stats).
        total_material_cost (float): Total cost of raw materials mined (recorded in stats).

    Functions:
        __init__: Initializes the supplier object.
        behavior: Simulates the continuous raw material extraction process.
    """

    def __init__(self, 
                 env: simpy.Environment, 
                 ID: str, 
                 name: str, 
                 node_type: str = "supplier",
                 capacity: int = 0, 
                 initial_level: int = 0, 
                 inventory_holding_cost:float = 0.0, 
                 raw_material: RawMaterial = None, 
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
            total_raw_materials_mined (int): total raw materials mined/extracted
            total_material_cost (float): total cost of the raw materials mined/extracted
            total_raw_materials_sold (int): total raw materials sold

        Returns:
            None
        """
        
        super().__init__(env=env,ID=ID,name=name,node_type=node_type,**kwargs)
        self._info_keys.extend(["capacity", "initial_level"])
        self._stats_keys.extend(["total_raw_materials_mined", "total_material_cost", "total_raw_materials_sold"])
        self.raw_material = raw_material # raw material supplied by the supplier
        self.sell_price = 0
        if(self.node_type!="infinite_supplier"):
            self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, node=self, holding_cost=inventory_holding_cost, replenishment_policy=None)
            self.inventory_drop = self.env.event()  # event to signal when inventory is dropped
            self.inventory_raised = self.env.event() # signal to indicate that inventory has been raised
            if(self.raw_material):
                self.sell_price = self.raw_material.cost # selling price of the raw material
                self.env.process(self.behavior()) # start the behavior process
            else:
                self.logger.logger.error(f"{self.ID}:Raw material not provided for this supplier. Recreate it with a raw material.")
                raise ValueError("Raw material not provided.")
        else:
            self.inventory = Inventory(env=self.env, capacity=float('inf'), initial_level=float('inf'), node=self, holding_cost=inventory_holding_cost, replenishment_policy=None)
        
        self.stats = Statistics(self)
        setattr(self.stats,"total_raw_materials_mined",0)
        setattr(self.stats,"total_material_cost",0)
        
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
        yield self.env.timeout(1)
        while True:
            if(self.inventory.inventory.level < self.inventory.inventory.capacity): # check if the inventory is not full
                mined_quantity = self.raw_material.extraction_quantity
                if((self.inventory.inventory.level+self.raw_material.extraction_quantity)>self.inventory.inventory.capacity): # check if the inventory can accommodate the extracted quantity
                    mined_quantity = self.inventory.inventory.capacity - self.inventory.inventory.level # update statistics
                self.inventory.put(mined_quantity)
                self.stats.update_stats(total_raw_materials_mined=mined_quantity, total_material_cost=mined_quantity*self.raw_material.mining_cost)
                self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Raw material mined/extracted. Inventory level:{self.inventory.inventory.level}")
                yield self.env.timeout(self.raw_material.extraction_time)
            else:
                yield self.env.timeout(1)
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}: Inventory level:{self.inventory.inventory.level}") # log every day/period inventory level

class InventoryNode(Node):
    """
    The InventoryNode class represents an inventory management node in the supply network, 
    such as a retailer or distributor. It manages inventory levels, replenishment policies, 
    supplier selection, and order processing dynamically.

    The node can handle both perishable and non-perishable inventories and supports 
    automatic replenishment using various replenishment policies. InventoryNode 
    interacts with multiple supplier links and selects suppliers based on the 
    configured selection policy.

    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): Unique identifier for the node.
        name (str): Name of the inventory node.
        node_type (str): Type of the inventory node (e.g., retailer or distributor).
        capacity (int): Maximum capacity of the inventory.
        initial_level (int): Initial inventory level.
        inventory_holding_cost (float): Inventory holding cost per unit.
        replenishment_policy (InventoryReplenishment): Replenishment policy object for the inventory.
        policy_param (dict): Parameters for the replenishment policy.
        product_sell_price (float): Selling price of the product.
        product_buy_price (float): Buying price of the product.
        inventory_type (str): Type of inventory ("non-perishable" or "perishable").
        shelf_life (int): Shelf life of the product for perishable items.
        manufacture_date (callable): Function to model manufacturing date (used for perishable inventories).
        product (Product): Product managed by the inventory node.
        supplier_selection_policy (SupplierSelectionPolicy): Supplier selection policy class.
        supplier_selection_mode (str): Mode for supplier selection (default is "fixed").
        **kwargs: Additional keyword arguments for the Node class and logger.

    Attributes:
        replenishment_policy (InventoryReplenishment): Replenishment policy object.
        inventory (Inventory): Inventory object managing stock.
        inventory_drop (simpy.Event): Event triggered when inventory drops.
        inventory_raised (simpy.Event): Event triggered when inventory is replenished.
        manufacture_date (callable): Manufacturing date generation function.
        sell_price (float): Selling price of the product.
        buy_price (float): Buying price of the product.
        product (Product): Product managed by the node.
        suppliers (list): List of supplier links connected to this node.
        ongoing_order (bool): Indicates if an order is currently in process.
        selection_policy (SupplierSelectionPolicy): Supplier selection policy object.
        stats (Statistics): Statistics tracking object for this node.

    Functions:
        __init__: Initializes the InventoryNode object.
        process_order: Places an order with the selected supplier and updates inventory upon delivery.
    """

    def __init__(self,
                 env: simpy.Environment, 
                 ID: str, 
                 name: str, 
                 node_type: str, 
                 capacity: int, 
                 initial_level: int, 
                 inventory_holding_cost:float,
                 replenishment_policy:InventoryReplenishment, 
                 policy_param: dict,
                 product_sell_price: float,
                 product_buy_price: float,
                 inventory_type:str = "non-perishable", 
                 shelf_life:int = 0,
                 manufacture_date:callable = None,
                 product:Product = None,
                 supplier_selection_policy: SupplierSelectionPolicy = SelectFirst,
                 supplier_selection_mode: str = "fixed",
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
            suppliers (list): list of supplier links from which the inventory node can replenish inventory
            replenishment_policy (str): replenishment policy for the inventory
            policy_param (list): parameters for the replenishment policy
            inventory (Inventory): inventory object
            product (Product): product that the inventory node sells
            manufacture_date (callable): function to model manufacturing date
            sell_price (float): selling price of the product
            buy_price (float): buying price of the product
            ongoing_order (bool): flag to check if the order is placed
        
        Returns:
            None

        Behavior:
            The inventory node sells the product to the customers. It replenishes the inventory from the suppliers according to the replenishment policy. 
            The inventory node can have multiple suppliers. It chooses a supplier based on the availability of the product at the suppliers.
            The product buy price is set to the supplier's product sell price. The inventory node sells the product at a higher price than the buy price.
        """
        super().__init__(env=env,ID=ID,name=name,node_type=node_type,**kwargs)
        self._info_keys.extend(["capacity", "initial_level", "replenishment_policy", "product_sell_price", "product_buy_price"])
        if(replenishment_policy):
            self.replenishment_policy = replenishment_policy(env = self.env, node = self, params = policy_param)
            self.env.process(self.replenishment_policy.run())

        self.capacity = capacity
        self.initial_level = initial_level
        self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, node=self, 
                                   inv_type=inventory_type, holding_cost=inventory_holding_cost, 
                                   replenishment_policy=self.replenishment_policy, shelf_life=shelf_life)
        self.inventory_drop = self.env.event()  # event to signal when inventory is dropped
        self.inventory_raised = self.env.event() # signal to indicate that inventory has been raised
        self.manufacture_date = manufacture_date
        self.sell_price = product_sell_price # set the sell price of the product
        self.buy_price = product_buy_price # set the buy price of the product
        if product is not None:
            self.product = copy.deepcopy(product) # product that the inventory node sells
            self.product.sell_price = product_sell_price
            self.product.buy_price = product_buy_price # set the buy price of the product to the product buy price
        self.suppliers = []
        self.ongoing_order = False # flag to check if the order is placed
        self.selection_policy = supplier_selection_policy(self,supplier_selection_mode)
        self.stats = Statistics(self, periodic_update=True, period=1) # create a statistics object for the inventory node

    def process_order(self, supplier, reorder_quantity):
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
        if supplier.source.inventory.inventory.level < reorder_quantity:  # check if the supplier is able to fulfill the order, record shortage
            shortage = reorder_quantity - supplier.source.inventory.inventory.level
            supplier.source.stats.update_stats(orders_shortage=[1,shortage], backorder=[1,reorder_quantity])

        if(supplier.source.node_status == "active"):
            self.stats.update_stats(demand_placed=[1,reorder_quantity],transportation_cost=supplier.cost)
            supplier.source.stats.update_stats(demand_received=[1,reorder_quantity])
            
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing inventory from supplier:{supplier.source.name}, order placed for {reorder_quantity} units.")
            event, man_date_ls = supplier.source.inventory.get(reorder_quantity)
            yield event

            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.") # log the shipment
            lead_time = supplier.lead_time() # get the lead time from the supplier
            validate_non_negative(name="lead_time", value=lead_time) # check if lead_time is non-negative
            yield self.env.timeout(lead_time) # lead time for the order
            if(self.inventory.inventory.level + reorder_quantity > self.inventory.inventory.capacity): # check if the inventory can accommodate the reordered quantity
                reorder_quantity = self.inventory.inventory.capacity - self.inventory.inventory.level # if not, set the reorder quantity to the remaining capacity
            
            if(man_date_ls):
                for ele in man_date_ls: # get manufacturing date from the supplier
                    self.inventory.put(ele[1],ele[0])
            elif(self.inventory.inv_type=="perishable"): # if self inventory is perishable but manufacture date is not provided
                if(self.manufacture_date): # calculate the manufacturing date using the function if provided
                    self.inventory.put(reorder_quantity,self.manufacture_date(self.env.now))
                else: # else put the product in the inventory with current time as manufacturing date
                    self.inventory.put(reorder_quantity,self.env.now)
            else:
                self.inventory.put(reorder_quantity)

            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Inventory replenished. reorder_quantity={reorder_quantity}, Inventory levels:{self.inventory.inventory.level}")

            self.stats.update_stats(fulfillment_received=[1,reorder_quantity],inventory_spend_cost=reorder_quantity*self.buy_price)
            supplier.source.stats.update_stats(demand_fulfilled=[1,reorder_quantity])
        else:
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Supplier:{supplier.source.name} is disrupted. Order not placed.")
        self.ongoing_order = False

class Manufacturer(Node):
    """
    The Manufacturer class models a production unit in the supply network that consumes raw materials 
    to manufacture finished products. It maintains separate inventories for raw materials and finished goods, 
    applies replenishment policies to the product inventory, and places orders to suppliers dynamically.

    The manufacturer can be connected to multiple suppliers and automatically produces products based on 
    raw material availability. It continuously updates real-time statistics such as production volume, 
    manufacturing cost, and revenue.

    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): Unique identifier for the manufacturer.
        name (str): Name of the manufacturer.
        capacity (int): Maximum capacity of the finished product inventory.
        initial_level (int): Initial inventory level for finished products.
        inventory_holding_cost (float): Holding cost per unit for finished products.
        product_sell_price (float): Selling price per unit of the finished product.
        replenishment_policy (InventoryReplenishment): Replenishment policy object for the product inventory.
        policy_param (dict): Parameters for the replenishment policy.
        product (Product): Product manufactured by the manufacturer.
        inventory_type (str): Type of inventory ("non-perishable" or "perishable").
        shelf_life (int): Shelf life of the product.
        supplier_selection_policy (SupplierSelectionPolicy): Supplier selection policy class.
        supplier_selection_mode (str): Supplier selection mode (default is "fixed").
        **kwargs: Additional keyword arguments for the Node class and logger.

    Attributes:
        replenishment_policy (InventoryReplenishment): Replenishment policy object for the product inventory.
        inventory (Inventory): Inventory object managing finished product stock.
        inventory_drop (simpy.Event): Event triggered when inventory drops.
        inventory_raised (simpy.Event): Event triggered when inventory is replenished.
        product (Product): Product manufactured by the manufacturer.
        suppliers (list): List of supplier links connected to this manufacturer.
        sell_price (float): Selling price per unit of the product.
        production_cycle (bool): Indicates whether the production cycle is currently active.
        raw_inventory_counts (dict): Inventory levels of raw materials by raw material ID.
        ongoing_order_raw (dict): Tracks ongoing orders for each raw material.
        ongoing_order (bool): Indicates whether a raw material order is currently in progress.
        selection_policy (SupplierSelectionPolicy): Supplier selection policy object.
        stats (Statistics): Statistics tracking object for the manufacturer.

    Functions:
        __init__: Initializes the Manufacturer object.
        manufacture_product: Manufactures the product by consuming raw materials and updating product inventory.
        behavior: Main behavior loop that checks inventory and triggers production if raw materials are available.
        process_order: Places an order for raw materials based on the quantity of products to be manufactured.
        process_order_raw: Places an individual order for a specific raw material from a supplier.

    Behavior:
        The manufacturer continuously monitors raw material inventory levels and initiates production when raw materials 
        are available. Finished products are added to the inventory upon completion. If raw materials are insufficient, 
        the manufacturer places replenishment orders with connected suppliers.

    Assumptions:
        The manufacturer produces only a single type of product.
        Separate inventories are maintained for raw materials and finished products.
        Only the finished product inventory is actively monitored by the replenishment policy.
        Raw material inventories are replenished based on product inventory requirements.
        The raw material inventory is initially empty.
    """

    def __init__(self,
                 env: simpy.Environment, 
                 ID: str, 
                 name: str, 
                 capacity: int, 
                 initial_level: int, 
                 inventory_holding_cost: float, 
                 product_sell_price: float, 
                 replenishment_policy: InventoryReplenishment, 
                 policy_param: dict, 
                 product: Product = None, 
                 inventory_type: str = "non-perishable",
                 shelf_life: int = 0,
                 supplier_selection_policy: SupplierSelectionPolicy = SelectFirst,
                 supplier_selection_mode: str = "fixed",
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
            product (Product): product manufactured by the manufacturer
            suppliers (list): list of suppliers from which the manufacturer can replenish inventory
            replenishment_policy (str): replenishment policy for the inventory
            policy_param (list): parameters for the replenishment policy
            sell_price (float): selling price of the product
            production_cycle (bool): production cycle status
            raw_inventory_counts (dict): dictionary to store inventory counts for raw products inventory
            ongoing_order_raw (dict): dictionary to store order status for raw materials
            ongoing_order (bool): order status for the product
            inventory (Inventory): inventory of the manufacturer
            profit (float): profit per unit sold
            total_products_manufactured (int): total products manufactured
            total_manufacturing_cost (float): total cost of the products manufactured
            revenue (float): revenue from the products sold
            isolated_logger (bool): flag to enable/disable isolated logger

        Returns:
            None
        """
        super().__init__(env=env,ID=ID,name=name,node_type="manufacturer",**kwargs)
        if product == None:
            self.node.logger.logger.error("Product not provided for the manufacturer.")
            raise ValueError("Product not provided for the manufacturer.")
        
        self._info_keys.extend(["capacity", "initial_level", "replenishment_policy", "product_sell_price"])
        self._stats_keys.extend(["total_products_manufactured", "total_manufacturing_cost", "revenue"]) 
        if(replenishment_policy):
            self.replenishment_policy = replenishment_policy(env = self.env, node = self, params = policy_param)
            self.env.process(self.replenishment_policy.run())
        self.capacity = capacity
        self.initial_level = initial_level
        
        self.inventory = Inventory(env=self.env, capacity=self.capacity, initial_level=self.initial_level, node=self, inv_type=inventory_type, holding_cost=inventory_holding_cost, replenishment_policy=self.replenishment_policy, shelf_life=shelf_life)
        self.inventory_drop = self.env.event()  # event to signal when inventory is dropped
        self.inventory_raised = self.env.event() # signal to indicate that inventory has bee
        self.product = product # product manufactured by the manufacturer
        self.suppliers = []
        self.product.sell_price = product_sell_price
        self.sell_price = product_sell_price # set the sell price of the product
        
        self.production_cycle = False # production cycle status
        self.raw_inventory_counts = {} # dictionary to store inventory counts for raw products inventory
        self.ongoing_order_raw = {} # dictionary to store order status
        self.ongoing_order = False # order status for the product        

        if(self.product.buy_price <= 0): # if the product buy price is not given, calculate it
            self.product.buy_price = self.product.manufacturing_cost 
            for raw_material in self.product.raw_materials:
                self.product.buy_price += raw_material[0].cost * raw_material[1] # calculate total cost of the product (per unit)

        self.env.process(self.behavior()) # start the behavior process
        self.selection_policy = supplier_selection_policy(self,supplier_selection_mode)
        
        self.stats = Statistics(self, periodic_update=True, period=1) # create a statistics object for the manufacturer
        setattr(self.stats,"total_products_manufactured",0) # adding specific statistics for the manufacturer
        setattr(self.stats,"total_manufacturing_cost",0) # adding specific statistics for the manufacturer

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
        max_producible_units = self.product.batch_size 
        for raw_material in self.product.raw_materials:
            raw_mat_id = raw_material[0].ID
            required_amount = raw_material[1]
            current_raw_material_level = self.raw_inventory_counts[raw_mat_id]
            max_producible_units = min(max_producible_units,int(current_raw_material_level/required_amount))
        if((self.inventory.inventory.level + max_producible_units)>self.inventory.inventory.capacity): # check if the inventory can accommodate the maximum producible units
            max_producible_units = self.inventory.inventory.capacity - self.inventory.inventory.level
        if(max_producible_units>0):
            self.production_cycle = True # produce the product
            for raw_material in self.product.raw_materials: # consume raw materials
                raw_mat_id = raw_material[0].ID
                required_amount = raw_material[1]
                self.raw_inventory_counts[raw_mat_id] -= raw_material[1]*max_producible_units
            yield self.env.timeout(self.product.manufacturing_time) # take manufacturing time to produce the product            
            self.inventory.put(max_producible_units, manufacturing_date=self.env.now)
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}: {max_producible_units} units manufactured.")
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}: Product inventory levels:{self.inventory.inventory.level}")
            self.stats.update_stats(total_products_manufactured=max_producible_units, total_manufacturing_cost=max_producible_units*self.product.manufacturing_cost) # update statistics
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
            self.node.logger.logger.error("No suppliers connected to the manufacturer.")
            raise ValueError("No suppliers connected to the manufacturer.")

        if(len(self.suppliers)>0): # create an inventory for storing raw materials as a dictionary. Key: raw material ID, Value: inventory level
            for supplier in self.suppliers: # iterate over supplier links
                if(supplier.source.raw_material is None): # check if the supplier has a raw material
                    self.logger.logger.error(f"{self.ID}:Supplier {supplier.source.ID} does not have a raw material. Please provide a raw material for the supplier.")
                    raise ValueError(f"Supplier {supplier.source.ID} does not have a raw material.")
                self.raw_inventory_counts[supplier.source.raw_material.ID] = 0 # store initial levels
                self.ongoing_order_raw[supplier.source.raw_material.ID] = False # store order status
                
        if(len(self.suppliers)<len(self.product.raw_materials)):
            self.node.logger.logger.warning(f"{self.ID}: {self.name}: The number of suppliers are less than the number of raw materials required to manufacture the product! This leads to no products being manufactured.")

        while True: # behavior of the manufacturer: consume raw materials, produce the product, and put the product in the inventory
            if(len(self.suppliers)>=len(self.product.raw_materials)): # check if required number of suppliers are connected
                if(not self.production_cycle):
                    self.env.process(self.manufacture_product()) # produce the product
            yield self.env.timeout(1)

    def process_order_raw(self, raw_mat_id, supplier, reorder_quantity):
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
        if supplier.source.inventory.inventory.level < reorder_quantity:  # check if the supplier is able to fulfill the order, record shortage
            shortage = reorder_quantity - supplier.source.inventory.inventory.level
            supplier.source.stats.update_stats(orders_shortage=[1,shortage], backorder=[1,reorder_quantity])

        if(supplier.source.node_status == "active"): # check if the supplier is active and has enough inventory
            if(self.raw_inventory_counts[raw_mat_id]>= reorder_quantity): # dont order if enough inventory is available (reorder_quantity depends on the number of product units that needs to be manufactured, there is no capcacity defined for raw material inventory)
                self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Sufficient raw material inventory for {supplier.source.raw_material.name}, no order placed. Current inventory level: {self.raw_inventory_counts}.")
                self.ongoing_order_raw[raw_mat_id] = False
                self.ongoing_order = False # set the order status to False
                return

            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing raw material:{supplier.source.raw_material.name} from supplier:{supplier.source.ID}, order placed for {reorder_quantity} units. Current inventory level: {self.raw_inventory_counts}.")
            event, man_date_ls = supplier.source.inventory.get(reorder_quantity)
            supplier.source.stats.update_stats(demand_received=[1,reorder_quantity]) # update the supplier statistics for demand received
            yield event
            
            self.stats.update_stats(demand_placed=[1,reorder_quantity],transportation_cost=supplier.cost)
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.")                
            lead_time = supplier.lead_time() # get the lead time from the supplier
            validate_non_negative(name="lead_time", value=lead_time) # check if lead_time is non-negative
            yield self.env.timeout(lead_time) # lead time for the order
            
            self.stats.update_stats(fulfillment_received=[1,reorder_quantity],inventory_spend_cost=reorder_quantity*supplier.source.sell_price)
            supplier.source.stats.update_stats(demand_fulfilled=[1,reorder_quantity]) # update the supplier statistics for demand fulfilled
            self.ongoing_order_raw[raw_mat_id] = False
            self.raw_inventory_counts[raw_mat_id] += reorder_quantity     
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Order received from supplier:{supplier.source.name}, inventory levels: {self.raw_inventory_counts}")
            self.ongoing_order = False # set the order status to False
        else:
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Supplier:{supplier.source.name} is disrupted.")
            yield self.env.timeout(1) # wait for 1 time unit before checking again

        self.ongoing_order_raw[raw_mat_id] = False
    
    def process_order(self, supplier, reorder_quantity):
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
        self.ongoing_order = True # set the order status to True
        for raw_mat in self.product.raw_materials: # place order for all raw materials required to produce the product
            raw_mat_id = raw_mat[0].ID
            raw_mat_reorder_sz = raw_mat[1]*reorder_quantity
            for supplier in self.suppliers:
                if(supplier.source.raw_material.ID == raw_mat_id and self.ongoing_order_raw[raw_mat_id] == False): # check if the supplier has the raw material and order is not already placed
                    self.ongoing_order_raw[raw_mat_id] = True # set the order status to True
                    self.env.process(self.process_order_raw(raw_mat_id, supplier, raw_mat_reorder_sz)) # place the order for the raw material
        yield self.env.timeout(1) # wait for the order to be placed

class Demand(Node):
    """
    The `Demand` class represents a customer-facing node that generates and fulfills product orders within the supply network. It models dynamic demand patterns using user-defined functions for order arrival times and order quantities, and manages customer tolerance for waiting in case of product unavailability.
    The demand node automatically places customer orders at configurable intervals and can handle situations where the requested quantity is not immediately available. Customers can either wait (if tolerance is set) or leave the system unfulfilled.

    For example, if customers arrive at a rate of one every 5 minutes and order between 10-20 units per request, the demand node will place these orders to its connected supply node. If the requested quantity is unavailable, the system either splits the order (if partial fulfillment is allowed) or waits for the inventory to be replenished, depending on the customer's tolerance.

    The class supports: Customizable lead time and delivery cost per order, Dynamic order splitting based on the minimum split ratio, Backorder management and real-time inventory check.
    The customer behavior, order processing, and shortage tracking are automatically simulated using SimPy processes.

    

    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): Unique identifier for the demand node.
        name (str): Name of the demand node.
        order_arrival_model (callable): Function that models inter-arrival times between customer orders.
        order_quantity_model (callable): Function that models the quantity per customer order.
        demand_node (Node): Upstream node from which the demand node sources products.
        tolerance (float): Maximum time customers are willing to wait if required quantity is unavailable.
        order_min_split_ratio (float): Minimum allowable fraction of the order that can be delivered in split deliveries.
        delivery_cost (callable): Function that models the delivery cost per order.
        lead_time (callable): Function that models the delivery lead time per order.
        **kwargs: Additional keyword arguments for Node and GlobalLogger.

    Attributes:
        order_arrival_model (callable): Function defining the order arrival process.
        order_quantity_model (callable): Function defining the order quantity distribution.
        demand_node (Node): Upstream node supplying the demand.
        customer_tolerance (float): Maximum waiting time allowed for customer orders.
        delivery_cost (callable): Delivery cost function for each order.
        lead_time (callable): Delivery lead time function for each order.
        min_split (float): Minimum allowed split ratio for partially fulfilled orders.
        stats (Statistics): Tracks various performance metrics like demand placed, fulfilled, and shortages.

    Functions:
        __init__: Initializes the demand node object and validates input models.
        _process_delivery: Handles the delivery process, including lead time and delivery cost updates.
        wait_for_order: Waits for required units based on customer tolerance when immediate fulfillment is not possible.
        customer: Simulates customer order placement and fulfillment behavior.
        behavior: Generates continuous customer demand based on the arrival and quantity models.

    
    Behavior:
        The demand node generates customer orders at random intervals and quantities using the specified arrival 
        and quantity models. If the upstream inventory can satisfy the order, delivery is processed immediately. 
        If not, the customer may wait for the order to be fulfilled within their tolerance time, possibly accepting 
        partial deliveries if a split ratio is allowed. If the tolerance is exceeded, the unmet demand is recorded as a shortage.

    Assumptions:
        - Customer orders arrive following the provided stochastic arrival model.
        - Order quantities follow the specified stochastic quantity model.
        - Customers can accept split deliveries based on the minimum split ratio.
        - Customers may wait for the fulfillment of their orders up to the defined tolerance time.
        - If customer tolerance is zero, unfulfilled demand is immediately considered a shortage.
        - Delivery cost and lead time are sampled dynamically for each order.
        - The connected upstream node must not be a supplier; it should typically be a retailer or distributor node.
    """


    def __init__(self,
                 env: simpy.Environment, 
                 ID: str, 
                 name: str, 
                 order_arrival_model: callable, 
                 order_quantity_model: callable, 
                 demand_node: Node,
                 tolerance: float = 0.0,
                 order_min_split_ratio: float = 1.0,
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
        if order_arrival_model is None or order_quantity_model is None:
            raise ValueError("Order arrival and quantity models cannot be None.")
        if demand_node is None or "supplier" in demand_node.node_type:
            raise ValueError("Demand node must be a valid non-supplier node.")
        validate_non_negative("Customer tolerance", tolerance)
        validate_positive("Order Min Split Ratio", order_min_split_ratio)
        if order_min_split_ratio > 1:
            self.logger.logger.error("Order Min Split Ratio is greater than 1. It will be set to 1.")
            raise ValueError("Order Min Split Ratio must be in the range [0, 1].")
        validate_number(name="order_time", value=order_arrival_model())
        validate_number(name="order_quantity", value=order_quantity_model())
        validate_number(name="delivery_cost", value=delivery_cost()) # check if delivery_cost is a number
        validate_number(name="lead_time", value=lead_time()) # check if lead_time is a number

        super().__init__(env=env,ID=ID,name=name,node_type="demand",**kwargs)
        self._info_keys.extend(["order_arrival_model", "order_quantity_model", "demand_node", "customer_tolerance", "delivery_cost", "lead_time"])
        self._stats_keys = ["node_status","transportation_cost", "node_cost","total_products_sold","total_demand","demand_placed"]
        
        self.order_arrival_model = order_arrival_model
        self.order_quantity_model = order_quantity_model
        self.demand_node = demand_node
        self.customer_tolerance = tolerance
        self.delivery_cost = delivery_cost
        self.lead_time = lead_time
        self.min_split = order_min_split_ratio
        self.env.process(self.behavior())
        self.stats = Statistics(self, periodic_update=True, period=1) # create a statistics object for the demand node

    def _process_delivery(self, order_quantity, customer_id):
        
        del_cost = self.delivery_cost()
        validate_non_negative(name="delivery_cost", value=del_cost) # check if delivery_cost is non-negative
        self.stats.update_stats(transportation_cost=del_cost)
        
        get_event, _ = self.demand_node.inventory.get(order_quantity)
        yield get_event
        self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}:Order quantity:{order_quantity}, available.")

        lead_time = self.lead_time() # get the lead time from the demand node
        validate_non_negative(name="lead_time", value=lead_time) # check if lead_time is non-negative
        yield self.env.timeout(lead_time) # wait for the delivery of the order
        self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}:Order quantity:{order_quantity} received.")

        self.stats.update_stats(fulfillment_received=[1,order_quantity])
        self.demand_node.stats.update_stats(demand_fulfilled=[1,order_quantity]) 
    
    def wait_for_order(self,customer_id,order_quantity):
        """
        Wait for the required number of units based on customer tolerance.
        If the customer tolerance is infinite, the method waits until the order is fulfilled.
        Otherwise, it waits for the specified tolerance time and updates the unsatisfied demand if the order is not fulfilled.
        
        Parameters:
            order_quantity (int): The quantity of the product ordered.
            customer_id (int): Customer ID for logging purposes.

        Attributes:
            customer_id (int): Customer ID for logging purposes.
            order_quantity (int): The quantity of the product ordered.
        
        Returns:
            None
        """
        self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}:Order quantity:{order_quantity} not available! Order will be split if split ratio is provided.")
        partial = order_quantity
        if self.min_split < 1:
            partial = int(order_quantity * self.min_split)
        waited = 0
        available = 0
        while order_quantity>0 and waited<=self.customer_tolerance:
            waiting_time = self.env.now
            available = self.demand_node.inventory.inventory.level
            if order_quantity <= available: # check if remaining order quantity is available 
                self.env.process(self._process_delivery(order_quantity, customer_id))
                order_quantity = 0
            elif available >= partial: # or else at least min required 'partial' is available
                self.env.process(self._process_delivery(available, customer_id))
                order_quantity -= available # update order quantity
            else: 
                self.demand_node.stats.update_stats(orders_shortage=[1,order_quantity-available])
            yield self.demand_node.inventory_raised # wait until inventory is replenished
            self.demand_node.inventory_raised = self.env.event()  # reset the event for the next iteration
            waited += self.env.now - waiting_time # update the waited time
        
        if order_quantity > 0: # if the order quantity is still greater than 0, it means the order was not fulfilled
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}: remaining order quantity:{order_quantity} not available!")

    def customer(self,customer_id,order_quantity):
        """
        Simulate the customer behavior, ordering products from demand node, consume and return.

        Parameters:
            customer_id (int): Customer ID for logging purposes.
            order_quantity (int): The quantity of the product ordered.

        Attributes:
            customer_id (int): Customer ID for logging purposes.
            order_quantity (int): The quantity of the product ordered.

        Returns:
            None
        """
        available = self.demand_node.inventory.inventory.level
        self.stats.update_stats(demand_placed=[1,order_quantity]) # update the demand placed statistics
        if order_quantity <= available:
            self.demand_node.stats.update_stats(demand_received=[1,order_quantity])
            yield from self._process_delivery(order_quantity, customer_id)
        elif self.customer_tolerance > 0: # wait for tolerance time if order quantity is not available (backorder policy = allowed total)
            self.demand_node.stats.update_stats(demand_received=[1,order_quantity],orders_shortage=[1,order_quantity-available]) # update the orders shortage statistics
            self.env.process(self.wait_for_order(customer_id, order_quantity))
        else: # No tolerance, leave without placing an order (backorder policy = not allowed)
            self.logger.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}: Order quantity:{order_quantity} not available, inventory level:{self.demand_node.inventory.inventory.level}. No tolerance! Shortage:{order_quantity-available}.")
            self.demand_node.stats.update_stats(orders_shortage=[1,order_quantity-available]) # update the orders shortage statistics
    
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
        customer_id = 1 # customer ID
        while True:
            order_time = self.order_arrival_model()
            order_quantity = self.order_quantity_model() 
            validate_non_negative(name=f"{self.ID}:order_arrival_model()", value=order_time)
            validate_positive(name=f"{self.ID}:order_quantity_model()", value=order_quantity)
            self.env.process(self.customer(f"{customer_id}", order_quantity)) # spawn a customer process
            customer_id += 1 # increment customer ID
            yield self.env.timeout(order_time) # wait for the next order arrival