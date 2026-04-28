from SupplyNetPy.Components.logger import GlobalLogger
import enum
import heapq
import simpy
import copy
import random
import numbers
from typing import Callable

# Public API — names re-exported by Components/__init__.py. Module-level
# constants ``_rng``, ``_LOGGER_KWARGS`` and ``_NODE_KWARGS`` are internal and
# intentionally omitted. ``global_logger`` IS exported: the docs advertise
# ``scm.global_logger.enable_logging() / disable_logging()`` as a bulk
# logging-control handle, so it is supported surface (even though day-to-day
# users should prefer per-node ``logging=False`` or ``node.logger.*``).
# ``set_seed`` is the sanctioned entry point for seeding the default RNG;
# per-instance RNG injection lives behind the ``rng=`` constructor kwarg.
__all__ = [
    "set_seed",
    "validate_positive",
    "validate_non_negative",
    "validate_number",
    "ensure_numeric_callable",
    "NodeType",
    "NamedEntity",
    "InfoMixin",
    "Statistics",
    "RawMaterial",
    "Product",
    "InventoryReplenishment",
    "SSReplenishment",
    "RQReplenishment",
    "PeriodicReplenishment",
    "SupplierSelectionPolicy",
    "SelectFirst",
    "SelectAvailable",
    "SelectCheapest",
    "SelectFastest",
    "Node",
    "Link",
    "Inventory",
    "Supplier",
    "InventoryNode",
    "Manufacturer",
    "Demand",
    "global_logger",
]

global_logger = GlobalLogger() # create a global logger

# Library-wide default RNG. Nodes and Links fall back to this when no per-instance
# rng is supplied. Users reproduce a run by calling set_seed(n) before building
# the network, or by passing their own random.Random() to individual components.
_rng = random.Random()

def set_seed(seed):
    """
    Seed the library-wide default RNG used for probabilistic node/link disruption.

    Components built without an explicit ``rng`` argument draw from this RNG, so
    seeding it once before constructing the network is enough to make a run
    reproducible. Components that were passed an explicit ``rng`` are unaffected.

    Parameters:
        seed: any value accepted by ``random.Random.seed`` (typically ``int``).

    Returns:
        None
    """
    _rng.seed(seed)

# Whitelist of kwargs accepted by GlobalLogger. Node.__init__ forwards only these to
# the logger, and Node subclasses strip them out before forwarding the rest to
# Inventory — which has a strict signature (no **kwargs), so unknown keys like
# typo'd parameter names raise TypeError at the Inventory boundary.
_LOGGER_KWARGS = {"log_to_file", "log_file", "log_to_screen"}

# Node-level kwargs that Node.__init__ consumes. Node subclasses (Supplier,
# InventoryNode, Manufacturer, Demand) use **kwargs, so these leak into the
# subclass's local kwargs even after being forwarded to super(); they must be
# stripped before that kwargs dict is forwarded onward to Inventory.
_NODE_KWARGS = {"failure_p", "node_disrupt_time", "node_recovery_time", "logging", "rng", "logger_name", "stats_period", "periodic_stats"}


class NodeType(str, enum.Enum):
    """
    Canonical node types accepted by :class:`Node` and :func:`create_sc_net`.

    ``NodeType`` is a ``str`` subclass, so every existing comparison against a
    literal string (``node.node_type == "demand"``, ``"supplier" in node.node_type``,
    ``node.node_type.lower()``) continues to work unchanged. Users can pass
    either a plain string (case-insensitive, via :meth:`_missing_`) or a
    :class:`NodeType` member:

    .. code-block:: python

        scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier")
        scm.Supplier(env=env, ID="S1", name="S1", node_type=scm.NodeType.SUPPLIER)

    :func:`create_sc_net` dispatches via a :class:`NodeType`-keyed table
    (``_NODE_DISPATCH`` in ``utilities.py``), replacing the duplicated
    hard-coded ``node["node_type"].lower() in [...]`` ladders. Adding a new
    node type is a single-site change on this enum plus an entry in the
    dispatch table — no more editing two hard-coded string lists.
    """
    INFINITE_SUPPLIER = "infinite_supplier"
    SUPPLIER = "supplier"
    MANUFACTURER = "manufacturer"
    FACTORY = "factory"
    WAREHOUSE = "warehouse"
    DISTRIBUTOR = "distributor"
    RETAILER = "retailer"
    STORE = "store"
    SHOP = "shop"
    DEMAND = "demand"

    @classmethod
    def _missing_(cls, value):
        """Case-insensitive lookup so ``NodeType("SUPPLIER")`` resolves correctly."""
        if isinstance(value, str):
            lowered = value.lower()
            for member in cls:
                if member.value == lowered:
                    return member
        return None

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
        global_logger.error(f"{name} must be positive.")
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
        global_logger.error(f"{name} cannot be negative.")
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
        global_logger.error(f"function {name}() must return a number (an int or a float).")
        raise ValueError(f"function {name}() must be a number (an int or a float).")


def ensure_numeric_callable(name: str, value):
    """
    Normalise a scalar-or-callable parameter to a zero-arg numeric callable.

    Many constructors accept either a number or a zero-arg callable (lead
    times, arrival intervals, recovery times). The previous auto-wrap was

    .. code-block:: python

        if not callable(value):
            value = lambda val=value: val

    which silently accepted any callable — including a class like ``int`` or
    a generator function — turning the eventual ``value()`` call into a
    runtime explosion deep inside a SimPy process (§6.4). This helper fixes
    that by invoking the callable once at validation time and asserting the
    result is a real number; non-numeric returns surface immediately at
    construction with a clear error message naming the offending parameter.

    Parameters:
        name (str): Parameter name used in error messages.
        value: A number or a zero-arg callable returning a number.

    Returns:
        callable: A zero-arg callable. If ``value`` was a scalar it is wrapped;
            if it was already callable the original is returned unchanged.

    Raises:
        TypeError: If ``value`` is callable but invoking it raises (the
            original exception is chained).
        ValueError: If the (wrapped) callable returns a non-numeric value.

    Note:
        The validation invocation samples the callable once at construction
        time. For stateful generators or iterators (rather than pure
        functions) this advances state before the simulation starts; if
        that matters, wrap the iterator in a closure that materialises the
        first sample lazily, or pass a numeric scalar instead.
    """
    if not callable(value):
        scalar = value
        value = lambda val=scalar: val
    try:
        sample = value()
    except Exception as e:
        global_logger.error(f"{name}: callable raised {type(e).__name__} on validation call: {e}")
        raise TypeError(
            f"{name} must be a number or a zero-arg callable returning a number; "
            f"calling it raised {type(e).__name__}: {e}"
        ) from e
    if not isinstance(sample, numbers.Number):
        global_logger.error(
            f"{name} must be a number or a zero-arg callable returning a number; "
            f"got {type(sample).__name__} ({sample!r})."
        )
        raise ValueError(
            f"{name} must be a number or a zero-arg callable returning a number; "
            f"got {type(sample).__name__}."
        )
    return value
        
class NamedEntity:
    """
    The `NamedEntity` class provides a standardized way to display names of the objects in the supply chain model. 
    When printed or displayed, the object will show its `name` (if defined), otherwise its `ID`, or the class name 
    as a fallback. This improves the readability and interpretability of simulation outputs by ensuring objects are 
    easily identifiable.
    
    Parameters:
        None

    Attributes:
        None

    Functions:
        __str__: returns the name of the object if available, otherwise returns the class name
        __repr__: returns the name of the object if available, otherwise returns the class name
    """
    def __str__(self) -> str:
        """Returns the name of the object if available, otherwise returns the class name."""
        return getattr(self, 'name', getattr(self, 'ID', self.__class__.__name__))

    def __repr__(self) -> str:
        """Returns the name of the object if available, otherwise returns the class name."""
        return getattr(self, 'name', getattr(self, 'ID', self.__class__.__name__))

class InfoMixin:
    """
    The `InfoMixin` class allows objects to easily provide their key details and statistics as dictionaries. 
    This helps in quickly summarizing, logging, or analyzing object data in a structured and consistent way 
    across the simulation.

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

    def get_info(self) -> dict:
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
    
    def get_statistics(self) -> dict:
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
    The `Statistics` class tracks and summarizes key performance indicators for each node in the supply chain.
    It monitors essential metrics such as demand, inventory levels, shortages, backorders, costs, revenue, and profit.
    The class supports both automatic periodic updates and manual updates through the `update_stats` method,
    which can be called at any point in the simulation to immediately record changes.

    The ``_info_keys`` / ``_stats_keys`` / ``_cost_components`` declarations are
    class-level, making the tracked set of KPIs declaratively discoverable in
    one place. ``Statistics.__init__`` copies the ``_stats_keys`` and
    ``_cost_components`` lists to the instance before any per-node extension
    runs (``Supplier.__init__`` and ``Manufacturer.__init__`` append their own
    subclass-specific KPIs), so those appends never leak into the class-level
    list and cross-contaminate other Statistics instances.

    Parameters:
        node (object): The node for which statistics are tracked.
        periodic_update (bool, optional): Whether to update statistics periodically. Default is False.
        period (float, optional): Time interval for periodic updates. Default is 1.

    Attributes:
        node (object): The node to which this statistics object belongs.
        name (str): Name of the statistics object. By default, it is the node's name post-fix " statistics".
        demand_placed (list): Orders and quantities placed by this node.
        fulfillment_received (list): Orders and quantities received by this node.
        demand_received (list): Orders and quantities demanded at this node.
        demand_fulfilled (list): Orders and quantities fulfilled by this node.
        shortage (list): Orders and quantities that faced shortage. ``orders_shortage`` is kept as a back-compat alias (§6.6).
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
    # Declarative KPI surface. Subclasses / node subclasses that need extra
    # stats append to ``self.stats._stats_keys`` / ``self.stats._cost_components``
    # after constructing Statistics; the ``__init__`` below copies these lists
    # to the instance so those appends never mutate the class-level lists.
    _info_keys = ["name"]
    _stats_keys = [
        "name",
        "demand_placed", "fulfillment_received", "demand_received", "demand_fulfilled",
        "shortage", "backorder",
        "inventory_level", "inventory_waste",
        "inventory_carry_cost", "inventory_spend_cost", "transportation_cost",
        "node_cost", "revenue", "profit",
    ]
    # Attributes that contribute to ``node_cost``. ``node_cost`` itself is NOT
    # listed — it is the derived sum (see ``update_stats``).
    _cost_components = ["inventory_carry_cost", "inventory_spend_cost", "transportation_cost"]

    def __init__(self, node:object, periodic_update:bool=False, period:float=1):
        """
        Initialize the statistics object.
        
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
            shortage (list): Orders and quantities that faced shortage. ``orders_shortage`` is kept as a back-compat alias (§6.6).
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
        
        Returns:
            None
        """
        # Clone the class-level declarative lists onto the instance so that
        # per-node extensions (e.g. ``Supplier`` appending "total_material_cost"
        # to its own ``self.stats._stats_keys``) do not leak into the shared
        # class attribute and pollute other Statistics instances.
        self._stats_keys = list(type(self)._stats_keys)
        self._cost_components = list(type(self)._cost_components)
        self.node = node # the node to which this statistics object belongs
        self.name = f"{self.node.ID} statistics"
        self.demand_placed = [0,0] # demand placed by this node [total orders placed, total quantity]
        self.fulfillment_received = [0,0] # fulfillment received by this node
        self.demand_received = [0,0] # demand received by this node (demand at this node)
        self.demand_fulfilled = [0,0] # demand fulfilled by this node (demand that was served by this node)
        # ``shortage`` (was ``orders_shortage`` before §6.6) — renamed to
        # match ``supplychainnet["shortage"]`` so the same vocabulary applies
        # at both the node and network level. ``orders_shortage`` is kept as
        # a read-only alias / accepted ``update_stats`` kwarg for back-compat.
        self.shortage = [0,0] # shortage of products at this node
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

        Drives the reset off ``_stats_keys`` so any KPI registered on a
        Statistics instance (including subclass-specific ones added by
        ``Supplier`` / ``Manufacturer``) is zeroed without the caller having
        to remember to extend ``reset``. The legacy ``vars(self)`` scan is
        kept as a fallback for instance attributes that aren't in
        ``_stats_keys`` (e.g. user-injected scratch fields).

        Parameters:
            None

        Returns:
            None
        """
        # Pass 1 — zero everything declared on _stats_keys (the source of
        # truth for tracked KPIs).
        for key in self._stats_keys:
            if not hasattr(self, key) or key == "name":
                continue
            current = getattr(self, key)
            if isinstance(current, list):
                setattr(self, key, [0, 0])
            elif isinstance(current, (int, float)):
                setattr(self, key, 0)
        # Pass 2 — back-stop for any non-tracked instance attribute that
        # used to be reset by the historical ``vars(self)`` sweep.
        for key, value in vars(self).items():
            if key.startswith("_") or key in self._stats_keys:
                continue
            if isinstance(value, list):
                setattr(self, key, [0, 0])
            elif isinstance(value, (int, float)):
                setattr(self, key, 0)
        # Inventory-side counters live on Inventory, not on Statistics, so
        # they need an explicit reset here. Adding a new metric on Inventory
        # that should reset means appending to this guarded block (or
        # promoting the metric to Statistics via _stats_keys).
        if hasattr(self.node, 'inventory'):
            self.node.inventory.carry_cost = 0
            self.node.inventory.waste = 0

    @property
    def orders_shortage(self):
        """Back-compat alias for :attr:`shortage`. Returns the same list (mutating it mutates ``shortage``)."""
        return self.shortage

    @orders_shortage.setter
    def orders_shortage(self, value):
        self.shortage = value

    def update_stats(self,**kwargs):
        """
        Update the statistics with the given keyword arguments.

        Parameters:
            **kwargs: keyword arguments containing the statistics to update.
                ``orders_shortage=`` is accepted as a back-compat alias for
                ``shortage=`` (§6.6 renamed the attribute).

        Attributes:
            None

        Returns:
            None
        """
        # Back-compat: ``orders_shortage`` was renamed to ``shortage`` in §6.6.
        # External code (and historical examples) still pass the old kwarg —
        # fold it onto the new key here so both spellings drive the same
        # bookkeeping. If a caller passes both, the new spelling wins.
        if "orders_shortage" in kwargs and "shortage" not in kwargs:
            kwargs["shortage"] = kwargs.pop("orders_shortage")
        elif "orders_shortage" in kwargs:
            kwargs.pop("orders_shortage")
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
                global_logger.warning(f"{self.node.ID}: (Updaing stats) Attribute {key} not found in Statistics class.")
        if hasattr(self.node, 'inventory'):
            if self.node.inventory.level != float('inf'):
                self.inventory_level = self.node.inventory.level if hasattr(self.node, 'inventory') else 0
                self.node.inventory.update_carry_cost()
                self.inventory_carry_cost = self.node.inventory.carry_cost
                self.inventory_waste = self.node.inventory.waste if hasattr(self.node.inventory, 'waste') else 0
        self.node_cost = sum(getattr(self, name) for name in self._cost_components)
        self.revenue = self.demand_fulfilled[1] * self.node.sell_price if hasattr(self.node, 'sell_price') else 0
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
    The `RawMaterial` class represents a raw material in a supply chain. It defines key properties of a raw material, 
    including extraction rate, extraction time, mining cost, and selling price. This class helps model the extraction 
    processes at a raw material supplier node in the network.

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
    _info_keys = ["ID", "name", "extraction_quantity", "extraction_time", "mining_cost", "cost"]
    _stats_keys = []

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
        validate_non_negative("Mining Cost", mining_cost)
        validate_positive("Cost", cost)
        self.ID = ID # ID of the raw material (alphanumeric)
        self.name = name # name of the raw material
        self.extraction_quantity = extraction_quantity # quantity of the raw material that is extracted in extraction_time
        self.extraction_time = extraction_time # time to extract 'extraction_quantity' units of raw material
        self.mining_cost = mining_cost # mining cost of the raw material (per item)
        self.cost = cost # selling cost of the raw material (per item)

