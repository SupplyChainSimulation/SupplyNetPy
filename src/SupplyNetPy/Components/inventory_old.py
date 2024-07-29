import simpy
import matplotlib.pyplot as plt

REPLENISHMENT_POLICIES = ["ss","periodic","justintime"]
INVENTORY_TYPES = ["single","mixed","perishable"]

class Product:
    def __init__(self, sku, name, description, cost, profit, product_type, shelf_life):
        """
        Represents a product in the supply chain.

        Parameters:
        - sku (str): stock keeping unit number
        - name (str): product name
        - description (str): discription of the product
        - cost (float): product unit cost
        - profit (float): profit per unit of the product
        - product_type (str): perishable, non-perishable
        - shelf_life (int): product shelf life (None in case it is non-perishable)
        """
        self.sku = sku
        self.name = name
        self.description = description
        self.cost = cost
        self.profit = profit
        self.product_type = product_type # perishable, non-perishable
        self.shelf_life = shelf_life

    def get_product_details(self):
        """
        Get details of the product.

        Returns:
        - str: Product details.
        """
        return f"Product SKU: {self.sku}, Name: {self.name}, Description: {self.description}"

class MonitoredContainer(simpy.Container):
    """
    Extension of SimPy's Container class with monitoring capabilities.
    This class allows monitoring of the container's level over time.
    It records the inventory level and time at regular intervals
    to analyze and visualize the behavior of the container.
    
    Parameters:
    - enable_monitoring (bool): Enable or disable monitoring of the container's level.

    Inherits from:
    - simpy.Container

    Attributes:
    - leveldata (list): A list to store recorded inventory levels.
    - timedata (list): A list to store corresponding timestamps for recorded levels.
    - avg_level (float): Time-averaged inventory level.
    - last_level (int): Last recorded inventory level.
    - last_timestamp (float): Timestamp of the last recorded level change.
    """
    def __init__(self, enable_monitoring, *args, **kwargs):
        """
        Initialize the MonitoredContainer.
        Parameters:
        - enable_monitoring (bool): Enable or disable monitoring of the container's level.
        - *args, **kwargs: Additional arguments to be passed to the simpy.Container constructor.
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
            self.avg_level = ((self.avg_level * self.last_timestamp)+ (delta_t * self.last_level)) / float(self._env.now)
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
        - result: Result of the put operation.
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
        - result: Result of the get operation.
        """
        result = super()._do_get(*args, **kwargs)
        self.record_level()
        return result

class Inventory:
    """
        Represents the inventory of a supply chain node.
    """
    def __init__(self, env, capacity, holding_cost, reorder_level=0, 
                 reorder_period=1, inventory_type="Single", replenishment_policy="sS", products=None):
        """
        Parameters:
        - env : SimPy Environment var
        - capacity (int): The maximum capacity of the inventory.
        - holding_cost (float): The holding cost per unit per day of the product.
        - reorder_level (int): The inventory level at which a reorder is triggered.
        - reorder_period (int): The time period between successive reorders.
        - inventory_type (str): The type of inventory (e.g., raw materials, finished goods).
        - replenishment_policy (str): The replenishment policy for the inventory 
          (e.g., Fixed Order Quantity, Periodic, Just In Time, Min-Max (s,S), Demand driven).
        - products (list of Product, optional): The list of products in the inventory. Defaults to None.
        """
        self.env = env
        self.capacity = capacity
        self.holding_cost = holding_cost
        self.reorder_level = reorder_level
        self.reorder_period = reorder_period
        self.inventory_type = inventory_type
        self.replenishment_policy = replenishment_policy
        self.products = products if products is not None else []

        self.stats_inventory_hold_costs = []

        # check for inventory 'capacity'
        if(self.capacity <= 0 or type(self.capacity)!=int):
            raise ValueError("Inventory capacity cannot be zero/negative/non-integer!")
        
        # check for inventory 'holding_cost'
        if(self.holding_cost <=0):
            raise ValueError("Inventory holding cost cannot be zero or negative!")        

        # check for reorder_level
        if(self.reorder_level>self.capacity or self.reorder_level<0):
            raise ValueError("Inventory reorder level cannot be negative/more than inventory capacity!")    

        # check for reorder_period
        if(self.reorder_period<=0):
            raise ValueError("Inventory reorder period cannot be negative/zero!")    

        global REPLENISHMENT_POLICIES
        # check for replenishment policy
        if(self.replenishment_policy.lower() not in REPLENISHMENT_POLICIES):
            raise ValueError(f"{self.replenishment_policy} is not currently available! Please select from these: (1) sS, (2) Periodic, (3) JustInTime")
        
        global INVENTORY_TYPES
        # check for inventory type
        if(self.inventory_type.lower() not in INVENTORY_TYPES):
            raise ValueError(f"{self.inventory_type} is not currently available! Please select from these: (1) Single, (2) Mixed, (3) Perishable")
        
        # check for self_products
        if(self.inventory_type.lower() == "mixed" and (self.products==None or self.products==[] or len(self.products)==1)):
            raise ValueError(f"Need more than one products to create 'Mixed' inventory! If there are no multiple products then choose 'Single' inventory type.")
        
        self.inventory = MonitoredContainer(enable_monitoring=True, env=env, init=self.capacity, capacity=self.capacity)

    # -TO DO-
    # Inventory Get method
        # Single item Inventory: directly get an item from the Container
        # Mixed items Inventory: needs logic that keeps count of item types that are stored in the Container
            # Get an item of the given type: need to update the item count and Container
            # possible scenario
            # (item1 storage space required = 1, but item2 storage space required is 2)
        # Perishable: needs logic that stores items' current shelf lives, and 'Get' accordingly
            # need a Priority Queue for this

    # Inventory Put method (similar to Get above)

    # Note: For the time being, only the 'single' inventory type is implemented; only sS replenishment policy is implemented

    def get(self,quantity,product=None):
        """
        Get 'quantity' units from this inventory.
        Parameters:
        quntity (int): number of units requested by the buyer 
        product (Product): product id/sku
        """
        if(self.inventory_type=="Single"):
            return self.inventory.get(quantity)

    def put(self,quantity,product=None):
        """
        Put 'quantity' units to this inventory.
        Parameters:
        quntity (int): number of units requested by the buyer 
        product (Product): product id/sku
        """
        if(self.inventory_type=="Single"):
            return self.inventory.put(quantity)
    
    def level(self):
        """
        Return inventory levels
        """
        return self.inventory.level

    def plot_inventory_levels(self,node_name,marker='.',color="red",linestyle='-'):
        """
        Plots inventory levels of this inventory over time.
        x-axis: time
        y-axis: inventory level
        Parameters:
        - node_name (str): name of the node that monitors this inventory
        - marker (str): plot market
        - color (str): line color
        - linestyle (str): linestyle
        """
        plt.plot(self.inventory.timedata, self.inventory.leveldata, marker=marker, color=color, linestyle=linestyle, label=f"{node_name} Inventory Levels")
        plt.xlabel("Time")
        plt.ylabel("Level")
        plt.title("Inventory levels over time")
        plt.legend()
        plt.show()