class Product(NamedEntity, InfoMixin):
    """
    The `Product` class models a finished good in the supply chain. It defines essential properties such 
    as manufacturing cost, manufacturing time, selling price, and the raw materials required to produce it. 
    The class supports both buying and manufacturing workflows, allowing nodes to either purchase the product 
    directly or produce it using defined raw material combinations. Products are typically manufactured in 
    batches, with each batch size and cycle time configurable, making it easy to model real-world production processes.

    Parameters:
        ID (str): ID of the product.
        name (str): Name of the product.
        manufacturing_cost (float): Manufacturing cost per unit.
        manufacturing_time (float): Time to manufacture one batch.
        sell_price (float): Selling price per unit.
        raw_materials (list): List of (raw material object, quantity) tuples required to produce one unit.
        batch_size (int): Number of units manufactured per cycle.
        buy_price (float, optional): Buying price per unit (default is 0).

    Attributes:
        _info_keys (list): Keys to include in the info dictionary.
        _stats_keys (list): Keys to include in the statistics dictionary.
        ID (str): ID of the product.
        name (str): Name of the product.
        manufacturing_cost (float): Manufacturing cost per unit.
        manufacturing_time (float): Manufacturing time for one batch.
        sell_price (float): Selling price per unit.
        buy_price (float): Buying price per unit.
        raw_materials (list): List of (raw material, quantity) tuples required to produce one unit.
        batch_size (int): Units manufactured per cycle.

    Functions:
        __init__: Initializes the product object.
    """
    _info_keys = ["ID", "name", "manufacturing_cost", "manufacturing_time", "sell_price", "buy_price", "raw_materials", "batch_size"]
    _stats_keys = []

    def __init__(self,
                 ID: str,
                 name: str,
                 manufacturing_cost: float,
                 manufacturing_time: float,
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
            manufacturing_time (float): Time to manufacture one batch of products
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
            manufacturing_time (float): Time to manufacture one batch
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
            global_logger.error("Raw materials cannot be empty.")
            raise ValueError("Raw materials cannot be empty.")
        for raw_mat in raw_materials:
            if not isinstance(raw_mat[0], RawMaterial):
                raise ValueError("Invalid raw material.")
            if raw_mat[1] <= 0:
                raise ValueError("Invalid quantity for raw material.")

        self.ID = ID # ID of the product (alphanumeric)
        self.name = name # name of the product
        self.manufacturing_cost = manufacturing_cost # manufacturing cost of the product (per unit)
        self.manufacturing_time = manufacturing_time # time (days) to manufacture 'batch_size' units of product
        self.sell_price = sell_price # price at which the product is sold
        self.buy_price = buy_price # price at which the product is bought, (default: 0). It is used by InventoryNode buy the product at some price and sell it at a higher price.   
        self.raw_materials = raw_materials # list of raw materials and quantity required to manufacture a single product unit
        self.batch_size = batch_size # number of units manufactured per cycle

class InventoryReplenishment(InfoMixin, NamedEntity):
    """

    The `InventoryReplenishment` class defines the abstract structure for inventory replenishment policies within
    SupplyNetPy. It provides a common interface for managing how nodes place replenishment orders during the simulation.

    This class is not intended for direct use. It must be subclassed to implement specific replenishment strategies,
    such as min-max (s, S), reorder point, quantity (RQ), or periodic review (TQ) policies.

    The `run` method should be overridden to define the replenishment logic for the policy. The class integrates with
    the SimPy environment to support time-driven inventory management. The `inventory_drop` event is used to signal stock
    depletion, enabling the replenishment process to respond to changes in inventory levels in real time.

    **Node contract for custom subclasses.** A policy should speak to its owning node through four helpers rather than
    reaching into node internals:

    - `self.node.position()` — backorder-aware inventory position (`on_hand - stats.backorder[1]`).
    - `self.node.place_order(quantity)` — selects a supplier via the node's selection policy and spawns the dispatch
      process. Replaces the `selection_policy.select(...)` + `env.process(process_order(...))` pair.
    - `self.node.wait_for_drop()` — generator used as `yield from self.node.wait_for_drop()` to block until the
      inventory drops; rotates the `inventory_drop` event atomically on wake-up.
    - `Link.available_quantity()` — for any supplier-selection policy, compares upstream stock without reading
      `link.source.inventory.level` directly.

    Staying inside this contract keeps a policy subclass independent of the concrete node layout and makes it
    compatible with any future `Node` subclass that provides the same methods.

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
    _info_keys = ["node", "params"]

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
        if not isinstance(env, simpy.Environment):
            raise ValueError("Invalid environment. Provide a valid SimPy environment.")
        self.env = env  # simulation environment
        self.node = node  # node to which this policy applies
        self.params = params  # parameters for the replenishment policy

    def run(self):
        """
        This method should be overridden by subclasses to implement the specific replenishment policy logic.
        """
        pass

class SSReplenishment(InventoryReplenishment):
    """
    Implements the (s, S) or min-max inventory replenishment policy with optional safety stock support.

    When the inventory level falls to or below the reorder point (s), an order is placed to replenish 
    stock up to the order-up-to level (S). If safety stock is provided, both the reorder point and the 
    order-up-to level are adjusted accordingly. The policy supports both event-driven and periodic inventory 
    checks, with an optional initial review delay. Supplier selection is automatically managed using the 
    node’s supplier selection policy.

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
    _info_keys = InventoryReplenishment._info_keys + ["name", "first_review_delay", "period"]

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
        if 's' not in params or 'S' not in params:
            raise ValueError("Parameters 's' and 'S' must be provided for the (s, S) replenishment policy.")
        if params['s'] > params['S']:
            raise ValueError("Reorder point (s) must be less than or equal to order-up-to level (S).")
        super().__init__(env, node, params)
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
        # ``s > S`` validation already runs in __init__ (line ~751); the
        # duplicate guard here was §8's "duplicate s>S check" nit. Removed.

        if 'safety_stock' in self.params: # check if safety_stock is specified
            validate_positive("Safety stock", self.params['safety_stock'])
            self.name = "min-max with safety replenishment (s, S, safety_stock)"
            s += self.params['safety_stock']
            S += self.params['safety_stock']

        if self.first_review_delay > 0: # if first review delay is specified, wait for the specified time before starting the replenishment process
            yield self.env.timeout(self.first_review_delay)

        while True: # run the replenishment process indefinitely
            self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.level}, on hand:{self.node.inventory.on_hand}")
            position = self.node.position()
            if position <= s:
                self.node.place_order(S - position)

            if self.period == 0: # if periodic check is OFF
                yield from self.node.wait_for_drop()  # wait for the inventory to be dropped
            elif self.period: # if periodic check is ON
                yield self.env.timeout(self.period)

class RQReplenishment(InventoryReplenishment):
    """
    Implements a Reorder Quantity (RQ) Inventory Replenishment Policy with optional safety stock support.

    This policy continuously monitors inventory levels and places a replenishment order when the inventory 
    falls to or below the reorder point (R). The replenishment quantity is fixed at Q units per order.

    The inventory can be checked continuously (event-based) if 'period' is set to 0 (default) and periodically if 
    a positive 'period' is provided. An optional first review delay can be configured to introduce a delay before 
    the first inventory check begins.

    Supplier selection is managed automatically using the node's supplier selection policy. If the selected 
    supplier does not have sufficient inventory, the shortage is recorded.

    Parameters:
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Parameters for the replenishment policy: R, Q, and optional parameters (safety_stock, first_review_delay, period).

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
    _info_keys = InventoryReplenishment._info_keys + ["name", "first_review_delay", "period"]

    def __init__(self, env, node, params):
        """ 
        Initialize the RQ replenishment policy object.

        Parameters:
            env (simpy.Environment): Simulation environment.
            node (object): Node to which this policy applies.
            params (dict): Replenishment policy parameters R, Q, and optional parameters (safety_stock, first_review_delay, period).

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

        Attributes:
            R (float): Reorder point.
            Q (float): Replenishment quantity.
        
        Returns:
            None
        """
        R, Q = self.params['R'], self.params['Q']

        if self.first_review_delay > 0:
            yield self.env.timeout(self.first_review_delay)

        while True:
            self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels: {self.node.inventory.level}, on hand: {self.node.inventory.on_hand}")
            if self.node.position() <= R:
                self.node.place_order(Q)

            if self.period == 0:
                yield from self.node.wait_for_drop()
            else:
                yield self.env.timeout(self.period)

class PeriodicReplenishment(InventoryReplenishment):
    """
    Implements a time-based inventory replenishment policy where a fixed quantity `Q` is ordered at regular intervals
    `T` with optional safety stock support.

    This policy ensures consistent inventory reviews and replenishment, independent of the current stock level. Supports 
    an optional initial review delay before starting periodic checks.

    Supplier selection is automatically managed using the node’s defined supplier selection policy. Shortages are 
    recorded if the supplier does not have enough stock.

    Parameters:
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Dictionary containing replenishment parameters: T, Q, and optional parameters (safety_stock, first_review_delay).

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Parameters for the replenishment policy.
        name (str): Replenishment policy name.
        first_review_delay (float): Delay before the first inventory check.

    Functions:
        __init__: Initializes the replenishment policy object.
        run: Continuously manages periodic replenishment by placing orders of size Q every T time units.
    """
    _info_keys = InventoryReplenishment._info_keys + ["name", "first_review_delay"]

    def __init__(self, env, node, params):
        """ 
        Initialize the replenishment policy object.

        Parameters:
            env (simpy.Environment): simulation environment
            node (object): node to which this policy applies
            params (dict): parameters for the replenishment policy (T, Q), and optional parameters (safety_stock, first_review_delay).

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
        validate_positive("Replenishment period (T)", params['T'])  # this assertion ensures that the replenishment period is positive
        validate_positive("Replenishment quantity (Q)", params['Q'])  # this assertion ensures that the replenishment quantity is positive
        super().__init__(env, node, params)
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
        ss = 0
        if 'safety_stock' in self.params: # check if safety_stock is specified
            validate_non_negative("Safety stock", self.params['safety_stock'])
            self.name = "Periodic with safety replenishment (T, Q, safety_stock)"
            ss = self.params['safety_stock']

        if self.first_review_delay > 0:
            yield self.env.timeout(self.first_review_delay)

        while True:
            self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.level}, on hand:{self.node.inventory.on_hand}")
            reorder_quantity = Q
            if self.node.inventory.level < ss:
                reorder_quantity += ss - self.node.inventory.level
            self.node.place_order(reorder_quantity)
            yield self.env.timeout(T) # periodic replenishment, wait for the next period

class SupplierSelectionPolicy(InfoMixin, NamedEntity):
    """
    Defines the framework for supplier selection strategies in the supply chain.

    Supports two modes:
    (1) "dynamic": Supplier selection is flexible and can change based on real-time conditions.
    (2) "fixed": Always selects a pre-assigned supplier.

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
    _info_keys = ["node", "mode"]

    def __init__(self, node, mode="dynamic"):
        """
        Initialize the supplier selection policy object.

        Parameters:
            node (object): Node for which the supplier selection policy is applied.
            mode (str): Supplier selection mode ("dynamic" or "fixed").

        Attributes:
            _info_keys (list): List of keys to include in the info dictionary.
            node (object): Node for which the supplier selection policy is applied.
            mode (str): Supplier selection mode ("dynamic" or "fixed").
            fixed_supplier (object): Fixed supplier if the mode is set to "fixed".

        Returns:
            None

        Raises:
            ValueError: If the mode is not "dynamic" or "fixed".
            TypeError: If the node is not an instance of Node class.
        """
        if mode not in ["dynamic", "fixed"]:
            global_logger.error(f"Invalid mode: {mode}. Mode must be either 'dynamic' or 'fixed'.")
            raise ValueError("Mode must be either 'dynamic' or 'fixed'.")
        if not isinstance(node, Node):
            global_logger.error("Node must be an instance of Node class.")
            raise TypeError("Node must be an instance of Node class.")
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
            global_logger.error(f"{self.node.ID} must have at least one supplier.")
            raise ValueError(f"{self.node.ID} must have at least one supplier.")

    def _active_suppliers(self):
        """
        Return the subset of ``self.node.suppliers`` whose transport link is
        currently active. If every link is disrupted, fall back to the full
        supplier list so subclasses always have a non-empty candidate set —
        the dispatch gate in ``process_order`` will then block the inactive
        choice and the policy will retry on the next replenishment trigger.

        Returns:
            list: Active suppliers (``Link`` objects), or all suppliers if none are active.
        """
        active = [s for s in self.node.suppliers if s.status == "active"]
        return active if active else self.node.suppliers

    def _apply_mode(self, selected):
        """
        Apply the fixed / dynamic mode semantics to a dynamically chosen supplier.

        In ``"fixed"`` mode the first selection is locked for all subsequent
        calls, but if the locked supplier's link is currently inactive the
        policy temporarily routes around it (returning ``selected`` for this
        call without changing the lock) — "fixed" means *prefer this one*,
        not *stop shipping if it's down*. The lock is restored as soon as
        the supplier's link recovers.

        Parameters:
            selected (Link): The supplier chosen by the subclass's selection logic.

        Returns:
            Link: ``self.fixed_supplier`` in fixed mode (or ``selected`` if the lock is inactive); ``selected`` in dynamic mode.
        """
        if self.mode == "fixed":
            if self.fixed_supplier is None:
                self.fixed_supplier = selected
            if self.fixed_supplier.status == "inactive":
                return selected
            return self.fixed_supplier
        return selected

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
    _info_keys = SupplierSelectionPolicy._info_keys + ["name"]

    def __init__(self, node, mode="fixed"):
        """
        Initialize the supplier selection policy object.

        Parameters:
            node (object): Node to which this supplier selection policy applies.
            mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "fixed").

        Attributes:
            name (str): Name of the selection policy.
            _info_keys (list): List of keys to include in the info dictionary.

        Returns:
            None
        """
        super().__init__(node, mode)
        self.name = "First fixed supplier"

    def select(self, order_quantity):
        """
        Selects the first supplier whose transport link is currently active.

        Disrupted links are filtered out; if every link is inactive, the policy
        falls back to the first supplier in the list (the dispatch gate in
        ``process_order`` then blocks it and the policy retries on the next
        replenishment trigger).

        In dynamic mode, the selection is evaluated for each order.
        In fixed mode, the first active supplier is locked for all subsequent
        selections. If the locked link later goes inactive, the policy
        temporarily routes around it without changing the lock.

        Parameters:
            order_quantity (float): The quantity to order.

        Returns:
            object: The selected supplier.
        """
        self.validate_suppliers()
        candidates = self._active_suppliers()
        selected = candidates[0]
        return self._apply_mode(selected)

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
    _info_keys = SupplierSelectionPolicy._info_keys + ["name"]

    def __init__(self, node, mode="dynamic"):
        """
        Initialize the supplier selection policy object.

        Parameters:
            node (object): Node to which this supplier selection policy applies.
            mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

        Attributes:
            name (str): Name of the selection policy.
            _info_keys (list): List of keys to include in the info dictionary.

        Returns:
            None
        """
        super().__init__(node, mode)
        self.name = "First available supplier"

    def select(self, order_quantity):
        """
        Selects the first active supplier with sufficient available inventory.

        Disrupted links are filtered out first. Among the active candidates the
        first one whose upstream inventory can cover ``order_quantity`` is
        chosen; if none can, the policy falls back to the first active
        candidate (inventory shortage is then recorded by ``process_order`` as
        a supplier backorder). If every link is inactive, falls back to the
        first supplier in the list — the dispatch gate will block it.

        In fixed mode, the first selection is locked for all subsequent orders.
        If the locked link later goes inactive, the policy temporarily routes
        around it without changing the lock.

        Parameters:
            order_quantity (float): The quantity to order.

        Returns:
            object: The selected supplier.
        """
        self.validate_suppliers()
        candidates = self._active_suppliers()
        available = [s for s in candidates if s.available_quantity() >= order_quantity]
        selected = available[0] if available else candidates[0]
        return self._apply_mode(selected)

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
    _info_keys = SupplierSelectionPolicy._info_keys + ["name"]

    def __init__(self, node, mode="dynamic"):
        """
        Initialize the supplier selection policy object.

        Parameters:
            node (object): Node to which this supplier selection policy applies.
            mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

        Attributes:
            name (str): Name of the selection policy.
            _info_keys (list): List of keys to include in the info dictionary.

        Returns:
            None
        """
        super().__init__(node, mode)
        self.name = "Cheapest supplier (Transportation cost)"

    def select(self, order_quantity):
        """
        Selects the active supplier with the lowest transportation cost.

        Disrupted links are filtered out first; if every link is inactive,
        the policy falls back to the cheapest among all suppliers (the dispatch
        gate in ``process_order`` will block it and the policy retries on the
        next trigger).

        In fixed mode, the first selection is locked for all subsequent orders.
        If the locked link later goes inactive, the policy temporarily routes
        around it without changing the lock.

        Parameters:
            order_quantity (float): The quantity to order.

        Returns:
            object: The selected supplier.
        """
        self.validate_suppliers()
        candidates = self._active_suppliers()
        selected = min(candidates, key=lambda s: s.cost)
        return self._apply_mode(selected)

class SelectFastest(SupplierSelectionPolicy):
    """
    Selects the supplier with the shortest lead time to deliver the product.

    The selection is based on minimizing lead time among all connected suppliers.
    Supports both dynamic selection (evaluated at each order event) and fixed selection (locks the first 
    selected supplier for all subsequent orders).

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
    _info_keys = SupplierSelectionPolicy._info_keys + ["name"]

    def __init__(self, node, mode="dynamic"):
        """
        Initialize the supplier selection policy object.

        Parameters:
            node (object): Node to which this supplier selection policy applies.
            mode (str, optional): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

        Attributes:
            name (str): Name of the selection policy.
            _info_keys (list): List of keys to include in the info dictionary.

        Returns:
            None
        """
        super().__init__(node, mode)
        self.name = "Fastest supplier (Lead time)"

    def select(self, order_quantity):
        """
        Selects the active supplier with the shortest lead time.

        Disrupted links are filtered out first; if every link is inactive,
        the policy falls back to the fastest among all suppliers (the dispatch
        gate in ``process_order`` will block it and the policy retries on the
        next trigger).

        In fixed mode, the first selection is locked for all subsequent orders.
        If the locked link later goes inactive, the policy temporarily routes
        around it without changing the lock.

        Parameters:
            order_quantity (float): The quantity to order.

        Returns:
            object: The selected supplier.
        """
        self.validate_suppliers()
        candidates = self._active_suppliers()
        selected = min(candidates, key=lambda s: s.lead_time())
        return self._apply_mode(selected)

class Node(NamedEntity, InfoMixin):
    """
    Represents a node in the supply network, such as a supplier, manufacturer, warehouse, distributor, retailer, or demand point.
    Supports automatic disruption and recovery, dynamic logging, and performance tracking.

    Each node can experience disruptions either probabilistically or based on custom-defined disruption and recovery times.
    During disruptions, the node becomes inactive and resumes operations after the specified recovery period.
    Tracks key performance metrics like transportation costs, node-specific costs, profit and net profit, products sold, 
    demand placed, and shortages.

    Supports integration with inbuilt replenishment policies: SS, RQ, Periodic and any custom policy created by extending 
    the `ReplenishmentPolicy` class.

    Supplier selection policies: Available, Cheapest, Fastest and any custom policy created by extending the 
    `SupplierSelectionPolicy` class.

    Supported node types: "infinite_supplier", "supplier", "manufacturer", "factory", "warehouse", "distributor", 
    "retailer", "store", "demand"

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
        _info_keys (list): List of keys to include in the info dictionary.
        env (simpy.Environment): simulation environment
        ID (str): ID of the node (alphanumeric)
        name (str): name of the node
        node_type (str): type of the node
        node_failure_p (float): node failure probability
        node_status (str): status of the node (active/inactive)
        node_disrupt_time (callable): function to model node disruption time
        node_recovery_time (callable): function to model node recovery time
        logger (GlobalLogger): logger object
        suppliers (list): inbound ``Link`` objects whose ``sink`` is this node; populated by ``Link.__init__`` via ``add_supplier_link``.

    Functions:
        __init__: Initializes the node object, validates parameters, and sets up logging and self-disruption if needed.
        disruption: Simulates node disruption and automatic recovery over time.
        add_supplier_link: Register an inbound Link with this node (called by Link.__init__).
        position: Backorder-aware inventory position used by replenishment policies.
        place_order: Pick a supplier via the selection policy and spawn the dispatch process.
        wait_for_drop: Generator; block on ``inventory_drop`` and rotate the event.
    """
    _info_keys = ["ID", "name", "node_type", "failure_p", "node_status", "logging"]

    def __init__(self, env: simpy.Environment,
                 ID: str,
                 name: str,
                 node_type: str,
                 failure_p:float = 0.0,
                 node_disrupt_time: Callable = None,
                 node_recovery_time: Callable = lambda: 1,
                 logging: bool = True,
                 rng: random.Random = None,
                 **kwargs) -> None:
        """
        Initialize the node object.
        
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
            _info_keys (list): List of keys to include in the info dictionary.  
            env (simpy.Environment): simulation environment
            ID (str): ID of the node (alphanumeric)
            name (str): name of the node
            node_type (str): type of the node
            node_failure_p (float): node failure probability
            node_status (str): status of the node (active/inactive)
            node_disrupt_time (callable): function to model node disruption time
            node_recovery_time (callable): function to model node recovery time
            logger (GlobalLogger): logger object

        Returns:
            None
        """
        if not isinstance(env, simpy.Environment):
            raise ValueError("Invalid environment. Provide a valid SimPy environment.")
        # Validate node_type via the NodeType enum — single source of truth
        # shared with create_sc_net. Accepts either a string (case-insensitive)
        # or a NodeType member. Stored as the normalized lowercase string so
        # every existing equality check against a literal (``== "demand"``,
        # ``"supplier" in node.node_type``) continues to work.
        try:
            node_type = NodeType(node_type).value
        except ValueError:
            global_logger.error(f"Invalid node type. Node type: {node_type}")
            raise ValueError(f"Invalid node type: {node_type}.")
        # ``ensure_numeric_callable`` does the auto-wrap and validates the
        # returned value is numeric on a single test invocation. This catches
        # the §6.4 footgun where ``not callable(x)`` would skip the wrap for
        # any callable — including a class like ``int`` or a generator
        # function — leaving ``x()`` to crash deep inside a SimPy process.
        node_recovery_time = ensure_numeric_callable("node_recovery_time", node_recovery_time)
        if node_disrupt_time is not None:
            node_disrupt_time = ensure_numeric_callable("node_disrupt_time", node_disrupt_time)
        self.env = env  # simulation environment
        self.ID = ID  # ID of the node (alphanumeric)
        self.name = name  # name of the node
        self.node_type = node_type  # type of the node (supplier, manufacturer, warehouse, distributor, retailer, demand)
        self.node_failure_p = failure_p  # node failure probability
        self.node_status = "active"  # node status (active/inactive)
        self.node_disrupt_time = node_disrupt_time  # callable function to model node disruption time
        self.node_recovery_time = node_recovery_time  # callable function to model node recovery time
        self.rng = rng if rng is not None else _rng  # RNG for probabilistic disruption; falls back to library default
        self.suppliers = []  # inbound Link registry; populated by Link.__init__ via Node.add_supplier_link

        logger_name = self.ID # default logger name is the node ID
        if 'logger_name' in kwargs:
            logger_name = kwargs.pop('logger_name')
        # Per-node loggers live as children of the library root ``"sim_trace"``
        # so their records propagate up to the single set of handlers configured
        # on ``global_logger``. This avoids each Node opening its own
        # FileHandler on ``simulation_trace.log`` (which used to truncate the
        # file once per node at construction). Users who pass a custom
        # ``logger_name`` get the prefix added automatically; if they already
        # supplied the prefix we don't double it.
        if not logger_name.startswith("sim_trace."):
            logger_name = f"sim_trace.{logger_name}"
        # Only forward kwargs that GlobalLogger actually accepts; ignore the rest
        # so unrelated keys (e.g. record_inv_levels, shelf_life) don't raise TypeError.
        logger_kwargs = {k: kwargs[k] for k in kwargs if k in _LOGGER_KWARGS}
        self.logger = GlobalLogger(logger_name=logger_name, **logger_kwargs)  # create a logger
        # Do NOT call enable_logging() here — the per-node logger inherits its
        # handlers from ``global_logger`` via propagation. The historical call
        # site re-attached a FileHandler in mode='w' on every Node, which
        # truncated the trace file N times during network construction (§4.8).
        if not logging:
            self.logger.disable_logging()  # mute this node specifically

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
        # TODO: interrupt all ongoing processes spawned by this node on disruption, and resume them after recovery.
        while True:
            if(self.node_status=="active"):
                if(self.node_disrupt_time): # if node_disrupt_time is provided, wait for the disruption time
                    disrupt_time = self.node_disrupt_time() # get the disruption time
                    validate_positive(name="node_disrupt_time", value=disrupt_time) # check if disrupt_time is positive
                    yield self.env.timeout(disrupt_time)
                    self.node_status = "inactive" # change the node status to inactive
                    self.logger.info(f"{self.env.now}:{self.ID}: Node disrupted.")
                elif(self.rng.random() < self.node_failure_p):
                    self.node_status = "inactive"
                    self.logger.info(f"{self.env.now}:{self.ID}: Node disrupted.")
                    yield self.env.timeout(1)
            else:
                recovery_time = self.node_recovery_time() # get the recovery time
                validate_positive(name="node_recovery_time", value=recovery_time) # check if disrupt_time is positive
                yield self.env.timeout(recovery_time)
                self.node_status = "active"
                self.logger.info(f"{self.env.now}:{self.ID}: Node recovered from disruption.")

    def add_supplier_link(self, link) -> None:
        """
        Register an inbound transport link whose ``sink`` is this node.

        This is the one supported entry point for attaching a Link to a Node.
        Supplier-selection policies iterate over ``node.suppliers`` to choose
        where to dispatch a replenishment order, so a Link must be registered
        here for the node to route orders over it.

        ``Link.__init__`` calls this automatically for its ``sink`` — users of
        the direct-instantiation API do not need to call it themselves.
        It is also safe to call explicitly if a Link is constructed separately
        from its sink and then attached later.

        Parameters:
            link (Link): The Link object whose ``sink`` is this node.

        Raises:
            TypeError: If ``link`` is not a Link instance.
            ValueError: If ``link.sink`` is not this node.

        Returns:
            None
        """
        if not isinstance(link, Link):
            global_logger.error("add_supplier_link expects a Link instance.")
            raise TypeError("add_supplier_link expects a Link instance.")
        if link.sink is not self:
            global_logger.error(
                f"{self.ID}: add_supplier_link called with a link whose sink is "
                f"{link.sink.ID}, not {self.ID}."
            )
            raise ValueError("link.sink must match the node add_supplier_link is called on.")
        self.suppliers.append(link)

    # ---- Replenishment-policy contract -------------------------------------
    # The three methods below form the public contract that replenishment
    # policies (SSReplenishment, RQReplenishment, PeriodicReplenishment, and
    # any user-defined subclass of InventoryReplenishment) are expected to
    # speak in terms of. They hide the `inventory.on_hand`, `stats.backorder`,
    # `selection_policy`, `process_order`, and `inventory_drop` internals so a
    # policy does not need privileged knowledge of the node's layout. Only
    # nodes that own replenishment plumbing (currently ``InventoryNode`` and
    # ``Manufacturer``) are expected to call ``place_order`` and
    # ``wait_for_drop``; ``position`` additionally works on ``Supplier`` since
    # it has both ``inventory`` and ``stats``.
    def position(self) -> float:
        """
        Backorder-aware inventory position used by replenishment policies.

        Returns ``inventory.on_hand - stats.backorder[1]`` — i.e. the current
        physical plus in-transit stock, minus units already committed to
        customer backorders. Replenishment policies use this single value in
        place of reaching into ``node.inventory.on_hand`` and
        ``node.stats.backorder[1]`` independently, so the arithmetic stays in
        one place.

        Returns:
            float: The backorder-aware inventory position.
        """
        return self.inventory.on_hand - self.stats.backorder[1]

    def place_order(self, quantity) -> None:
        """
        Pick a supplier via this node's selection policy and spawn ``process_order``.

        Wraps the "choose supplier, then ``env.process(process_order(...))``"
        idiom so replenishment policies can express a dispatch as a single
        call instead of reaching into ``selection_policy.select`` and
        ``process_order`` independently. The spawned SimPy process handles
        the capacity clamp, link-disruption gate, and supplier-side
        bookkeeping; this method does not yield.

        Parameters:
            quantity (float): Quantity to order (pre-clamp; the downstream
                ``process_order`` may still reduce it to fit capacity or
                skip the dispatch if the link is disrupted).

        Returns:
            None
        """
        supplier = self.selection_policy.select(quantity)
        self.env.process(self.process_order(supplier, quantity))

    def wait_for_drop(self):
        """
        Generator: block until the inventory-drop event fires, then rotate it.

        Replenishment policies use ``yield from node.wait_for_drop()`` in
        place of manually yielding on ``self.node.inventory_drop`` and
        reassigning a fresh event afterwards. Rotating the event inside this
        helper keeps the "yield then reset" pattern in exactly one place.

        Yields:
            simpy.Event: The current ``inventory_drop`` event; on wake-up the
            slot is replaced with a fresh ``env.event()``.
        """
        yield self.inventory_drop
        self.inventory_drop = self.env.event()

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
        env (simpy.Environment): Simulation environment.
        ID (str): ID of the link.
        source (Node): Source node.
        sink (Node): Sink node.
        cost (float): Transportation cost.
        lead_time (callable): Function for stochastic lead time.
        link_failure_p (float): Failure probability.
        status (str): Current status of the link ("active" or "inactive").
        link_disrupt_time (callable): Disruption time function.
        link_recovery_time (callable): Recovery time function.

    Functions:
        __init__: Initializes the link object and validates parameters.
        disruption: Simulates link disruption and automatic recovery.
    """
    _info_keys = ["ID", "source", "sink", "cost", "lead_time", "link_failure_p"]
    _stats_keys = ["status"]

    def __init__(self, env: simpy.Environment,
                 ID: str,
                 source: Node,
                 sink: Node,
                 cost: float, # transportation cost
                 lead_time: Callable,
                 link_failure_p: float = 0.0,
                 link_disrupt_time: Callable = None,
                 link_recovery_time: Callable = lambda: 1,
                 rng: random.Random = None) -> None:
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
        if not isinstance(env, simpy.Environment):
            raise ValueError("Invalid environment. Provide a valid SimPy environment.")
        if not isinstance(source, Node) or not isinstance(sink, Node):
            raise ValueError("Invalid source or sink node. Provide valid Node instances.")
        if lead_time is None:
            global_logger.error("Lead time cannot be None. Provide a function to model stochastic lead time.")
            raise ValueError("Lead time cannot be None. Provide a function to model stochastic lead time.")
        lead_time = ensure_numeric_callable("lead_time", lead_time)
        if(source == sink):
            global_logger.error("Source and sink nodes cannot be the same.")
            raise ValueError("Source and sink nodes cannot be the same.")
        if(source.node_type == "demand"):
            global_logger.error("Demand node cannot be a source node.")
            raise ValueError("Demand node cannot be a source node.")
        if("supplier" in sink.node_type):
            global_logger.error("Supplier node cannot be a sink node.")
            raise ValueError("Supplier node cannot be a sink node.")
        if("supplier" in source.node_type and "supplier" in sink.node_type):
            global_logger.error("Supplier nodes cannot be connected.")
            raise ValueError("Supplier nodes cannot be connected.")
        if("supplier" in source.node_type and sink.node_type == "demand"):
            global_logger.error("Supplier node cannot be connected to a demand node.")
            raise ValueError("Supplier node cannot be connected to a demand node.")
        validate_non_negative("Cost", cost)
        if (link_disrupt_time is not None):
            link_disrupt_time = ensure_numeric_callable("link_disrupt_time", link_disrupt_time)
        if (link_recovery_time is not None):
            link_recovery_time = ensure_numeric_callable("link_recovery_time", link_recovery_time)

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
        self.rng = rng if rng is not None else _rng  # RNG for probabilistic disruption; falls back to library default

        # Auto-register with the sink via the public method instead of mutating
        # sink.suppliers directly. Every Node initialises ``suppliers = []`` in
        # its __init__, so this works for any valid sink — including a plain
        # Node or a Demand — rather than depending on the sink having its own
        # suppliers-list setup.
        self.sink.add_supplier_link(self)
        if(self.link_failure_p>0 or self.link_disrupt_time): # disrupt the link if link_failure_p > 0
            self.env.process(self.disruption())
    
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
        # Ongoing shipments already dispatched over this link are intentionally
        # not interrupted when the link goes inactive — only *new* orders are
        # blocked (see the link-status check in InventoryNode.process_order and
        # Manufacturer.process_order_raw). Interrupting in-transit shipments
        # would require tracking them as individual processes; deferred.
        while True:
            if(self.status=="active"):
                if(self.link_disrupt_time): # if link_disrupt_time is provided, wait for the disruption time
                    disrupt_time = self.link_disrupt_time() # get the disruption time
                    validate_positive(name="link_disrupt_time", value=disrupt_time) # check if disrupt_time is positive
                    yield self.env.timeout(disrupt_time)
                    self.status = "inactive" # change the link status to inactive
                    global_logger.info(f"{self.env.now}:{self.ID}: Link disrupted.")
                elif(self.rng.random() < self.link_failure_p):
                    self.status = "inactive"
                    global_logger.info(f"{self.env.now}:{self.ID}: Link disrupted.")
                    yield self.env.timeout(1)
            else:
                recovery_time = self.link_recovery_time() # get the recovery time
                validate_positive(name="link_recovery_time", value=recovery_time) # check if disrupt_time is positive
                yield self.env.timeout(recovery_time)
                self.status = "active"
                global_logger.info(f"{self.env.now}:{self.ID}: Link recovered from disruption.")

    def available_quantity(self) -> float:
        """
        Amount of the upstream source's inventory currently available over this link.

        Exposed so supplier-selection policies (e.g. ``SelectAvailable``) can
        compare candidate links without reaching into ``link.source.inventory.level``.

        Returns:
            float: The source node's current inventory level.
        """
        return self.source.inventory.level

class Inventory(NamedEntity, InfoMixin):
    """
    The Inventory class models stock management within a node in the supply network. 
    It supports both perishable and non-perishable items, enforces capacity limits, 
    tracks on-hand levels, and notifies replenishment policy whenever inventory levels drops.
    For perishable inventories, it manages product shelf life and automatically removes expired items. 
    The class also records inventory levels and calculates carrying costs over time.

    Parameters:
        env (simpy.Environment): Simulation environment.
        capacity (float): Maximum capacity of the inventory.
        initial_level (float): Initial inventory level.
        node (Node): Node to which this inventory belongs.
        replenishment_policy (InventoryReplenishment): Replenishment policy for the inventory.
        holding_cost (float): Holding cost per unit per time period.
        shelf_life (float): Shelf life for perishable items.
        inv_type (str): Type of the inventory, either "non-perishable" or "perishable".
        record_inv_levels (bool): Flag to enable recording of inventory levels over time.

    Attributes:
        _info_keys (list): Keys included in the information dictionary.
        _stats_keys (list): Keys included in the statistics dictionary.
        env (simpy.Environment): Simulation environment.
        capacity (float): Maximum inventory capacity.
        init_level (float): Initial inventory level.
        level (float): Current inventory level.
        on_hand (float): Current on-hand inventory.
        inv_type (str): Inventory type ("non-perishable" or "perishable").
        holding_cost (float): Holding cost per unit.
        carry_cost (float): Total accumulated carrying cost.
        replenishment_policy (InventoryReplenishment): Inventory replenishment policy.
        inventory (simpy.Container): SimPy container managing inventory levels.
        last_update_t (float): Last timestamp when carrying cost was updated.
        shelf_life (float): Shelf life of perishable items (if applicable).
        perish_queue (list): ``heapq`` min-heap of perishable batches as ``(manufacturing_date, quantity)`` tuples. Index 0 is always the oldest batch (earliest to expire); ``put`` uses ``heapq.heappush`` and ``get`` / ``remove_expired`` use ``heapq.heappop``.
        perish_changed (simpy.Event): Wake-up signal for the ``remove_expired`` daemon. ``put`` succeeds it when an inserted batch displaces the heap head (or arrives into an empty queue), so the daemon recomputes the next expiry instead of polling. Rotated on each wake-up.
        waste (float): Total quantity of expired items.
        instantaneous_levels (list): Recorded inventory levels over time.

    Functions:
        __init__: Initializes the inventory object.
        record_inventory_levels: Records inventory levels at regular time intervals.
        put: Adds items to the inventory, handling perishable item tracking.
        get: Removes items from inventory, using FIFO for perishables.
        remove_expired: Automatically removes expired items from perishable inventory.
        update_carry_cost: Updates carrying cost based on inventory level and holding time.
    """
    _info_keys = ["capacity", "initial_level", "replenishment_policy", "holding_cost", "shelf_life", "inv_type"]
    _stats_keys = ["level", "carry_cost", "instantaneous_levels"]

    def __init__(self,
                 env: simpy.Environment, 
                 capacity: float, 
                 initial_level: float, 
                 node: Node,
                 replenishment_policy: InventoryReplenishment,
                 holding_cost: float = 0.0,
                 shelf_life: float = 0,
                 inv_type: str = "non-perishable",
                 record_inv_levels = False) -> None:
        """
        Initialize the Inventory object.
        
        Parameters:
            env (simpy.Environment): Simulation environment.
            capacity (float): Maximum capacity of the inventory.
            initial_level (float): Initial inventory level.
            node (Node): Node to which this inventory belongs.
            replenishment_policy (InventoryReplenishment): Replenishment policy for the inventory.
            holding_cost (float): Holding cost per unit per time period.
            shelf_life (float): Shelf life for perishable items.
            inv_type (str): Type of the inventory, either "non-perishable" or "perishable".

        Attributes:
            _info_keys (list): Keys included in the information dictionary.
            _stats_keys (list): Keys included in the statistics dictionary.
            env (simpy.Environment): Simulation environment.
            capacity (float): Maximum inventory capacity.
            init_level (float): Initial inventory level.
            level (float): Current inventory level.
            on_hand (float): Current on-hand inventory.
            inv_type (str): Inventory type ("non-perishable" or "perishable").
            holding_cost (float): Holding cost per unit.
            carry_cost (float): Total accumulated carrying cost.
            replenishment_policy (InventoryReplenishment): Inventory replenishment policy.
            inventory (simpy.Container): SimPy container managing inventory levels.
            last_update_t (float): Last timestamp when carrying cost was updated.
            shelf_life (float): Shelf life of perishable items (if applicable).
            perish_queue (list): ``heapq`` min-heap of perishable batches as ``(manufacturing_date, quantity)`` tuples. Index 0 is always the oldest batch (earliest to expire); ``put`` uses ``heapq.heappush`` and ``get`` / ``remove_expired`` use ``heapq.heappop``.
            waste (float): Total quantity of expired items.
            instantaneous_levels (list): Recorded inventory levels over time.

        Returns:
            None
        """
        if not isinstance(node, Node):
            global_logger.error("Node must be an instance of Node class.")
            raise TypeError("Node must be an instance of Node class.")
        self.node = node # node to which this inventory belongs
        if initial_level > capacity:
            self.node.logger.error("Initial level cannot be greater than capacity.")
            raise ValueError("Initial level cannot be greater than capacity.")
        if replenishment_policy is not None:
            if not issubclass(replenishment_policy.__class__, InventoryReplenishment):
                self.node.logger.error(f"{type(replenishment_policy).__name__} must inherit from InventoryReplenishment")
                raise TypeError(f"{type(replenishment_policy).__name__} must inherit from InventoryReplenishment")
        if inv_type not in ["non-perishable", "perishable"]:
            self.node.logger.error(f"Invalid inventory type. {inv_type} is not yet available.")
            raise ValueError(f"Invalid inventory type. {inv_type} is not yet available.")
        validate_positive("Capacity", capacity)
        validate_non_negative("Initial level", initial_level)
        validate_non_negative("Inventory holding cost",holding_cost)
        validate_non_negative("Shelf life", shelf_life)
        self.env = env
        self.init_level = initial_level
        self.on_hand = initial_level # current inventory level
        self.inv_type = inv_type
        self.holding_cost = holding_cost
        self.carry_cost = 0 # initial carrying cost based on the initial inventory level
        self.replenishment_policy = replenishment_policy
        self.inventory = simpy.Container(env=self.env, capacity=capacity, init=self.init_level) # Inventory container setup
        self.last_update_t = self.env.now # last time the carrying cost was updated
        
        if self.inv_type == "perishable":
            validate_positive("Shelf life", shelf_life)
            self.shelf_life = shelf_life
            self.perish_queue = [(0, initial_level)]
            self.waste = 0
            # Event-driven wake-up for ``remove_expired``. ``put`` succeeds this
            # event when an inserted batch displaces the heap head (so the next
            # expiry moves earlier), and the daemon rotates a fresh event in on
            # wake-up — same idiom as ``Node.wait_for_drop``.
            self.perish_changed = self.env.event()
            self.env.process(self.remove_expired())

        self.instantaneous_levels = []
        if record_inv_levels:
            self.env.process(self.record_inventory_levels())  # record inventory levels at regular intervals

    @property
    def level(self):
        """Current inventory level, delegating to the underlying SimPy container."""
        return self.inventory.level

    @property
    def capacity(self):
        """Inventory capacity, delegating to the underlying SimPy container."""
        return self.inventory.capacity

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

    def put(self, amount: float, manufacturing_date: float = None):
        """
        Add items to inventory. For perishable items, tracks manufacturing date.

        Parameters:
            amount (float): amount to add
            manufacturing_date (float): only required for perishable inventories

        Returns:
            float: the amount actually accepted into inventory. May be less than
                the requested ``amount`` when the inventory is at/near capacity, and
                0 when the inventory is infinite, already full, or ``amount <= 0``.
                Callers that track ``on_hand`` must reconcile any shortfall
                (``requested - accepted``) against their bookkeeping.
        """
        if self.inventory.level == float('inf') or amount <= 0 or self.inventory.level == self.capacity:
            return 0

        if amount + self.inventory.level > self.capacity: # adjust amount if it exceeds capacity
            old_amount = amount
            amount = self.capacity - self.inventory.level
            self.node.logger.warning(f"Inventory capacity exceeded. Only {amount} of {old_amount} units added to inventory.")

        if self.inv_type == "perishable":
            if manufacturing_date is None:
                self.node.logger.error("Manufacturing date must be provided for perishable inventory.")
                raise ValueError("Manufacturing date must be provided for perishable inventory.")
            # ``perish_queue`` is a min-heap keyed by manufacturing date — the
            # oldest (earliest-to-expire) batch is always at index 0. heappush
            # is O(log n); the previous manual sorted-insert was O(n).
            new_batch = (manufacturing_date, amount)
            heapq.heappush(self.perish_queue, new_batch)
            # Wake the ``remove_expired`` daemon only when this push moves the
            # head — i.e. an empty→non-empty transition or an older batch that
            # displaces the prior head. With monotonic mfg_dates (the common
            # case) the head changes only on the empty→non-empty transition,
            # so the daemon is undisturbed for routine restocks.
            if self.perish_queue[0] is new_batch and not self.perish_changed.triggered:
                self.perish_changed.succeed()
        self.update_carry_cost()  # Update carrying cost based on the amount added
        self.inventory.put(amount)
        if(not self.node.inventory_raised.triggered):
            self.node.inventory_raised.succeed()  # signal that inventory has been raised
        return amount

    def get(self, amount: float):
        """
        Remove items from inventory. For perishable items, oldest products are removed first.

        Parameters:
            amount (float): amount to remove

        Returns:
            tuple: (SimPy get event, List of (manufacture_date, quantity)) for perishable items
        """
        if self.inventory.level == float('inf'):
            return self.inventory.get(amount), []

        man_date_ls = []
        if self.inv_type == "perishable":
            x_amount = amount
            while x_amount > 0 and self.perish_queue:
                mfg_date, qty = self.perish_queue[0]  # peek at the oldest batch
                if qty <= x_amount:
                    man_date_ls.append((mfg_date, qty))
                    x_amount -= qty
                    heapq.heappop(self.perish_queue)  # O(log n) — was pop(0): O(n)
                else:
                    man_date_ls.append((mfg_date, x_amount))
                    # Partial consumption: replace the head with the same
                    # mfg_date and a smaller qty. Heap invariant is preserved
                    # because (mfg_date, qty - x_amount) <= (mfg_date, qty),
                    # which was already the smallest tuple in the heap.
                    self.perish_queue[0] = (mfg_date, qty - x_amount)
                    x_amount = 0
        self.update_carry_cost()
        get_event = self.inventory.get(amount)
        self.on_hand -= amount  # Update the on-hand inventory level
        if(self.replenishment_policy):
            if(not self.node.inventory_drop.triggered):
                self.node.inventory_drop.succeed()  # signal that inventory has been dropped
        return get_event, man_date_ls

    def remove_expired(self):
        """
        Remove expired items from perishable inventory.

        Event-driven: sleeps until the head batch's expiry rather than polling
        every simulation tick. Wakes early via ``perish_changed`` when ``put``
        inserts a batch that displaces the heap head (or arrives into an empty
        queue), so a fresher head with an earlier expiry is honoured without
        waiting for the previous timer to elapse. The rotation-event idiom
        (``self.perish_changed = self.env.event()`` after each wake) mirrors
        ``Node.wait_for_drop`` and avoids re-firing on a stale event.
        """
        while True:
            if not self.perish_queue:
                # Nothing to expire — block until the next put signals a head.
                yield self.perish_changed
                self.perish_changed = self.env.event()
                continue
            # ``perish_queue`` is a min-heap by mfg_date: the oldest batch is
            # at index 0, so a single peek is enough to compute the next
            # expiry deadline. ``max(0, ...)`` guards against stale batches
            # whose deadline has already passed (e.g. backdated mfg_date).
            next_expiry = self.perish_queue[0][0] + self.shelf_life
            sleep_dt = max(0, next_expiry - self.env.now)
            timer = self.env.timeout(sleep_dt)
            result = yield timer | self.perish_changed
            if self.perish_changed in result:
                # The head moved earlier (older batch arrived, or queue went
                # empty→non-empty). Rotate the event and recompute from the
                # new head — even if the timer also fired, the next iteration
                # will see sleep_dt == 0 and drain on the spot.
                self.perish_changed = self.env.event()
                continue
            # Timer fired — drain everything now expired. ``self.get(qty)``
            # does the heappop on the consumed batch (or the partial-
            # consumption update on the head), so the explicit heappop here
            # only handles the rare qty == 0 sentinel left over from prior
            # partial consumption.
            while self.perish_queue and self.env.now - self.perish_queue[0][0] >= self.shelf_life:
                mfg_date, qty = self.perish_queue[0]  # peek at oldest batch
                if qty > 0:
                    get_event, _ = self.get(qty) # get/remove expired items from the inventory
                    yield get_event
                    self.waste += qty  # update waste statistics
                    self.node.logger.info(f"{self.env.now:.4f}: {qty} units expired (Mgf date:{mfg_date}).")
                else:
                    heapq.heappop(self.perish_queue)

    def update_carry_cost(self):
        """
        Update the carrying cost of the inventory based on the current level and holding cost.
        """
        carry_period = self.env.now - self.last_update_t
        self.carry_cost += self.inventory.level * (carry_period) * self.holding_cost  # update the carrying cost based on the current inventory level
        self.last_update_t = self.env.now  # update the last update time

class Supplier(Node):
    """
    The `Supplier` class represents a supplier in the supply network that continuously 
    extracts raw materials whenever the inventory is not full. Each supplier is associated 
    with a specific raw material and can have either finite or infinite inventory capacity.

    For finite suppliers, raw materials are extracted in batches based on the extraction 
    quantity and extraction time specified by the instance of `RawMaterial` class. For infinite suppliers, 
    inventory is considered unlimited.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): unique identifier for the supplier
        name (str): name of the supplier
        node_type (str): type of the node (supplier/infinite_supplier)
        capacity (float): maximum capacity of the inventory
        initial_level (float): initial inventory level
        inventory_holding_cost (float): inventory holding cost
        raw_material (RawMaterial): raw material supplied by the supplier
        **kwargs: any additional keyword arguments for the Node class and logger

    Attributes:
        _info_keys (list): list of keys to include in the info dictionary.
        raw_material (RawMaterial): raw material supplied by the supplier
        sell_price (float): selling price of the raw material
        inventory (Inventory): inventory of the supplier
        inventory_drop (simpy.Event): event to signal when inventory is dropped
        inventory_raised (simpy.Event): event to signal when inventory is raised
        stats (Statistics): statistics object for the supplier

    Functions:
        __init__: Initializes the supplier object.
        behavior: Simulates the continuous raw material extraction process.
    """
    _info_keys = Node._info_keys + ["raw_material", "sell_price"]

    def __init__(self,
                 env: simpy.Environment,
                 ID: str,
                 name: str,
                 node_type: str = "supplier",
                 capacity: float = 0.0,
                 initial_level: float = 0.0,
                 inventory_holding_cost:float = 0.0,
                 raw_material: RawMaterial = None,
                 **kwargs) -> None:
        """
        Initialize the supplier object.
        
        Parameters:
            env (simpy.Environment): simulation environment
            ID (str): unique identifier for the supplier
            name (str): name of the supplier
            node_type (str): type of the node (supplier/infinite_supplier)
            capacity (float): maximum capacity of the inventory
            initial_level (float): initial inventory level
            inventory_holding_cost (float): inventory holding cost
            raw_material (RawMaterial): raw material supplied by the supplier
            **kwargs: any additional keyword arguments for the Node class and logger
        
        Attributes:
            _info_keys (list): list of keys to include in the info dictionary.
            raw_material (RawMaterial): raw material supplied by the supplier
            sell_price (float): selling price of the raw material
            inventory (Inventory): inventory of the supplier
            inventory_drop (simpy.Event): event to signal when inventory is dropped
            inventory_raised (simpy.Event): event to signal when inventory is raised
            stats (Statistics): statistics object for the supplier

        Returns:
            None
        """
        # Pull periodic-stats kwargs out before forwarding to Node — Statistics
        # owns this knob, but exposing it as a node-level kwarg lets users tune
        # the periodic update cadence without subclassing. Suppliers default to
        # no periodic update (current behavior); if the user opts in, the
        # cadence is configurable.
        periodic_stats = kwargs.pop('periodic_stats', False)
        stats_period = kwargs.pop('stats_period', 1)
        if periodic_stats:
            validate_positive(name="stats_period", value=stats_period)
        super().__init__(env=env,ID=ID,name=name,node_type=node_type,**kwargs)
        self.raw_material = raw_material # raw material supplied by the supplier
        self.sell_price = 0
        if(self.raw_material):
            self.sell_price = self.raw_material.cost # selling price of the raw material
        if(self.node_type!="infinite_supplier"):
            inventory_kwargs = {k: v for k, v in kwargs.items() if k not in _LOGGER_KWARGS and k not in _NODE_KWARGS}
            self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, node=self, holding_cost=inventory_holding_cost, replenishment_policy=None, **inventory_kwargs)
            self.inventory_drop = self.env.event()  # event to signal when inventory is dropped
            self.inventory_raised = self.env.event() # signal to indicate that inventory has been raised
            if(self.raw_material):
                self.env.process(self.behavior()) # start the behavior process
            else:
                self.logger.error(f"{self.ID}:Raw material not provided for this supplier. Recreate it with a raw material.")
                raise ValueError("Raw material not provided.")
        else:
            inventory_kwargs = {k: v for k, v in kwargs.items() if k not in _LOGGER_KWARGS and k not in _NODE_KWARGS}
            self.inventory = Inventory(env=self.env, capacity=float('inf'), initial_level=float('inf'), node=self, holding_cost=inventory_holding_cost, replenishment_policy=None, **inventory_kwargs)
        
        self.stats = Statistics(self, periodic_update=periodic_stats, period=stats_period)
        setattr(self.stats,"total_raw_materials_mined",0)
        setattr(self.stats,"total_material_cost",0)
        self.stats._stats_keys.extend(["total_raw_materials_mined", "total_material_cost"])
        self.stats._cost_components.append("total_material_cost")
        
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
        while True:
            if(self.inventory.level < self.inventory.capacity): # check if the inventory is not full
                mined_quantity = self.raw_material.extraction_quantity
                if((self.inventory.level+self.raw_material.extraction_quantity)>self.inventory.capacity): # check if the inventory can accommodate the extracted quantity
                    mined_quantity = self.inventory.capacity - self.inventory.level # update statistics
                self.inventory.put(mined_quantity)
                self.stats.update_stats(total_raw_materials_mined=mined_quantity, total_material_cost=mined_quantity*self.raw_material.mining_cost)
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Raw material mined/extracted. Inventory level:{self.inventory.level}")
                yield self.env.timeout(self.raw_material.extraction_time)
            else:
                # Inventory is full — wait for a downstream draw (Inventory.get
                # succeeds inventory_drop) instead of polling every tick.
                yield from self.wait_for_drop()
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Inventory level:{self.inventory.level}") # log on each event-driven wake-up

class InventoryNode(Node):
    """
    The `InventoryNode` class represents an inventory management node in the supply network, 
    such as a retailer, a store, a warehouse, or distributor. It manages inventory levels, replenishment policies, 
    supplier selection, and order processing dynamically.

    The node can handle both perishable and non-perishable inventories and supports 
    automatic replenishment using various replenishment policies. The node can also
    interact with multiple supplier links and selects suppliers based on the 
    configured selection policy.

    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): Unique identifier for the node.
        name (str): Name of the inventory node.
        node_type (str): Type of the inventory node (e.g., retailer or distributor).
        capacity (float): Maximum capacity of the inventory.
        initial_level (float): Initial inventory level.
        inventory_holding_cost (float): Inventory holding cost per unit.
        replenishment_policy (InventoryReplenishment): Replenishment policy object for the inventory.
        policy_param (dict): Parameters for the replenishment policy.
        product_sell_price (float): Selling price of the product.
        product_buy_price (float): Buying price of the product.
        inventory_type (str): Type of inventory ("non-perishable" or "perishable").
        shelf_life (float): Shelf life of the product for perishable items.
        manufacture_date (callable): Function to model manufacturing date (used for perishable inventories).
        product (Product): Product managed by the inventory node.
        supplier_selection_policy (SupplierSelectionPolicy): Supplier selection policy class.
        supplier_selection_mode (str): Mode for supplier selection (default is "fixed").
        **kwargs: Additional keyword arguments for the Node class and logger.

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        replenishment_policy (InventoryReplenishment): Replenishment policy object.
        inventory (Inventory): Inventory object managing stock.
        inventory_drop (simpy.Event): Event triggered when inventory drops.
        inventory_raised (simpy.Event): Event triggered when inventory is replenished.
        manufacture_date (callable): Manufacturing date generation function.
        sell_price (float): Selling price of the product.
        buy_price (float): Buying price of the product.
        product (Product): Product managed by the node.
        suppliers (list): List of supplier links connected to this node.
        pending_orders (int): Number of replenishment orders currently in flight (dispatched but not yet delivered).
        selection_policy (SupplierSelectionPolicy): Supplier selection policy object.
        stats (Statistics): Statistics tracking object for this node.

    Functions:
        __init__: Initializes the InventoryNode object.
        process_order: Places an order with the selected supplier and updates inventory upon delivery.
    """
    _info_keys = Node._info_keys + ["sell_price", "buy_price", "pending_orders", "selection_policy"]

    def __init__(self,
                 env: simpy.Environment,
                 ID: str,
                 name: str,
                 node_type: str,
                 capacity: float,
                 initial_level: float,
                 inventory_holding_cost:float,
                 replenishment_policy:InventoryReplenishment,
                 policy_param: dict,
                 product_sell_price: float,
                 product_buy_price: float,
                 inventory_type:str = "non-perishable", 
                 shelf_life:float = 0.0,
                 manufacture_date: Callable = None,
                 product:Product = None,
                 supplier_selection_policy: SupplierSelectionPolicy = SelectFirst,
                 supplier_selection_mode: str = "fixed",
                 **kwargs) -> None:
        """
        Initialize the inventory node object.
        
        Parameters:
            env (simpy.Environment): Simulation environment.
            ID (str): Unique identifier for the node.
            name (str): Name of the inventory node.
            node_type (str): Type of the inventory node (e.g., retailer or distributor).
            capacity (float): Maximum capacity of the inventory.
            initial_level (float): Initial inventory level.
            inventory_holding_cost (float): Inventory holding cost per unit.
            replenishment_policy (InventoryReplenishment): Replenishment policy object for the inventory.
            policy_param (dict): Parameters for the replenishment policy.
            product_sell_price (float): Selling price of the product.
            product_buy_price (float): Buying price of the product.
            inventory_type (str): Type of inventory ("non-perishable" or "perishable").
            shelf_life (float): Shelf life of the product for perishable items.
            manufacture_date (callable): Function to model manufacturing date (used for perishable inventories).
            product (Product): Product managed by the inventory node.
            supplier_selection_policy (SupplierSelectionPolicy): Supplier selection policy class.
            supplier_selection_mode (str): Mode for supplier selection (default is "fixed").
            **kwargs: Additional keyword arguments for the Node class and logger.
        
        Attributes:
            _info_keys (list): List of keys to include in the info dictionary.
            replenishment_policy (InventoryReplenishment): Replenishment policy object.
            inventory (Inventory): Inventory object managing stock.
            inventory_drop (simpy.Event): Event triggered when inventory drops.
            inventory_raised (simpy.Event): Event triggered when inventory is replenished.
            manufacture_date (callable): Manufacturing date generation function.
            sell_price (float): Selling price of the product.
            buy_price (float): Buying price of the product.
            product (Product): Product managed by the node.
            suppliers (list): List of supplier links connected to this node.
            pending_orders (int): Number of replenishment orders currently in flight (dispatched but not yet delivered).
            selection_policy (SupplierSelectionPolicy): Supplier selection policy object.
            stats (Statistics): Statistics tracking object for this node.
        
        Returns:
            None

        Behavior:
            The inventory node stocks the product in inventory to make it available to the consumer node or demand node (end customer). 
            It orders product from its supplier node to maintain the right inventory levels according to the replenishment policy.
            The inventory node can have multiple suppliers. It chooses a supplier based on the specified supplier selection policy. 
            The product buy and sell prices are set during initialization. The inventory node is expected to sell the product at 
            a higher price than the buy price, but this is user-configured.
        """
        # Pull periodic-stats kwargs out before forwarding to Node — exposes
        # the ``Statistics`` periodic update cadence as a node-level kwarg.
        periodic_stats = kwargs.pop('periodic_stats', False)
        stats_period = kwargs.pop('stats_period', 1)
        if periodic_stats:
            validate_positive(name="stats_period", value=stats_period)
        super().__init__(env=env,ID=ID,name=name,node_type=node_type,**kwargs)
        validate_non_negative("Product Sell Price", product_sell_price)
        validate_non_negative("Product Buy Price", product_buy_price)
        self.replenishment_policy = None
        if(replenishment_policy):
            self.replenishment_policy = replenishment_policy(env = self.env, node = self, params = policy_param)
            self.env.process(self.replenishment_policy.run())
            
        inventory_kwargs = {k: v for k, v in kwargs.items() if k not in _LOGGER_KWARGS and k not in _NODE_KWARGS}
        self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, node=self,
                                   inv_type=inventory_type, holding_cost=inventory_holding_cost,
                                   replenishment_policy=self.replenishment_policy, shelf_life=shelf_life, **inventory_kwargs)
        self.inventory_drop = self.env.event()  # event to signal when inventory is dropped
        self.inventory_raised = self.env.event() # signal to indicate that inventory has been raised
        self.manufacture_date = manufacture_date
        self.sell_price = product_sell_price # set the sell price of the product
        self.buy_price = product_buy_price # set the buy price of the product
        if product is not None:
            # Deep-copy so each InventoryNode that "sells" the same Product
            # can override sell_price / buy_price independently without
            # mutating the original (or every other node's copy). Without
            # this, two nodes sharing a Product reference would clobber each
            # other's prices via the assignments below.
            self.product = copy.deepcopy(product)
            self.product.sell_price = product_sell_price
            self.product.buy_price = product_buy_price # set the buy price of the product to the product buy price
        # self.suppliers is already initialised to [] in Node.__init__; inbound
        # Links register themselves via Node.add_supplier_link.
        self.pending_orders = 0 # count of replenishment orders currently in flight (dispatched but not yet delivered)
        self.selection_policy = supplier_selection_policy(self,supplier_selection_mode)
        self.stats = Statistics(self, periodic_update=periodic_stats, period=stats_period) # create a statistics object for the inventory node

    def process_order(self, supplier, reorder_quantity):
        """
        Place an order for the product from the suppliers.

        Parameters:
            supplier (Link): The supplier link from which the order is placed.
            reorder_quantity (float): The quantity of the product to reorder.

        Attributes:
            None
        
        Returns:
            None
        """
        # Use the true physical commitment (on_hand - customer backorders) as the
        # reference for the capacity clamp. `on_hand` is inventory position, not
        # physical on-hand; customer backorders that still count against on_hand
        # will leave the shelf as soon as the next delivery lands, so they do not
        # consume capacity and must be excluded from the clamp.
        gross = self.inventory.on_hand - self.stats.backorder[1]
        if(gross + reorder_quantity > self.inventory.capacity): # check if the inventory can accommodate the reordered quantity
                reorder_quantity = self.inventory.capacity - gross # if not, adjust reorder quantity to order only what can fit

        if reorder_quantity <= 0:
            return  # no need to place an order if reorder quantity is zero

        # A new order cannot be placed while the physical transport link is down.
        # Ongoing shipments that already cleared this gate are not interrupted —
        # Link.disruption only blocks *new* dispatches. Guarding here (before the
        # shortage bookkeeping and before pending_orders increments) means a
        # blocked order does not count as in-flight or create a phantom
        # backorder on the supplier. The replenishment policy re-triggers when
        # inventory drops again or on the next periodic tick.
        if supplier.status == "inactive":
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Link:{supplier.ID} from {supplier.source.name} is disrupted. Order not placed.")
            return

        self.pending_orders += 1  # count this order as in flight; decremented when delivery completes (or supplier disrupted)

        if supplier.source.inventory.level < reorder_quantity:  # check if the supplier is able to fulfill the order, record shortage
            shortage = reorder_quantity - supplier.source.inventory.level
            supplier.source.stats.update_stats(shortage=[1,shortage], backorder=[1,reorder_quantity])
            if(not supplier.source.inventory_drop.triggered):
                supplier.source.inventory_drop.succeed()  # signal that inventory has been dropped (since backorder is created)

        if(supplier.source.node_status == "active"):
            self.stats.update_stats(demand_placed=[1,reorder_quantity],transportation_cost=supplier.cost)
            supplier.source.stats.update_stats(demand_received=[1,reorder_quantity])

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing inventory from supplier:{supplier.source.name}, order placed for {reorder_quantity} units.")
            event, man_date_ls = supplier.source.inventory.get(reorder_quantity)
            self.inventory.on_hand += reorder_quantity
            yield event

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.") # log the shipment
            lead_time = supplier.lead_time() # get the lead time from the supplier
            validate_non_negative(name="lead_time", value=lead_time) # check if lead_time is non-negative
            yield self.env.timeout(lead_time) # lead time for the order

            accepted = 0
            if(man_date_ls):
                for ele in man_date_ls: # get manufacturing date from the supplier
                    accepted += self.inventory.put(ele[1],ele[0])
            elif(self.inventory.inv_type=="perishable"): # if self inventory is perishable but manufacture date is not provided
                if(self.manufacture_date): # calculate the manufacturing date using the function if provided
                    accepted = self.inventory.put(reorder_quantity,self.manufacture_date(self.env.now))
                else: # else put the product in the inventory with current time as manufacturing date
                    accepted = self.inventory.put(reorder_quantity,self.env.now)
            else:
                accepted = self.inventory.put(reorder_quantity)

            # Reconcile on_hand with what put() actually accepted: the pre-increment
            # at line ~2014 assumed the full reorder_quantity would land, but put() may
            # clamp at capacity or refuse at capacity/inf/non-positive. Without this,
            # on_hand drifts permanently higher than the physical+in-transit total.
            shortfall = reorder_quantity - accepted
            if shortfall > 0:
                self.inventory.on_hand -= shortfall

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Inventory replenished. reorder_quantity={reorder_quantity}, Inventory levels:{self.inventory.level}")

            self.stats.update_stats(fulfillment_received=[1,reorder_quantity],inventory_spend_cost=reorder_quantity*self.buy_price)
            supplier.source.stats.update_stats(demand_fulfilled=[1,reorder_quantity])
        else:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Supplier:{supplier.source.name} is disrupted. Order not placed.")
        self.pending_orders -= 1

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
        capacity (float): Maximum capacity of the finished product inventory.
        initial_level (float): Initial inventory level for finished products.
        inventory_holding_cost (float): Holding cost per unit for finished products.
        product_sell_price (float): Selling price per unit of the finished product.
        replenishment_policy (InventoryReplenishment): Replenishment policy object for the product inventory.
        policy_param (dict): Parameters for the replenishment policy.
        product (Product): Product manufactured by the manufacturer.
        inventory_type (str): Type of inventory ("non-perishable" or "perishable").
        shelf_life (float): Shelf life of the product.
        supplier_selection_policy (SupplierSelectionPolicy): Supplier selection policy class.
        supplier_selection_mode (str): Supplier selection mode (default is "fixed").
        **kwargs: Additional keyword arguments for the Node class and logger.

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        replenishment_policy (InventoryReplenishment): Replenishment policy object for the product inventory.
        inventory (Inventory): Inventory object managing finished product stock.
        inventory_drop (simpy.Event): Event triggered when inventory drops.
        inventory_raised (simpy.Event): Event triggered when inventory is replenished.
        product (Product): Product manufactured by the manufacturer.
        suppliers (list): List of supplier links connected to this manufacturer.
        sell_price (float): Selling price per unit of the product.
        production_cycle (bool): Indicates whether the production cycle is currently active.
        raw_inventory_counts (dict): Inventory levels of raw materials by raw material ID.
        ongoing_order_raw (dict): Indicates whether a raw material order is currently in progress.
        pending_orders (int): Number of raw-material orders currently in flight (dispatched but not yet delivered).
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
        are available. Finished products are added to the inventory upon completion of a manufacturing cycle. If raw 
        materials are insufficient, the manufacturer places replenishment orders with connected suppliers.

    Assumptions:
        The manufacturer produces only a single type of product.
        Separate inventories are maintained for raw materials and finished products.
        Only the finished product inventory is actively monitored by the replenishment policy.
        Raw material inventories are replenished based on product inventory requirements.
        The raw material inventory is initially empty.
    """
    _info_keys = Node._info_keys + ["replenishment_policy", "product_sell_price"]

    def __init__(self,
                 env: simpy.Environment,
                 ID: str,
                 name: str,
                 capacity: float,
                 initial_level: float, 
                 inventory_holding_cost: float, 
                 product_sell_price: float, 
                 replenishment_policy: InventoryReplenishment, 
                 policy_param: dict, 
                 product: Product = None, 
                 inventory_type: str = "non-perishable",
                 shelf_life: float = 0.0,
                 supplier_selection_policy: SupplierSelectionPolicy = SelectFirst,
                 supplier_selection_mode: str = "fixed",
                 **kwargs) -> None:
        """
        Initialize the manufacturer object.
        
        Parameters:
            env (simpy.Environment): Simulation environment.
            ID (str): Unique identifier for the manufacturer.
            name (str): Name of the manufacturer.
            capacity (float): Maximum capacity of the finished product inventory.
            initial_level (float): Initial inventory level for finished products.
            inventory_holding_cost (float): Holding cost per unit for finished products.
            product_sell_price (float): Selling price per unit of the finished product.
            replenishment_policy (InventoryReplenishment): Replenishment policy object for the product inventory.
            policy_param (dict): Parameters for the replenishment policy.
            product (Product): Product manufactured by the manufacturer.
            inventory_type (str): Type of inventory ("non-perishable" or "perishable").
            shelf_life (float): Shelf life of the product.
            supplier_selection_policy (SupplierSelectionPolicy): Supplier selection policy class.
            supplier_selection_mode (str): Supplier selection mode (default is "fixed").
            **kwargs: Additional keyword arguments for the Node class and logger.

        Attributes:
            _info_keys (list): List of keys to include in the info dictionary.
            replenishment_policy (InventoryReplenishment): Replenishment policy object for the product inventory.
            inventory (Inventory): Inventory object managing finished product stock.
            inventory_drop (simpy.Event): Event triggered when inventory drops.
            inventory_raised (simpy.Event): Event triggered when inventory is replenished.
            product (Product): Product manufactured by the manufacturer.
            suppliers (list): List of supplier links connected to this manufacturer.
            sell_price (float): Selling price per unit of the product.
            production_cycle (bool): Indicates whether the production cycle is currently active.
            raw_inventory_counts (dict): Inventory levels of raw materials by raw material ID.
            ongoing_order_raw (dict): Indicates whether a raw material order is currently in progress.
            pending_orders (int): Number of raw-material orders currently in flight (dispatched but not yet delivered).
            selection_policy (SupplierSelectionPolicy): Supplier selection policy object.
            stats (Statistics): Statistics tracking object for the manufacturer.

        Returns:
            None
        """
        # Pull periodic-stats kwargs out before forwarding to Node — exposes
        # the ``Statistics`` periodic update cadence as a node-level kwarg.
        periodic_stats = kwargs.pop('periodic_stats', False)
        stats_period = kwargs.pop('stats_period', 1)
        if periodic_stats:
            validate_positive(name="stats_period", value=stats_period)
        super().__init__(env=env,ID=ID,name=name,node_type="manufacturer",**kwargs)
        if product == None:
            global_logger.error("Product not provided for the manufacturer.")
            raise ValueError("Product not provided for the manufacturer.")
        elif not isinstance(product, Product):
            raise ValueError("Invalid product type. Expected a Product instance.")
        validate_positive("Product Sell Price", product_sell_price)
        self.replenishment_policy = None
        if(replenishment_policy):
            self.replenishment_policy = replenishment_policy(env = self.env, node = self, params = policy_param)
            self.env.process(self.replenishment_policy.run())
        
        inventory_kwargs = {k: v for k, v in kwargs.items() if k not in _LOGGER_KWARGS and k not in _NODE_KWARGS}
        self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, node=self, inv_type=inventory_type, holding_cost=inventory_holding_cost, replenishment_policy=self.replenishment_policy, shelf_life=shelf_life, **inventory_kwargs)
        self.inventory_drop = self.env.event()  # event to signal when inventory is dropped
        self.inventory_raised = self.env.event() # signal to indicate that inventory has been raised
        # Event-driven trigger for the production loop: succeeds whenever
        # ``process_order_raw`` deposits raw material into ``raw_inventory_counts``.
        # ``behavior`` waits on it instead of polling every simulation tick.
        self.raw_material_arrived = self.env.event()
        self.product = product # product manufactured by the manufacturer
        # self.suppliers is already initialised to [] in Node.__init__.
        self.product.sell_price = product_sell_price
        self.sell_price = product_sell_price # set the sell price of the product
        
        self.production_cycle = False # production cycle status
        self.raw_inventory_counts = {} # dictionary to store inventory counts for raw products inventory
        self.ongoing_order_raw = {} # dictionary to store order status
        self.pending_orders = 0 # count of raw-material orders currently in flight (dispatched but not yet delivered)

        if(self.product.buy_price <= 0): # if the product buy price is not given, calculate it
            self.product.buy_price = self.product.manufacturing_cost 
            for raw_material in self.product.raw_materials:
                self.product.buy_price += raw_material[0].cost * raw_material[1] # calculate total cost of the product (per unit)

        self.env.process(self.behavior()) # start the behavior process
        self.selection_policy = supplier_selection_policy(self,supplier_selection_mode)
        
        self.stats = Statistics(self, periodic_update=periodic_stats, period=stats_period) # create a statistics object for the manufacturer
        setattr(self.stats,"total_products_manufactured",0) # adding specific statistics for the manufacturer
        setattr(self.stats,"total_manufacturing_cost",0) # adding specific statistics for the manufacturer
        self.stats._stats_keys.extend(["total_products_manufactured", "total_manufacturing_cost"])
        self.stats._cost_components.append("total_manufacturing_cost")

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
        if((self.inventory.level + max_producible_units)>self.inventory.capacity): # check if the inventory can accommodate the maximum producible units
            max_producible_units = self.inventory.capacity - self.inventory.level
        # Don't produce more than what's been committed via process_order.
        # on_hand already accounts for pending production (§3.11); producing
        # beyond (on_hand - level) would grow level past on_hand, breaking
        # the invariant level <= on_hand and masking true inventory position.
        pending = self.inventory.on_hand - self.inventory.level
        if pending < max_producible_units:
            max_producible_units = max(pending, 0)
        if(max_producible_units>0):
            self.production_cycle = True # produce the product
            for raw_material in self.product.raw_materials: # consume raw materials
                raw_mat_id = raw_material[0].ID
                required_amount = raw_material[1]
                self.raw_inventory_counts[raw_mat_id] -= raw_material[1]*max_producible_units
            yield self.env.timeout(self.product.manufacturing_time) # take manufacturing time to produce the product
            accepted = self.inventory.put(max_producible_units, manufacturing_date=self.env.now)
            shortfall = max_producible_units - accepted
            if shortfall > 0:
                self.inventory.on_hand -= shortfall
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: {max_producible_units} units manufactured.")
            self.logger.info(f"{self.env.now:.4f}:{self.ID}: Product inventory levels:{self.inventory.level}")
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
            self.logger.error("No suppliers connected to the manufacturer.")
            raise ValueError("No suppliers connected to the manufacturer.")

        if(len(self.suppliers)>0): # create an inventory for storing raw materials as a dictionary. Key: raw material ID, Value: inventory level
            for supplier in self.suppliers: # iterate over supplier links
                if(supplier.source.raw_material is None): # check if the supplier has a raw material
                    self.logger.error(f"{self.ID}:Supplier {supplier.source.ID} does not have a raw material. Please provide a raw material for the supplier.")
                    raise ValueError(f"Supplier {supplier.source.ID} does not have a raw material.")
                self.raw_inventory_counts[supplier.source.raw_material.ID] = 0 # store initial levels
                self.ongoing_order_raw[supplier.source.raw_material.ID] = False # store order status
                
        if(len(self.suppliers)<len(self.product.raw_materials)):
            self.logger.warning(f"{self.ID}: {self.name}: The number of suppliers are less than the number of raw materials required to manufacture the product! This leads to no products being manufactured.")

        # Event-driven production loop: produce whenever raw material arrives,
        # then block on ``raw_material_arrived`` until the next delivery. The
        # ``production_cycle`` re-entry guard from the polling version is no
        # longer needed because we await ``manufacture_product`` directly, so
        # at most one production cycle is in flight at any time.
        while len(self.suppliers) >= len(self.product.raw_materials): # check if required number of suppliers are connected
            yield self.env.process(self.manufacture_product()) # produce the product (no-op if max_producible == 0)
            yield self.raw_material_arrived
            self.raw_material_arrived = self.env.event() # rotate for the next arrival

    def process_order_raw(self, raw_mat_id, supplier, reorder_quantity):
        """
        Place an order for given raw material from the given supplier for replenishment.
        
        Parameters:
            supplier (Link): The supplier link from which the order is placed.
            reorder_quantity (float): The quantity of the raw material to reorder.
        
        Attributes:
            None

        Returns:    
            None
        """
        # Link-disruption gate: mirrors the one in InventoryNode.process_order.
        # A disrupted physical link blocks new raw-material dispatches; ongoing
        # shipments already past this point keep flowing. We clear ongoing_order_raw
        # so the per-material flag does not stick and the manufacturer can retry
        # the order on the next replenishment tick, once the link recovers.
        if supplier.status == "inactive":
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Link:{supplier.ID} from {supplier.source.name} is disrupted. Raw-material order not placed.")
            self.ongoing_order_raw[raw_mat_id] = False
            yield self.env.timeout(1) # wait a tick before the policy retries
            return

        if supplier.source.inventory.level < reorder_quantity:  # check if the supplier is able to fulfill the order, record shortage
            shortage = reorder_quantity - supplier.source.inventory.level
            supplier.source.stats.update_stats(shortage=[1,shortage], backorder=[1,reorder_quantity])

        if(supplier.source.node_status == "active"): # check if the supplier is active and has enough inventory
            if(self.raw_inventory_counts[raw_mat_id]>= reorder_quantity): # dont order if enough inventory is available (reorder_quantity depends on the number of product units that needs to be manufactured, there is no capcacity defined for raw material inventory)
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Sufficient raw material inventory for {supplier.source.raw_material.name}, no order placed. Current inventory level: {self.raw_inventory_counts}.")
                self.ongoing_order_raw[raw_mat_id] = False
                return

            self.pending_orders += 1  # count this raw-material order as in flight
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing raw material:{supplier.source.raw_material.name} from supplier:{supplier.source.ID}, order placed for {reorder_quantity} units. Current inventory level: {self.raw_inventory_counts}.")
            event, man_date_ls = supplier.source.inventory.get(reorder_quantity)
            supplier.source.stats.update_stats(demand_received=[1,reorder_quantity]) # update the supplier statistics for demand received
            yield event

            self.stats.update_stats(demand_placed=[1,reorder_quantity],transportation_cost=supplier.cost)
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.")
            lead_time = supplier.lead_time() # get the lead time from the supplier
            validate_non_negative(name="lead_time", value=lead_time) # check if lead_time is non-negative
            yield self.env.timeout(lead_time) # lead time for the order

            self.stats.update_stats(fulfillment_received=[1,reorder_quantity],inventory_spend_cost=reorder_quantity*supplier.source.sell_price)
            supplier.source.stats.update_stats(demand_fulfilled=[1,reorder_quantity]) # update the supplier statistics for demand fulfilled
            self.ongoing_order_raw[raw_mat_id] = False
            self.raw_inventory_counts[raw_mat_id] += reorder_quantity
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Order received from supplier:{supplier.source.name}, inventory levels: {self.raw_inventory_counts}")
            self.pending_orders -= 1
            # Wake the production loop — raw material just landed.
            if not self.raw_material_arrived.triggered:
                self.raw_material_arrived.succeed()
        else:
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Supplier:{supplier.source.name} is disrupted.")
            yield self.env.timeout(1) # wait for 1 time unit before checking again

        self.ongoing_order_raw[raw_mat_id] = False
    
    def process_order(self, supplier, reorder_quantity):
        """
        Place an order for raw materials and replenish raw materials inventory.
        
        Parameters:
            supplier (Link): Supplier link
            reorder_quantity (float): The quantity of the raw material to reorder.
        
        Attributes:
            None

        Returns:
            None
        """
        # Exclude customer backorders from the capacity clamp — they still count
        # against on_hand but will leave the shelf on the next delivery, so they
        # do not consume product-inventory capacity. See §3.10 for details.
        gross = self.inventory.on_hand - self.stats.backorder[1]
        if(gross + reorder_quantity > self.inventory.capacity): # check if the inventory can accommodate the reordered quantity
                reorder_quantity = self.inventory.capacity - gross # if not, adjust reorder quantity to order only what can fit
        if reorder_quantity <= 0:
            return # no need to place an order if reorder quantity is zero

        # Commit the intended production up-front on on_hand (mirroring
        # InventoryNode.process_order). Without this commit, the replenishment
        # policy can re-trigger between dispatch here and the next
        # manufacture_product run, see a stale on_hand, and place a duplicate
        # raw-material order for the same product units. See §3.11.
        self.inventory.on_hand += reorder_quantity

        for raw_mat in self.product.raw_materials: # place order for all raw materials required to produce the product
            raw_mat_id = raw_mat[0].ID
            raw_mat_reorder_sz = raw_mat[1]*reorder_quantity
            for supplier in self.suppliers:
                if(supplier.source.raw_material.ID == raw_mat_id and self.ongoing_order_raw[raw_mat_id] == False): # check if the supplier has the raw material and order is not already placed
                    self.ongoing_order_raw[raw_mat_id] = True # set the order status to True
                    self.env.process(self.process_order_raw(raw_mat_id, supplier, raw_mat_reorder_sz)) # place the order for the raw material
        # Zero-duration yield: this method is called via ``env.process`` so it
        # has to be a generator, but it has no real wait — every raw-material
        # dispatch is itself spawned as a sibling process and not awaited
        # here (the production loop wakes via ``raw_material_arrived``). The
        # historical ``timeout(1)`` was an arbitrary one-tick stall called
        # out as §8's "process_order trailing tick" nit.
        yield self.env.timeout(0)

class Demand(Node):
    """
    The `Demand` class represents a demand node that generates product orders within the supply network. 
    It models dynamic demand patterns using user-defined functions for order arrival times and order quantities, and manages 
    customer tolerance for waiting in case of product unavailability.
    The demand node automatically places customer orders at configurable intervals and can handle situations where the requested 
    quantity is not immediately available. Customers can either wait (if tolerance is set) or leave the system unfulfilled.

    The class supports: 
    
    - Customizable lead time and delivery cost per order, 
    
    - Dynamic order splitting based on the minimum split ratio, 
    
    - Backorder management and real-time inventory check.

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
        consume_available (bool): If True, the demand node consumes available inventory immediately and leaves.
        **kwargs: Additional keyword arguments for Node and GlobalLogger.

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        order_arrival_model (callable): Function defining the order arrival process.
        order_quantity_model (callable): Function defining the order quantity distribution.
        demand_node (Node): Upstream node supplying the demand.
        customer_tolerance (float): Maximum waiting time allowed for customer orders.
        delivery_cost (callable): Delivery cost function for each order.
        lead_time (callable): Delivery lead time function for each order.
        min_split (float): Minimum allowed split ratio for partially fulfilled orders.
        consume_available (bool): If True, partial fulfillment is allowed and available inventory is consumed immediately.
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
        If not, 
        
        - the customer may leave immediately (if tolerance is zero)

        - else, the customer waits for the order to be fulfilled within their tolerance time, possibly accepting
        partial deliveries if a split ratio is allowed. If the tolerance is exceeded, the unmet demand is recorded as a shortage.

    Assumptions:
        - Customer orders arrive following the provided stochastic arrival model.
        - Order quantities follow the specified stochastic quantity model.
        - Customers may wait for the fulfillment of their orders up to the defined tolerance time.
        - Customers can accept split deliveries based on the minimum split ratio.
        - If customer tolerance is zero, customer returns without waiting for fulfillment.
        - Delivery cost and lead time are sampled dynamically for each order (if specified).
        - The connected upstream node must not be a supplier; it should typically be a retailer or distributor node.
    """
    _info_keys = Node._info_keys + [
        "order_arrival_model", "order_quantity_model", "demand_node",
        "customer_tolerance", "delivery_cost", "lead_time",
    ]

    def __init__(self,
                 env: simpy.Environment,
                 ID: str,
                 name: str,
                 order_arrival_model: Callable,
                 order_quantity_model: Callable,
                 demand_node: Node,
                 tolerance: float = 0.0,
                 order_min_split_ratio: float = 1.0,
                 delivery_cost: Callable = lambda: 0,
                 lead_time: Callable = lambda: 0,
                 consume_available: bool = False,
                 **kwargs) -> None:
        """
        Initialize the demand node object.
        
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
            consume_available (bool): If True, the demand node consumes available inventory immediately and leaves.
            **kwargs: Additional keyword arguments for Node and GlobalLogger.
        
        Attributes:
            _info_keys (list): List of keys to include in the info dictionary.
            order_arrival_model (callable): Function defining the order arrival process.
            order_quantity_model (callable): Function defining the order quantity distribution.
            demand_node (Node): Upstream node supplying the demand.
            customer_tolerance (float): Maximum waiting time allowed for customer orders.
            delivery_cost (callable): Delivery cost function for each order.
            lead_time (callable): Delivery lead time function for each order.
            min_split (float): Minimum allowed split ratio for partially fulfilled orders.
            consume_available (bool): If True, partial fulfillment is allowed and available inventory is consumed immediately.
            stats (Statistics): Tracks various performance metrics like demand placed, fulfilled, and shortages.

        Returns:
            None
        """
        # Pull periodic-stats kwargs out before forwarding to Node — exposes
        # the ``Statistics`` periodic update cadence as a node-level kwarg.
        periodic_stats = kwargs.pop('periodic_stats', False)
        stats_period = kwargs.pop('stats_period', 1)
        if periodic_stats:
            validate_positive(name="stats_period", value=stats_period)
        super().__init__(env=env,ID=ID,name=name,node_type="demand",**kwargs)
        if order_arrival_model is None or order_quantity_model is None:
            raise ValueError("Order arrival and quantity models cannot be None.")
        # Auto-wrap + numeric-validate every Demand callable in one place;
        # see ``ensure_numeric_callable`` for the §6.4 rationale.
        order_arrival_model = ensure_numeric_callable("order_arrival_model", order_arrival_model)
        order_quantity_model = ensure_numeric_callable("order_quantity_model", order_quantity_model)
        delivery_cost = ensure_numeric_callable("delivery_cost", delivery_cost)
        lead_time = ensure_numeric_callable("lead_time", lead_time)
        if demand_node is None or "supplier" in demand_node.node_type:
            raise ValueError("Demand node must be a valid non-supplier node.")
        validate_non_negative("Customer tolerance", tolerance)
        validate_positive("Order Min Split Ratio", order_min_split_ratio)
        if order_min_split_ratio > 1:
            self.logger.error("Order Min Split Ratio must be in the range (0, 1].")
            raise ValueError("Order Min Split Ratio must be in the range (0, 1].")
        validate_number(name="order_time", value=order_arrival_model())
        validate_number(name="order_quantity", value=order_quantity_model())
        validate_number(name="delivery_cost", value=delivery_cost()) # check if delivery_cost is a number
        validate_number(name="lead_time", value=lead_time()) # check if lead_time is a number

        self.order_arrival_model = order_arrival_model
        self.order_quantity_model = order_quantity_model
        self.demand_node = demand_node
        self.customer_tolerance = tolerance
        self.delivery_cost = delivery_cost
        self.lead_time = lead_time
        self.min_split = order_min_split_ratio
        self.consume_available = consume_available # if True, the demand node consumes available inventory immediately and leaves
        self.env.process(self.behavior())
        self.stats = Statistics(self, periodic_update=periodic_stats, period=stats_period) # create a statistics object for the demand node

    def _process_delivery(self, order_quantity, customer_id):
        """
        Process the delivery of the order, including lead time and delivery cost updates.

        Parameters:
            order_quantity (float): The quantity of the product ordered.
            customer_id (int): Customer ID for logging purposes.

        Attributes:
            order_quantity (float): The quantity of the product ordered.
            customer_id (int): Customer ID for logging purposes.

        returns:
            None
        """
        del_cost = self.delivery_cost()
        validate_non_negative(name="delivery_cost", value=del_cost) # check if delivery_cost is non-negative
        self.stats.update_stats(transportation_cost=del_cost)
        
        get_event, _ = self.demand_node.inventory.get(order_quantity)
        yield get_event
        self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}:Order quantity:{order_quantity}, available.")

        lead_time = self.lead_time() # get the lead time from the demand node
        validate_non_negative(name="lead_time", value=lead_time) # check if lead_time is non-negative
        yield self.env.timeout(lead_time) # wait for the delivery of the order
        #self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}:Order quantity:{order_quantity} received.")

        self.stats.update_stats(fulfillment_received=[1,order_quantity])
        self.demand_node.stats.update_stats(demand_fulfilled=[1,order_quantity]) 
    
    def wait_for_order(self,customer_id,order_quantity):
        """
        Wait for the required number of units based on customer tolerance.
        If the customer tolerance is infinite, the method waits until the order is fulfilled.
        Otherwise, it waits for the specified tolerance time and updates the unsatisfied demand if the order is not fulfilled.
        
        Parameters:
            order_quantity (float): The quantity of the product ordered.
            customer_id (int): Customer ID for logging purposes.

        Attributes:
            customer_id (int): Customer ID for logging purposes.
            order_quantity (float): The quantity of the product ordered.
        
        Returns:
            None
        """
        self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}:Order quantity:{order_quantity} not available! Order will be split if split ratio is provided.")
        self.demand_node.stats.update_stats(backorder=[1,order_quantity])
        if(not self.demand_node.inventory_drop.triggered):
            self.demand_node.inventory_drop.succeed()  # signal that inventory has been dropped (since backorder is created)
        partial = order_quantity
        if self.min_split < 1:
            partial = int(order_quantity * self.min_split)
        
        waited = 0
        available = 0
        while order_quantity>0 and waited<=self.customer_tolerance:
            waiting_time = self.env.now
            available = self.demand_node.inventory.level
            if order_quantity <= available: # check if remaining order quantity is available 
                self.env.process(self._process_delivery(order_quantity, customer_id))
                self.demand_node.stats.update_stats(backorder=[-1,-order_quantity])
                order_quantity = 0
                break
            elif available >= partial: # or else at least min required 'partial' is available
                self.env.process(self._process_delivery(available, customer_id))
                # Partial shipment: backorder count stays 1 (one outstanding customer order)
                # while its quantity ticks down. fulfillment_received and demand_fulfilled
                # each get a compensating -1 on the count so the single eventual completion
                # is counted exactly once — matching the backorder accounting convention.
                self.demand_node.stats.update_stats(backorder=[0,-available], demand_fulfilled=[-1,0])
                self.stats.update_stats(fulfillment_received=[-1,0])
                order_quantity -= available # update order quantity
            else: 
                self.demand_node.stats.update_stats(shortage=[1,order_quantity-available])
            yield self.demand_node.inventory_raised # wait until inventory is replenished
            self.demand_node.inventory_raised = self.env.event()  # reset the event for the next iteration
            waited += self.env.now - waiting_time # update the waited time
        
        if order_quantity > 0: # if the order quantity is still greater than 0, it means the order was not fulfilled
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}: remaining order quantity:{order_quantity} not available!")

    # ---- Customer-fulfilment helpers (§6.5) -------------------------------
    # ``customer`` used to inline four different fulfilment paths with
    # different yield idioms (``yield from`` vs ``env.process`` vs no yield
    # at all) and stats updates baked into each branch. Factoring them into
    # named helpers makes the intent of each branch explicit and keeps
    # ``customer`` itself a one-glance dispatcher. Each helper is a SimPy
    # generator returning ``None`` so the dispatcher can use a uniform
    # ``yield from`` form; ``_serve_no_tolerance`` is a degenerate generator
    # (``return; yield``) so the call site does not need a special case.
    # The third helper deliberately spawns ``wait_for_order`` as its own
    # process — preserving the historical fire-and-forget semantics so the
    # customer's enclosing ``customer`` call returns promptly even when the
    # tolerance window is large; KPIs accrue inside ``wait_for_order`` no
    # matter when the parent process exits.

    def _serve_in_full(self, order_quantity, customer_id):
        """Inventory has the full requested quantity — record demand and deliver."""
        self.demand_node.stats.update_stats(demand_received=[1, order_quantity])
        yield from self._process_delivery(order_quantity, customer_id)

    def _serve_partial_consume(self, order_quantity, available, customer_id):
        """``consume_available`` path — ship what's on hand, record the rest as shortage."""
        self.logger.info(
            f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}: Order quantity:"
            f"{order_quantity} not available, inventory level:{available}. Consuming available inventory."
        )
        self.demand_node.stats.update_stats(
            demand_received=[1, available],
            shortage=[1, order_quantity - available],
        )
        yield from self._process_delivery(available, customer_id)

    def _enqueue_for_tolerance(self, order_quantity, available, customer_id):
        """Backorder-allowed path — record shortage and let ``wait_for_order`` poll until tolerance."""
        self.demand_node.stats.update_stats(
            demand_received=[1, order_quantity],
            shortage=[1, order_quantity - available],
        )
        # Fire-and-forget: ``wait_for_order`` runs as a sibling process so
        # the parent ``customer`` call returns promptly even when the
        # tolerance window is large. Backorder/shortage bookkeeping inside
        # ``wait_for_order`` is independent of the parent's lifecycle.
        self.env.process(self.wait_for_order(customer_id, order_quantity))
        return
        yield  # pragma: no cover — keeps this a generator so the dispatcher can ``yield from`` uniformly.

    def _serve_no_tolerance(self, order_quantity, available, customer_id):
        """Zero-tolerance path — log shortage and leave without a wait."""
        self.logger.info(
            f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}: Order quantity:"
            f"{order_quantity} not available, inventory level:"
            f"{self.demand_node.inventory.level}. No tolerance! Shortage:{order_quantity - available}."
        )
        self.demand_node.stats.update_stats(shortage=[1, order_quantity - available])
        return
        yield  # pragma: no cover — keeps this a generator (see _enqueue_for_tolerance).

    def customer(self, customer_id, order_quantity):
        """
        Dispatcher: route a single customer order to the right fulfilment helper.

        Four cases drive the dispatch — exactly the same set the original
        inline branch handled — but the branches now delegate to named
        helpers (see ``_serve_in_full`` / ``_serve_partial_consume`` /
        ``_enqueue_for_tolerance`` / ``_serve_no_tolerance``) so each path's
        intent is named in one place and the dispatcher reads as a single
        rule table.

        Parameters:
            customer_id (int): Customer ID for logging purposes.
            order_quantity (float): The quantity of the product ordered.

        Returns:
            None
        """
        available = self.demand_node.inventory.level
        self.stats.update_stats(demand_placed=[1, order_quantity])
        if order_quantity <= available:
            yield from self._serve_in_full(order_quantity, customer_id)
        elif self.consume_available and available > 0:
            yield from self._serve_partial_consume(order_quantity, available, customer_id)
        elif self.customer_tolerance > 0:
            yield from self._enqueue_for_tolerance(order_quantity, available, customer_id)
        else:
            yield from self._serve_no_tolerance(order_quantity, available, customer_id)
    
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
            self.env.process(self.customer(f"{customer_id}", order_quantity)) # create a customer
            customer_id += 1 # increment customer ID
            yield self.env.timeout(order_time) # wait for the next order arrival