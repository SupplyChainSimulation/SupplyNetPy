from SupplyNetPy.Components.logger import GlobalLogger
import enum
import heapq
import simpy
from simpy.core import BoundClass
from simpy.resources.container import ContainerGet
import copy
import random
import numbers
from typing import Callable

# Public API — the names re-exported by Components/__init__.py. The module-level
# values ``_rng``, ``_LOGGER_KWARGS`` and ``_NODE_KWARGS`` are internal and are
# left out on purpose. ``global_logger`` IS exported: the docs offer
# ``scm.global_logger.enable_logging() / disable_logging()`` as a single switch
# for all logging, so it is part of the supported API (though for everyday use
# prefer per-node ``logging=False`` or ``node.logger.*``). ``set_seed`` is the
# intended way to seed the default random-number generator; to give one
# component its own generator, pass ``rng=`` when building it.
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

# The keyword arguments that GlobalLogger accepts. Node.__init__ passes only
# these on to the logger, and Node subclasses remove them before passing the
# rest on to Inventory. Inventory takes a fixed set of arguments (no catch-all
# ``**kwargs``), so a misspelled parameter name raises a clear TypeError there
# instead of being quietly ignored.
_LOGGER_KWARGS = {"log_to_file", "log_file", "log_to_screen"}

# The keyword arguments that Node.__init__ itself uses. The Node subclasses
# (Supplier, InventoryNode, Manufacturer, Demand) take a catch-all ``**kwargs``,
# so these names are still present in the subclass's kwargs even after being
# passed up to Node; they must be removed before the remaining kwargs are passed
# on to Inventory.
_NODE_KWARGS = {"failure_p", "node_disrupt_time", "node_recovery_time", "logging", "rng", "logger_name", "stats_period", "periodic_stats", "disruption_impact", "disruption_loss_fraction"}


class NodeType(str, enum.Enum):
    """
    Canonical node types accepted by `Node` and `create_sc_net`.

    ``NodeType`` is a ``str`` subclass, so every existing comparison against a
    literal string (``node.node_type == "demand"``, ``"supplier" in node.node_type``,
    ``node.node_type.lower()``) continues to work unchanged. Users can pass
    either a plain string (case-insensitive, via `_missing_`) or a
    `NodeType` member:

    ```python
    scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier")
    scm.Supplier(env=env, ID="S1", name="S1", node_type=scm.NodeType.SUPPLIER)
    ```

    Some types are different names for the same kind of node:
    ``"manufacturer"`` and ``"factory"`` both create a manufacturer, and
    ``"warehouse"``, ``"distributor"``, ``"retailer"``, ``"store"`` and
    ``"shop"`` all create an `InventoryNode`. ``"supplier"`` creates a
    raw-material supplier and ``"infinite_supplier"`` an infinite supplier.

    `create_sc_net` looks up which class to create for each type in a
    table (``_NODE_DISPATCH`` in ``utilities.py``). To add a new node type,
    add it to this enum and add an entry to that table.
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
    Turn a value that is "a number, or a zero-arg function returning a number"
    into a zero-arg function.

    Many constructors accept either a plain number or a zero-arg function (lead
    times, arrival intervals, recovery times). The earlier version simply did

    ```python
    if not callable(value):
        value = lambda val=value: val
    ```

    which accepted any function at all — even a class like ``int`` or a
    generator function — so the later ``value()`` call could fail deep inside a
    running simulation, far from where the mistake was made. This helper avoids
    that by calling the function once when it is set up and checking the result
    is a real number, so a bad value is reported right away, at construction,
    with a clear message naming the parameter at fault.

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
        demand_placed (list): Orders this node placed, as [number of orders, units].
        fulfillment_received (list): Orders this node received (they arrived), as [number of orders, units].
        demand_received (list): Orders placed with this node (replenishment orders and customer orders), as [number of orders, units].
        demand_fulfilled (list): Orders this node fulfilled (sent out in full), as [number of orders, units].
        shortage (list): How many units this node was missing when orders arrived, as [number of orders, units]. A running total that is never reduced. ``orders_shortage`` is kept as an old name for it (§6.6).
        backorder (list): Orders this node owes right now, as [number of orders, units].
        inventory_level (float): The inventory level at the last update.
        inventory_waste (float): Expired units thrown away so far.
        inventory_carry_cost (float): Holding cost so far.
        inventory_spend_cost (float): What this node paid for the units it received.
        transportation_cost (float): Transportation cost of this node's orders.
        destroyed_qty (float): Units destroyed in disruptions (see Inventory.destroy).
        destroyed_value (float): Value of the destroyed units; part of ``node_cost``.
        node_cost (float): Everything this node spent (the sum of its costs).
        revenue (float): Sell price times the units this node fulfilled.
        profit (float): Revenue minus node cost.
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
        "destroyed_qty", "destroyed_value",
        "node_cost", "revenue", "profit",
    ]
    # Attributes that contribute to ``node_cost``. ``node_cost`` itself is NOT
    # listed — it is the derived sum (see ``update_stats``). ``destroyed_value``
    # is the monetary loss from disruption-driven inventory destruction
    # (Inventory.destroy + Node._disruption_impact_fn); rolling it into
    # node_cost makes the impact visible in profit without callers needing
    # to know about a separate "loss" line.
    _cost_components = ["inventory_carry_cost", "inventory_spend_cost", "transportation_cost", "destroyed_value"]

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
            demand_placed (list): Orders this node placed, as [number of orders, units].
            fulfillment_received (list): Orders this node received (they arrived), as [number of orders, units].
            demand_received (list): Orders placed with this node (replenishment orders and customer orders), as [number of orders, units].
            demand_fulfilled (list): Orders this node fulfilled (sent out in full), as [number of orders, units].
            shortage (list): How many units this node was missing when orders arrived, as [number of orders, units]. A running total that is never reduced. ``orders_shortage`` is kept as an old name for it (§6.6).
            backorder (list): Orders this node owes right now, as [number of orders, units].
            inventory_level (float): The inventory level at the last update.
            inventory_waste (float): Expired units thrown away so far.
            inventory_carry_cost (float): Holding cost so far.
            inventory_spend_cost (float): What this node paid for the units it received.
            transportation_cost (float): Transportation cost of this node's orders.
            node_cost (float): Everything this node spent (the sum of its costs).
            revenue (float): Sell price times the units this node fulfilled.
            profit (float): Revenue minus node cost.
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
        self.demand_placed = [0,0] # orders this node placed: [number of orders, units]
        self.fulfillment_received = [0,0] # orders that arrived at this node
        self.demand_received = [0,0] # orders placed with this node
        self.demand_fulfilled = [0,0] # orders this node sent out in full
        # ``shortage`` (was ``orders_shortage`` before §6.6) — renamed to
        # match ``supplychainnet["shortage"]`` so the same vocabulary applies
        # at both the node and network level. ``orders_shortage`` is kept as
        # a read-only alias / accepted ``update_stats`` kwarg for back-compat.
        self.shortage = [0,0] # units missing when orders arrived (running total)
        self.backorder = [0,0] # orders this node owes right now
        self.inventory_level = 0 # inventory level at the last update
        self.inventory_waste = 0 # expired units thrown away so far
        self.inventory_carry_cost = 0 # holding cost so far
        self.inventory_spend_cost = 0 # what this node paid for the units it received
        self.transportation_cost = 0 # transportation cost of this node's orders
        # Units destroyed in disruptions (for example, a flood at a
        # warehouse). ``destroyed_qty`` counts the units; ``destroyed_value``
        # is their value, and is part of ``node_cost`` (see _cost_components).
        self.destroyed_qty = 0
        self.destroyed_value = 0
        self.node_cost = 0 # everything this node spent
        self.revenue = 0 # sell price times the units this node fulfilled
        self.profit = 0 # revenue minus node cost

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
        # Pass 2 — a safety net for any counter that is not in the tracked list
        # but used to be reset by the old "reset everything" sweep.
        for key, value in vars(self).items():
            if key.startswith("_") or key in self._stats_keys:
                continue
            if isinstance(value, list):
                setattr(self, key, [0, 0])
            elif isinstance(value, (int, float)):
                setattr(self, key, 0)
        # Some counters live on the Inventory object, not on Statistics, so they
        # have to be reset here by hand. If you add a new Inventory counter that
        # should reset, add it to this block (or move the counter onto
        # Statistics by listing it in _stats_keys).
        if hasattr(self.node, 'inventory'):
            self.node.inventory.carry_cost = 0
            self.node.inventory.waste = 0

    @property
    def orders_shortage(self):
        """Old name kept for compatibility — same as `shortage`. Returns the same list, so changing it also changes ``shortage``."""
        return self.shortage

    @orders_shortage.setter
    def orders_shortage(self, value):
        self.shortage = value

    def update_stats(self,**kwargs):
        """
        Update the statistics with the given keyword arguments.

        Parameters:
            **kwargs: keyword arguments containing the statistics to update.
                ``orders_shortage=`` is still accepted as the old name for
                ``shortage=`` (the attribute was renamed).

        Attributes:
            None

        Returns:
            None
        """
        # ``orders_shortage`` was renamed to ``shortage``. Older code (and some
        # examples) still pass the old name, so map it onto the new one here and
        # let both names update the same counter. If a caller passes both, the
        # new name wins.
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
    The `RawMaterial` class represents a raw material: what a raw-material supplier mines and a manufacturer
    uses up. A raw-material supplier mines `extraction_quantity` units every `extraction_time` time units, at
    `mining_cost` per unit, and sells them at `cost` per unit. (The parameter names say "extraction"; it means
    the same as mining.)

    Parameters:
        ID (str): ID of the raw material.
        name (str): Name of the raw material.
        extraction_quantity (float): Units mined in each round of mining.
        extraction_time (float): Time units each round of mining takes.
        mining_cost (float): Cost of mining one unit.
        cost (float): The raw-material supplier's sell price per unit (what a buyer pays for one unit).

    Attributes:
        _info_keys (list): Keys to include in the info dictionary.
        _stats_keys (list): Keys to include in the statistics dictionary.
        ID (str): ID of the raw material.
        name (str): Name of the raw material.
        extraction_quantity (float): Units mined in each round of mining.
        extraction_time (float): Time units each round of mining takes.
        mining_cost (float): Cost of mining one unit.
        cost (float): The raw-material supplier's sell price per unit.

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
            extraction_quantity (float): units mined in each round of mining
            extraction_time (float): time units each round of mining takes
            mining_cost (float): cost of mining one unit
            cost (float): the raw-material supplier's sell price per unit

        Attributes:
            _info_keys (list): list of keys to include in the info dictionary
            _stats_keys (list): list of keys to include in the statistics dictionary
            ID (str): ID of the raw material (alphanumeric)
            name (str): name of the raw material
            extraction_quantity (float): units mined in each round of mining
            extraction_time (float): time units each round of mining takes
            mining_cost (float): cost of mining one unit
            cost (float): the raw-material supplier's sell price per unit

        Returns:
            None
        """
        validate_positive("Extraction quantity", extraction_quantity)
        validate_non_negative("Extraction time", extraction_time)
        validate_non_negative("Mining Cost", mining_cost)
        validate_positive("Cost", cost)
        self.ID = ID # ID of the raw material (alphanumeric)
        self.name = name # name of the raw material
        self.extraction_quantity = extraction_quantity # units mined in each round of mining
        self.extraction_time = extraction_time # time units each round of mining takes
        self.mining_cost = mining_cost # cost of mining one unit
        self.cost = cost # the raw-material supplier's sell price per unit

class Product(NamedEntity, InfoMixin):
    """
    The `Product` class represents the product that a manufacturer makes and other sites buy and sell. It
    defines the manufacturing cost, the manufacturing time, the sell price, and the raw materials needed to
    make one unit. A manufacturer makes it in production batches: at most `batch_size` units at a time, each
    production batch taking `manufacturing_time`.

    Parameters:
        ID (str): ID of the product.
        name (str): Name of the product.
        manufacturing_cost (float): Manufacturing cost per unit.
        manufacturing_time (float): Time units to make one production batch.
        sell_price (float): Sell price per unit.
        raw_materials (list): List of (raw material, quantity) tuples: the raw materials needed to make one unit.
        batch_size (int): The most units made in one production batch.
        buy_price (float, optional): Buy price per unit (default is 0).

    Attributes:
        _info_keys (list): Keys to include in the info dictionary.
        _stats_keys (list): Keys to include in the statistics dictionary.
        ID (str): ID of the product.
        name (str): Name of the product.
        manufacturing_cost (float): Manufacturing cost per unit.
        manufacturing_time (float): Time units to make one production batch.
        sell_price (float): Sell price per unit.
        buy_price (float): Buy price per unit.
        raw_materials (list): List of (raw material, quantity) tuples needed to make one unit.
        batch_size (int): The most units made in one production batch.

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
            manufacturing_cost (float): Manufacturing cost per unit
            manufacturing_time (float): Time units to make one production batch
            sell_price (float): Sell price per unit
            buy_price (float, optional): Buy price per unit (default is 0)
            raw_materials (list): List of (raw material, quantity) tuples: the raw materials needed to make one unit
            batch_size (int): The most units made in one production batch

        Attributes:
            _info_keys (list): List of keys to include in the info dictionary
            _stats_keys (list): List of keys to include in the statistics dictionary
            ID (str): ID of the product
            name (str): Name of the product
            manufacturing_cost (float): Manufacturing cost per unit
            manufacturing_time (float): Time units to make one production batch
            sell_price (float): Sell price per unit
            buy_price (float): Buy price per unit (default is 0)
            raw_materials (list): List of (raw material, quantity) tuples needed to make one unit
            batch_size (int): The most units made in one production batch

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
        self.manufacturing_time = manufacturing_time # time units to make one production batch
        self.sell_price = sell_price # sell price per unit
        self.buy_price = buy_price # buy price per unit (default: 0)
        self.raw_materials = raw_materials # (raw material, quantity) tuples needed to make one unit
        self.batch_size = batch_size # the most units made in one production batch

class InventoryReplenishment(InfoMixin, NamedEntity):
    """
    The `InventoryReplenishment` class is the base for all replenishment policies in SupplyNetPy: the rules a
    site follows to decide when to place a replenishment order and how many units to order.

    This class is not used directly. Each policy is a subclass, such as the (s, S) policy (`SSReplenishment`),
    the (R, Q) policy (`RQReplenishment`) and the periodic policy (`PeriodicReplenishment`).

    A subclass overrides the `run` method with its rule. `run` runs as a SimPy process for the whole
    simulation. A policy usually checks the node's inventory position each time the node's inventory drops
    (the `inventory_drop` event), or at fixed intervals.

    **How a custom policy should talk to its node.** A policy should use these four helper methods instead of reaching
    into the node's internal attributes:

    - `self.node.position()` — the inventory position: inventory level plus units in transit, minus units the
      node still owes (to other sites and to waiting customers).
    - `self.node.place_order(quantity)` — picks a supplier using the node's supplier-selection policy and places
      the replenishment order. This replaces calling `selection_policy.select(...)` and
      `env.process(process_order(...))` yourself.
    - `self.node.wait_for_drop()` — used as `yield from self.node.wait_for_drop()` to wait until the inventory
      drops; on wake-up it safely replaces the `inventory_drop` event with a fresh one.
    - `Link.available_quantity()` — lets a supplier-selection policy check a supplier's inventory level without
      reading `link.source.inventory.level` directly.

    Sticking to these helpers keeps a policy from depending on how a particular node is built, so it works with any
    future `Node` type that offers the same methods.

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
        The policy's rule. Each subclass overrides this method.
        """
        pass

class SSReplenishment(InventoryReplenishment):
    """
    Implements the (s, S) replenishment policy, with an optional safety stock.

    When the inventory position falls to the reorder point `s` or below, the node places a replenishment order
    big enough to bring its inventory position back up to the order-up-to level `S`. If a safety stock is
    given, it is added to both `s` and `S`. The inventory position is checked each time the node's inventory
    drops, or every `period` time units if a period is given, starting after an optional first review delay.
    The supplier is chosen by the node's supplier-selection policy.

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
        first_review_delay (float): Time units to wait before the first check of the inventory position.
        period (float): Time units between checks. 0 (the default) means checking each time the inventory drops.

    Functions:
        __init__: Initializes the replenishment policy object.
        run: Checks the inventory position and places replenishment orders by the (s, S) rule.
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
            first_review_delay (float): time units to wait before the first check of the inventory position
            period (float): time units between checks; 0 means checking each time the inventory drops

        Returns:
            None
        """
        validate_non_negative("Reorder point (s)", params['s']) # s must not be negative
        validate_positive("Order-up-to level (S)", params['S']) # S must be positive
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
        Runs the (s, S) policy for the whole simulation: checks the inventory position and places
        replenishment orders.

        Parameters:
            None

        Attributes: 
            s (float): reorder point
            S (float): order-up-to level

        Returns:
            None    
        """
        s, S = self.params['s'], self.params['S']  # get the reorder point and order-up-to level
        # (__init__ has already checked that s is not above S.)

        if 'safety_stock' in self.params: # check if safety_stock is specified
            validate_positive("Safety stock", self.params['safety_stock'])
            self.name = "min-max with safety replenishment (s, S, safety_stock)"
            s += self.params['safety_stock']
            S += self.params['safety_stock']

        if self.first_review_delay > 0: # wait before the first check, if a first review delay is given
            yield self.env.timeout(self.first_review_delay)

        while True: # check for the whole simulation
            self.node.logger.info(f"{self.env.now:.4f}:{self.node.ID}: Inventory levels:{self.node.inventory.level}, on hand:{self.node.inventory.on_hand}")
            position = self.node.position()
            if position <= s:
                self.node.place_order(S - position)

            if self.period == 0: # no period: check again when the inventory drops
                yield from self.node.wait_for_drop()
            elif self.period: # a period is given: check again after it
                yield self.env.timeout(self.period)

class RQReplenishment(InventoryReplenishment):
    """
    Implements the (R, Q) replenishment policy.

    When the inventory position falls to the reorder point `R` or below, the node places a replenishment order
    of a fixed `Q` units.

    The inventory position is checked each time the node's inventory drops if `period` is 0 (the default), or
    every `period` time units if a positive period is given. An optional first review delay sets how long to
    wait before the first check.

    The supplier is chosen by the node's supplier-selection policy. If the supplier cannot fill the order at
    once, a shortage is recorded at the supplier.

    Parameters:
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Parameters for the replenishment policy: R, Q, and the optional first_review_delay and period.

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        env (simpy.Environment): Simulation environment.
        node (object): Node to which this policy applies.
        params (dict): Replenishment policy parameters (R, Q, optional delays and period).
        name (str): Replenishment policy name.
        first_review_delay (float): Time units to wait before the first check of the inventory position.
        period (float): Time units between checks. 0 (the default) means checking each time the inventory drops.

    Functions:
        __init__: Initializes the (R, Q) replenishment policy object.
        run: Checks the inventory position and places a replenishment order when it reaches the reorder point.
    """
    _info_keys = InventoryReplenishment._info_keys + ["name", "first_review_delay", "period"]

    def __init__(self, env, node, params):
        """ 
        Initialize the (R, Q) replenishment policy object.

        Parameters:
            env (simpy.Environment): Simulation environment.
            node (object): Node to which this policy applies.
            params (dict): Replenishment policy parameters: R, Q, and the optional first_review_delay and period.

        Attributes:
            _info_keys (list): List of keys to include in the info dictionary.
            env (simpy.Environment): Simulation environment.
            node (object): Node to which this policy applies.
            params (dict): Replenishment policy parameters (R, Q, optional delays and period).
            name (str): Replenishment policy name.
            first_review_delay (float): Time units to wait before the first check of the inventory position.
            period (float): Time units between checks. 0 means checking each time the inventory drops.

        Returns:
            None
        """
        validate_non_negative("Reorder point (R)", params['R']) # R must not be negative
        validate_positive("Order quantity (Q)", params['Q'])  # Q must be positive
        super().__init__(env, node, params)
        self.name = "RQ replenishment (R, Q)"
        self.first_review_delay = params.get('first_review_delay', 0)
        self.period = params.get('period', 0)
        
    def run(self):
        """
        Runs the (R, Q) policy for the whole simulation: places a replenishment order of `Q` units whenever
        the inventory position is at the reorder point `R` or below.

        If a period is given, the inventory position is checked every `period` time units. Otherwise it is
        checked each time the node's inventory drops.

        Parameters:
            None

        Attributes:
            R (float): Reorder point.
            Q (float): Units in each replenishment order.
        
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
    Implements the periodic replenishment policy: every `T` time units, the node places a replenishment order of
    `Q` units, whatever its inventory position. If a safety stock is given and the inventory level is below it,
    the order also includes the units needed to bring the inventory level back up to the safety stock. An
    optional first review delay sets how long to wait before the first order.

    The supplier is chosen by the node's supplier-selection policy. If the supplier cannot fill the order at
    once, a shortage is recorded at the supplier.

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
        first_review_delay (float): Time units to wait before the first replenishment order.

    Functions:
        __init__: Initializes the replenishment policy object.
        run: Places a replenishment order of Q units every T time units.
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
            first_review_delay (float): time units to wait before the first replenishment order

        Returns:
            None
        """
        validate_positive("Replenishment period (T)", params['T'])  # T must be positive
        validate_positive("Replenishment quantity (Q)", params['Q'])  # Q must be positive
        super().__init__(env, node, params)
        self.name = "Periodic replenishment (T, Q)"
        self.first_review_delay = params.get('first_review_delay', 0)

    def run(self):
        """
        Runs the periodic policy for the whole simulation: places a replenishment order every `T` time units.

        Parameters:
            None

        Attributes:
            T (float): time units between replenishment orders
            Q (float): units in each replenishment order

        Returns:
            None
        """
        T, Q = self.params['T'], self.params['Q']  # the period and the order size
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
            yield self.env.timeout(T) # wait for the next period

class SupplierSelectionPolicy(InfoMixin, NamedEntity):
    """
    The base for all supplier-selection policies: the rules a site follows to choose which of its suppliers
    receives a replenishment order.

    A site reaches each of its suppliers over a link, so the policy works with links: the site's suppliers are
    the links in `node.suppliers`, and `select` returns the link to the chosen supplier (the supplier itself is
    `link.source`).

    There are two modes:
    (1) "dynamic": the supplier is chosen afresh for every replenishment order.
    (2) "fixed": the first supplier chosen is remembered and used for every later order (another one is used
        only while the link to the remembered supplier is disrupted).

    Each policy is a subclass that overrides the `select` method with its own rule.

    Parameters:
        node (object): Node for which the supplier selection policy is applied.
        mode (str): Supplier selection mode. Must be "dynamic" or "fixed".

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        node (object): Node for which the supplier selection policy is applied.
        mode (str): Supplier selection mode ("dynamic" or "fixed").
        fixed_supplier (Link): In "fixed" mode, the link to the remembered supplier (None until the first choice).

    Functions:
        __init__: Initializes the supplier selection policy object.
        select: The policy's rule for choosing a supplier; each subclass overrides it.
        validate_suppliers: Checks that the node has at least one supplier.
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
            fixed_supplier (Link): In "fixed" mode, the link to the remembered supplier (None until the first choice).

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
        The policy's rule for choosing a supplier. Each subclass overrides this method.

        Parameters:
            order_quantity (float): Units in the replenishment order.

        Returns:
            None
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def validate_suppliers(self):
        """
        Checks that the node has at least one supplier (a link into it).

        Returns:
            None
        """
        if not self.node.suppliers:
            global_logger.error(f"{self.node.ID} must have at least one supplier.")
            raise ValueError(f"{self.node.ID} must have at least one supplier.")

    def _active_suppliers(self):
        """
        Return the links to the suppliers whose link is not disrupted right now.
        If every link is disrupted, return all of them instead, so the calling
        policy always has at least one to choose from. In that case
        ``process_order`` will not send the order over the disrupted link, and
        the replenishment policy will try again at its next check.

        Returns:
            list: The links that are not disrupted, or all links if every one is.
        """
        active = [s for s in self.node.suppliers if s.status == "active"]
        return active if active else self.node.suppliers

    def _apply_mode(self, selected):
        """
        Apply the "fixed" or "dynamic" mode to a freshly chosen supplier.

        In ``"fixed"`` mode the first chosen supplier is remembered and used for
        later orders. But if the link to the remembered supplier is disrupted,
        the policy uses ``selected`` for this order instead (without forgetting
        the remembered one): "fixed" means *prefer this supplier*, not *stop
        ordering while its link is disrupted*. The remembered supplier is used
        again as soon as its link recovers.

        Parameters:
            selected (Link): The link to the supplier chosen by the subclass's own rule.

        Returns:
            Link: in fixed mode, the link to the remembered supplier (or ``selected``
                while that link is disrupted); in dynamic mode, ``selected``.
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
    A supplier-selection policy that chooses the first supplier in the node's list of suppliers (the order in
    which the links were created), skipping suppliers whose link is disrupted.

    In dynamic mode, the choice is made afresh for each replenishment order.
    In fixed mode (the default for this policy), the first choice is remembered and used for later orders.

    Parameters:
        node (object): Node to which this supplier selection policy applies.
        mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "fixed").

    Attributes:
        node (object): Node to which this policy applies.
        mode (str): Supplier selection mode.
        fixed_supplier (Link): In "fixed" mode, the link to the remembered supplier.
        name (str): Name of the selection policy.
        _info_keys (list): List of keys to include in the info dictionary.

    Functions:
        __init__: Initializes the selection policy with node and mode.
        select: Chooses the first supplier whose link is not disrupted.
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
        Chooses the first supplier whose link is not disrupted right now.

        Suppliers whose link is disrupted are skipped. If every link is
        disrupted, the policy chooses the first supplier in the list
        (``process_order`` then does not send the order over the disrupted link,
        and the replenishment policy tries again at its next check).

        In dynamic mode, the choice is made afresh for each order. In fixed
        mode, the first choice is remembered and used for later orders; while
        its link is disrupted, the policy uses another supplier whose link is
        not, without forgetting the remembered one.

        Parameters:
            order_quantity (float): Units in the replenishment order.

        Returns:
            Link: The link to the chosen supplier.
        """
        self.validate_suppliers()
        candidates = self._active_suppliers()
        selected = candidates[0]
        return self._apply_mode(selected)

class SelectAvailable(SupplierSelectionPolicy):
    """
    A supplier-selection policy that chooses the first supplier whose inventory level can fill the whole order.

    If no supplier can fill the whole order, it chooses the first supplier in the list. Suppliers whose link is
    disrupted are skipped. In dynamic mode the choice is made afresh for each replenishment order; in fixed mode
    the first choice is remembered and used for later orders.

    Parameters:
        node (object): Node to which this supplier selection policy applies.
        mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

    Attributes:
        node (object): Node to which this policy applies.
        mode (str): Supplier selection mode.
        fixed_supplier (Link): In "fixed" mode, the link to the remembered supplier.
        name (str): Name of the selection policy.
        _info_keys (list): List of keys to include in the info dictionary.

    Functions:
        __init__: Initializes the selection policy with node and mode.
        select: Chooses the first supplier whose inventory level can fill the whole order.

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
        Chooses the first supplier whose inventory level can fill the whole order.

        Suppliers whose link is disrupted are skipped first. Among those left,
        it chooses the first one whose inventory level is at least
        ``order_quantity``; if none is, it chooses the first of them (the order
        then waits at that supplier until enough units arrive, and the supplier
        records a shortage and a backorder). If every link is disrupted, it
        chooses the first supplier in the list, and ``process_order`` does not
        send the order over the disrupted link.

        In fixed mode, the first choice is remembered and used for later
        orders. While its link is disrupted, the policy uses another supplier
        whose link is not, without forgetting the remembered one.

        Parameters:
            order_quantity (float): Units in the replenishment order.

        Returns:
            Link: The link to the chosen supplier.
        """
        self.validate_suppliers()
        candidates = self._active_suppliers()
        available = [s for s in candidates if s.available_quantity() >= order_quantity]
        selected = available[0] if available else candidates[0]
        return self._apply_mode(selected)

class SelectCheapest(SupplierSelectionPolicy):
    """
    A supplier-selection policy that chooses the supplier with the lowest transportation cost (the `cost` of
    the link to it).

    Suppliers whose link is disrupted are skipped. In dynamic mode the choice is made afresh for each
    replenishment order; in fixed mode the first choice is remembered and used for later orders.

    Parameters:
        node (object): Node to which this supplier selection policy applies.
        mode (str): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

    Attributes:
        node (object): Node to which this policy applies.
        mode (str): Supplier selection mode.
        fixed_supplier (Link): In "fixed" mode, the link to the remembered supplier.
        name (str): Name of the selection policy.
        _info_keys (list): List of keys to include in the info dictionary.

    Functions:
        __init__: Initializes the supplier selection policy.
        select: Chooses the supplier with the lowest transportation cost.
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
        Chooses the supplier with the lowest transportation cost.

        Suppliers whose link is disrupted are skipped first. If every link is
        disrupted, the policy chooses the cheapest of all suppliers
        (``process_order`` then does not send the order over the disrupted link,
        and the replenishment policy tries again at its next check).

        In fixed mode, the first choice is remembered and used for later
        orders. While its link is disrupted, the policy uses another supplier
        whose link is not, without forgetting the remembered one.

        Parameters:
            order_quantity (float): Units in the replenishment order.

        Returns:
            Link: The link to the chosen supplier.
        """
        self.validate_suppliers()
        candidates = self._active_suppliers()
        selected = min(candidates, key=lambda s: s.cost)
        return self._apply_mode(selected)

class SelectFastest(SupplierSelectionPolicy):
    """
    A supplier-selection policy that chooses the supplier with the shortest lead time.

    The lead time of each link is drawn once when the choice is made, so if lead times are random, the choice
    can differ from one order to the next. Suppliers whose link is disrupted are skipped. In dynamic mode the
    choice is made afresh for each replenishment order; in fixed mode the first choice is remembered and used
    for later orders.

    Parameters:
        node (object): Node to which this supplier selection policy applies.
        mode (str, optional): Supplier selection mode, either "dynamic" or "fixed" (default: "dynamic").

    Attributes:
        node (object): Node to which this policy applies.
        mode (str): Supplier selection mode ("dynamic" or "fixed").
        fixed_supplier (Link): In "fixed" mode, the link to the remembered supplier.
        name (str): Name of the selection policy.
        _info_keys (list): List of keys to include in the info dictionary.

    Functions:
        __init__: Initializes the supplier selection policy and sets the selection mode.
        select: Chooses the supplier with the shortest lead time.
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
        Chooses the supplier with the shortest lead time.

        Suppliers whose link is disrupted are skipped first. If every link is
        disrupted, the policy chooses the fastest of all suppliers
        (``process_order`` then does not send the order over the disrupted link,
        and the replenishment policy tries again at its next check).

        In fixed mode, the first choice is remembered and used for later
        orders. While its link is disrupted, the policy uses another supplier
        whose link is not, without forgetting the remembered one.

        Parameters:
            order_quantity (float): Units in the replenishment order.

        Returns:
            Link: The link to the chosen supplier.
        """
        self.validate_suppliers()
        candidates = self._active_suppliers()
        selected = min(candidates, key=lambda s: s.lead_time())
        return self._apply_mode(selected)

# ---------------------------------------------------------------------------
# Disruption impact helpers
#
# A disruption can have many causes (natural disaster, power cut, political
# event, contamination), and each can affect the units at a node differently.
# ``Node`` offers a single ``disruption_impact`` setting that takes either a
# built-in name (handled here) or a function you supply that receives the node.
# The effect runs once, at the moment the node's status changes from active to
# inactive inside ``Node.disruption`` — not once per time unit. So an effect
# that should build up *during* the disruption (slow spoilage, ongoing theft)
# belongs in your own function that starts its own SimPy process; running an
# effect once per time unit here would wake the simulation up for nothing.
#
# Built-in options:
#   - "none" / None       — no effect on the units; only the status changes.
#   - "destroy_all"       — destroy all units at the node (and, for a
#                           manufacturer, its raw materials too: all physical
#                           units at the site are lost at once).
#   - "destroy_fraction"  — destroy ``loss fraction × inventory level``. The
#                           fraction can itself be a zero-arg function, so each
#                           disruption can destroy a different amount.
# ---------------------------------------------------------------------------

def _unit_destroyed_value(node) -> float:
    """
    The value of one destroyed unit, used to record ``destroyed_value``.

    Each kind of node values its units differently: an ``InventoryNode`` uses
    its ``buy_price``, a ``Manufacturer`` the ``buy_price`` of its ``Product``,
    and a raw-material supplier the ``cost`` of its ``RawMaterial``. This
    helper tries each in turn, so the impact functions do not need to know
    about every kind of node. It returns 0 when no price is set (for example,
    a node built only to study disruptions, with no costs); the callers then
    record ``destroyed_qty`` but no ``destroyed_value``.
    """
    if getattr(node, "buy_price", 0):
        return node.buy_price
    product = getattr(node, "product", None)
    if product is not None and getattr(product, "buy_price", 0):
        return product.buy_price
    raw = getattr(node, "raw_material", None)
    if raw is not None and getattr(raw, "cost", 0):
        return raw.cost
    return 0


def _destroy_all_impact(node) -> None:
    """
    Built-in effect for ``disruption_impact="destroy_all"``: destroy all units at
    the node and record the loss in its statistics. For a `Manufacturer` this
    also clears its raw materials (``raw_inventory_counts``), not just its
    product `Inventory`. For an infinite supplier (``level == inf``) this does
    nothing — there is no real pile to destroy.
    """
    inv = getattr(node, "inventory", None)
    unit_value = _unit_destroyed_value(node)
    if inv is not None and inv.level != float('inf'):
        destroyed = inv.destroy(amount=None, reason="destroy_all")
        if destroyed > 0 and hasattr(node, "stats"):
            node.stats.update_stats(destroyed_qty=destroyed,
                                    destroyed_value=destroyed * unit_value)
    # A manufacturer counts its raw materials in a plain dictionary, not in its
    # inventory, so they are cleared by hand here. Each raw material is valued
    # at its own cost (more accurate than the product's value used above).
    raw_counts = getattr(node, "raw_inventory_counts", None)
    if raw_counts:
        raw_cost_lookup = {}
        # A manufacturer's suppliers are links whose ``source`` is a
        # raw-material supplier; its ``raw_material`` holds the cost per unit.
        for link in getattr(node, "suppliers", []):
            rm = getattr(getattr(link, "source", None), "raw_material", None)
            if rm is not None:
                raw_cost_lookup[rm.ID] = rm.cost
        total_qty = 0
        total_value = 0
        for rm_id, qty in list(raw_counts.items()):
            if qty <= 0:
                continue
            total_qty += qty
            total_value += qty * raw_cost_lookup.get(rm_id, 0)
            raw_counts[rm_id] = 0
        if total_qty > 0:
            node.logger.info(
                f"{node.env.now:.4f}:{node.ID}: {total_qty} units of raw materials "
                f"destroyed (destroy_all)."
            )
            if hasattr(node, "stats"):
                node.stats.update_stats(destroyed_qty=total_qty,
                                        destroyed_value=total_value)


def _destroy_fraction_impact(fraction_fn):
    """
    Build the effect for ``disruption_impact="destroy_fraction"``. ``fraction_fn``
    is a zero-arg function returning a number between 0 and 1; it is called
    each time a disruption starts, so each disruption can destroy a different
    fraction (for example, a flood severity drawn at random).
    """
    def _impact(node) -> None:
        inv = getattr(node, "inventory", None)
        if inv is None or inv.level == float('inf'):
            return
        fraction = fraction_fn()
        validate_number(name="disruption_loss_fraction", value=fraction)
        if fraction < 0 or fraction > 1:
            global_logger.error(
                f"{node.ID}: disruption_loss_fraction must be in [0, 1]; got {fraction}."
            )
            raise ValueError(
                f"disruption_loss_fraction must be in [0, 1]; got {fraction}."
            )
        destroyed = inv.destroy(amount=inv.level * fraction, reason="destroy_fraction")
        if destroyed > 0 and hasattr(node, "stats"):
            node.stats.update_stats(
                destroyed_qty=destroyed,
                destroyed_value=destroyed * _unit_destroyed_value(node),
            )
    return _impact


def _resolve_disruption_impact(impact, loss_fraction):
    """
    Turn the ``disruption_impact`` setting into one function ``f(node) -> None``
    (or ``None`` for no effect).

    Accepted values:
      * ``None`` or ``"none"`` (any letter case) — returns ``None``.
      * ``"destroy_all"`` — returns `_destroy_all_impact`.
      * ``"destroy_fraction"`` — used with ``loss_fraction`` (a number, or a
        zero-arg function returning one); returns a function that destroys
        ``fraction × inventory level`` each time a disruption starts.
      * Any other function — used as it is. It must take one argument (the node).

    Raises:
        ValueError: For an unknown name, or for a value that is neither a
            string, a function nor None.
    """
    if impact is None:
        return None
    if isinstance(impact, str):
        key = impact.lower()
        if key == "none":
            return None
        if key == "destroy_all":
            return _destroy_all_impact
        if key == "destroy_fraction":
            fn = ensure_numeric_callable("disruption_loss_fraction", loss_fraction)
            return _destroy_fraction_impact(fn)
        global_logger.error(
            f"Unknown disruption_impact preset: {impact!r}. "
            f"Use 'destroy_all', 'destroy_fraction', None, or a callable."
        )
        raise ValueError(f"Unknown disruption_impact preset: {impact!r}.")
    if callable(impact):
        return impact
    global_logger.error(
        f"disruption_impact must be a string, a callable, or None; got {type(impact).__name__}."
    )
    raise ValueError(
        f"disruption_impact must be a string, a callable, or None; got {type(impact).__name__}."
    )


class Node(NamedEntity, InfoMixin):
    """
    Represents a node in the supply chain network: a raw-material supplier, a manufacturer, a warehouse,
    distributor or retailer, or a customer demand. This is the base class they all share. It handles
    disruption and recovery, and logging.

    A node can be disrupted at random (each time unit, a disruption starts with probability `failure_p`) or at
    the times given by `node_disrupt_time`. While disrupted, its status is "inactive"; it recovers after
    `node_recovery_time`. The subclasses also keep statistics (`stats`): orders, shortages, costs, revenue and
    profit.

    Sites can use the built-in replenishment policies ((s, S), (R, Q) and periodic) or a custom one made by
    subclassing `InventoryReplenishment`, and the built-in supplier-selection policies (`SelectFirst`,
    `SelectAvailable`, `SelectCheapest`, `SelectFastest`) or a custom one made by subclassing
    `SupplierSelectionPolicy`.

    For the node types, see `NodeType`.

    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): Unique node ID.
        name (str): Node name.
        node_type (str): Type of the node.
        failure_p (float, optional): Disruption probability: the chance, each time unit, that a disruption starts.
        node_disrupt_time (callable, optional): Time units until the next disruption (a number, or a function
            returning one each time).
        node_recovery_time (callable, optional): Time units a disruption lasts (a number, or a function
            returning one each time).
        logging (bool, optional): Flag to enable/disable logging.
        disruption_impact (str | callable | None, optional): What a disruption does to the units at the node,
            at the moment it starts. ``None`` (default) leaves them untouched. Built-in names:
            ``"destroy_all"`` destroys all units at the node (and a manufacturer's raw materials);
            ``"destroy_fraction"`` destroys ``disruption_loss_fraction × inventory level``. For any other
            effect (partial spoilage, contamination, capacity damage), pass your own function
            ``f(node) -> None``. It runs once per disruption; for an effect that builds up during the
            disruption, start a SimPy process inside the function.
        disruption_loss_fraction (float | callable, optional): Fraction between 0 and 1, used with
            ``disruption_impact="destroy_fraction"``. May be a zero-arg function, so each disruption can
            destroy a different fraction.
        **kwargs: Additional arguments for the logger.

    Attributes:
        _info_keys (list): List of keys to include in the info dictionary.
        env (simpy.Environment): simulation environment
        ID (str): ID of the node (alphanumeric)
        name (str): name of the node
        node_type (str): type of the node
        node_failure_p (float): disruption probability (the chance, each time unit, that a disruption starts)
        node_status (str): status of the node: "active", or "inactive" while disrupted
        node_disrupt_time (callable): function giving the time units until the next disruption
        node_recovery_time (callable): function giving the time units a disruption lasts
        disruption_impact: The ``disruption_impact`` setting as given (a name, a function, or None).
        _disruption_impact_fn (callable | None): The function that ``disruption()`` calls when a disruption starts.
        logger (GlobalLogger): logger object
        suppliers (list): The links to this node's suppliers (links whose ``sink`` is this node); filled in by
            ``Link.__init__`` through ``add_supplier_link``.

    Functions:
        __init__: Initializes the node object, checks the parameters, and sets up logging and disruptions if needed.
        disruption: Disrupts the node and recovers it, for the whole simulation.
        add_supplier_link: Registers a link from one of this node's suppliers (called by Link.__init__).
        position: The inventory position, used by replenishment policies.
        place_order: Chooses a supplier with the supplier-selection policy and places a replenishment order.
        wait_for_drop: Waits until the inventory drops (use with ``yield from``).
    """
    _info_keys = ["ID", "name", "node_type", "failure_p", "node_status", "logging", "disruption_impact"]

    def __init__(self, env: simpy.Environment,
                 ID: str,
                 name: str,
                 node_type: str,
                 failure_p:float = 0.0,
                 node_disrupt_time: Callable = None,
                 node_recovery_time: Callable = lambda: 1,
                 logging: bool = True,
                 rng: random.Random = None,
                 disruption_impact=None,
                 disruption_loss_fraction=1.0,
                 **kwargs) -> None:
        """
        Initialize the node object.
        
        Parameters:
            env (simpy.Environment): Simulation environment.
            ID (str): Unique node ID.
            name (str): Node name.
            node_type (str): Type of the node.
            failure_p (float, optional): Disruption probability: the chance, each time unit, that a disruption starts.
            node_disrupt_time (callable, optional): Time units until the next disruption (a number or a function).
            node_recovery_time (callable, optional): Time units a disruption lasts (a number or a function).
            logging (bool, optional): Flag to enable/disable logging.
            **kwargs: Additional arguments for the logger.

        Attributes:
            _info_keys (list): List of keys to include in the info dictionary.  
            env (simpy.Environment): simulation environment
            ID (str): ID of the node (alphanumeric)
            name (str): name of the node
            node_type (str): type of the node
            node_failure_p (float): disruption probability
            node_status (str): status of the node: "active", or "inactive" while disrupted
            node_disrupt_time (callable): function giving the time units until the next disruption
            node_recovery_time (callable): function giving the time units a disruption lasts
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
        # ``ensure_numeric_callable`` turns a plain number into a function that
        # returns it, and calls the function once to check that it returns a
        # number. A mistake (for example, passing a class such as ``int``) is
        # then reported here, instead of crashing later in the middle of a run.
        node_recovery_time = ensure_numeric_callable("node_recovery_time", node_recovery_time)
        if node_disrupt_time is not None:
            node_disrupt_time = ensure_numeric_callable("node_disrupt_time", node_disrupt_time)
        self.env = env  # simulation environment
        self.ID = ID  # ID of the node (alphanumeric)
        self.name = name  # name of the node
        self.node_type = node_type  # type of the node (see NodeType)
        self.node_failure_p = failure_p  # disruption probability
        self.node_status = "active"  # "active", or "inactive" while disrupted
        self.node_disrupt_time = node_disrupt_time  # function: time units until the next disruption
        self.node_recovery_time = node_recovery_time  # function: time units a disruption lasts
        self.rng = rng if rng is not None else _rng  # random number generator for random disruptions; the library's default if none is given
        self.suppliers = []  # links to this node's suppliers; filled in by Link.__init__ through add_supplier_link
        # Work out the disruption-impact function once, here. The setting as
        # given is kept as ``disruption_impact`` (shown by get_info); the
        # function that runs when a disruption starts is ``_disruption_impact_fn``.
        self.disruption_impact = disruption_impact
        self._disruption_impact_fn = _resolve_disruption_impact(disruption_impact, disruption_loss_fraction)

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

        if(self.node_failure_p>0 or self.node_disrupt_time): # start the disruption process if the node can be disrupted
            self.env.process(self.disruption()) 
    
    def disruption(self):
        """
        Disrupts the node (its status becomes "inactive") and recovers it after the
        recovery time, for the whole simulation. Disruptions start either at the
        times given by ``node_disrupt_time``, or at random: each time unit, a
        disruption starts with probability ``failure_p``.

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
                    # The disruption-impact effect runs once, at the moment the
                    # node switches from active to inactive. Effects that should
                    # build up *during* the disruption belong in a custom
                    # function that starts its own process; checking once per
                    # time unit here would wake the simulation up for nothing.
                    if self._disruption_impact_fn is not None:
                        self._disruption_impact_fn(self)
                else:
                    # Random disruption: check once per time unit, so
                    # ``node_failure_p`` acts as the chance that a disruption
                    # starts in any one time unit. The ``yield env.timeout(1)`` below MUST run
                    # whether or not this check succeeds. If it were skipped on a
                    # miss, the ``while True`` loop would spin without advancing
                    # simulation time, repeating the check over and over until one
                    # finally succeeds — which would disrupt the node almost
                    # immediately at t=0 no matter how small ``failure_p`` is.
                    if(self.rng.random() < self.node_failure_p):
                        self.node_status = "inactive"
                        self.logger.info(f"{self.env.now}:{self.ID}: Node disrupted.")
                        if self._disruption_impact_fn is not None:
                            self._disruption_impact_fn(self)
                    yield self.env.timeout(1)
            else:
                recovery_time = self.node_recovery_time() # get the recovery time
                validate_positive(name="node_recovery_time", value=recovery_time) # the recovery time must be positive
                yield self.env.timeout(recovery_time)
                self.node_status = "active"
                self.logger.info(f"{self.env.now}:{self.ID}: Node recovered from disruption.")

    def add_supplier_link(self, link) -> None:
        """
        Register a link from one of this node's suppliers (a link whose ``sink``
        is this node).

        This is the one supported way to attach a Link to a Node.
        Supplier-selection policies look through ``node.suppliers`` to choose
        which supplier receives a replenishment order, so a Link must be
        registered here for the node to send orders over it.

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
    # The three methods below are what replenishment policies (the built-in
    # ones and any subclass of InventoryReplenishment) use to work with their
    # node, so a policy never needs to read or change the node's internal
    # attributes (`inventory.on_hand`, `stats.backorder`, `selection_policy`,
    # `process_order`, `inventory_drop`). ``place_order`` and ``wait_for_drop``
    # need a node that places replenishment orders (``InventoryNode`` and
    # ``Manufacturer``); ``position`` also works on a ``Supplier``, which has
    # an inventory and statistics too.
    def position(self) -> float:
        """
        The inventory position, used by replenishment policies.

        The inventory position is what the node can count on: its inventory
        level plus the units in transit to it, minus the units it still owes
        (to other sites and to waiting customers). Replenishment policies use
        this one value instead of working it out themselves, so the arithmetic
        stays in one place.

        ``inventory.on_hand`` already holds most of it. The node's backorders
        hold two kinds of waiting orders, and only one of them is subtracted
        here:

        - Replenishment orders from other sites. They were taken off
          ``on_hand`` when they were placed (those still waiting are in the
          inventory's line, see ``Inventory.waiting_site_orders``), so
          subtracting them again would count them twice and make the node order
          too much.
        - Customers waiting for units. They were not taken off ``on_hand``, so
          they are subtracted here.

        Returns:
            float: The inventory position.
        """
        customer_backorders = self.stats.backorder[1] - self.inventory.waiting_site_orders()
        return self.inventory.on_hand - customer_backorders

    def place_order(self, quantity) -> None:
        """
        Choose a supplier with this node's supplier-selection policy and place a
        replenishment order with it.

        This does in one call what a replenishment policy would otherwise do in
        two steps: ``selection_policy.select(...)`` and
        ``env.process(process_order(...))``. The order itself is handled by
        ``process_order``, which runs as its own SimPy process: it reduces the
        order to fit the node's capacity, does not send it if the link is
        disrupted, and records the order at the supplier. This method returns
        at once.

        Parameters:
            quantity (float): Units to order. ``process_order`` may still reduce
                this to fit the capacity, or not send the order if the link is
                disrupted.

        Returns:
            None
        """
        supplier = self.selection_policy.select(quantity)
        self.env.process(self.process_order(supplier, quantity))

    def wait_for_drop(self):
        """
        Wait until the node's inventory drops, then get ready for the next drop.

        Replenishment policies use it as ``yield from node.wait_for_drop()``.
        It waits on the node's ``inventory_drop`` event, which fires when the
        inventory drops. A SimPy event can fire only once, so after it fires it
        is replaced with a fresh one, ready for the next drop. Doing this here
        keeps that replacing step in one place.

        Yields:
            simpy.Event: The current ``inventory_drop`` event.
        """
        yield self.inventory_drop
        self.inventory_drop = self.env.event()

class Link(NamedEntity, InfoMixin):
    """
    Represents a link: the transport connection that carries goods from one site, its source (the supplier),
    to another, its sink (the buyer).

    Each link has a transportation cost (per order) and a lead time. A link can be disrupted at random (each
    time unit, a disruption starts with probability `link_failure_p`) or at the times given by
    `link_disrupt_time`; it recovers after `link_recovery_time`. While a link is disrupted, no new orders are
    sent over it; orders already in transit still arrive.

    Parameters:
        env (simpy.Environment): Simulation environment.
        ID (str): ID of the link.
        source (Node): The supplier: the site the goods come from.
        sink (Node): The buyer: the site the goods go to.
        cost (float): Transportation cost of each order sent over the link.
        lead_time (callable): Time units an order takes to arrive (a number, or a function returning one each time).
        link_failure_p (float): Disruption probability: the chance, each time unit, that a disruption starts.
        link_disrupt_time (callable): Time units until the next disruption (a number or a function).
        link_recovery_time (callable): Time units a disruption lasts (a number or a function).

    Attributes:
        env (simpy.Environment): Simulation environment.
        ID (str): ID of the link.
        source (Node): The supplier.
        sink (Node): The buyer.
        cost (float): Transportation cost of each order.
        lead_time (callable): Function giving the lead time of each order.
        link_failure_p (float): Disruption probability.
        status (str): Status of the link: "active", or "inactive" while disrupted.
        link_disrupt_time (callable): Function giving the time units until the next disruption.
        link_recovery_time (callable): Function giving the time units a disruption lasts.

    Functions:
        __init__: Initializes the link object and checks the parameters.
        disruption: Disrupts the link and recovers it, for the whole simulation.
        available_quantity: The supplier's inventory level.
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
        Initialize the link.

        Parameters:
            env (simpy.Environment): The simulation environment.
            ID (str): Unique identifier for the link.
            source (Node): The supplier (the site the goods come from). Cannot be a customer demand.
            sink (Node): The buyer (the site the goods go to). Cannot be a raw-material supplier.
            cost (float): Transportation cost of each order sent over the link. Must not be negative.
            lead_time (callable): Lead time of each order: a number, or a function returning one (it can be random). Cannot be None.
            link_failure_p (float, optional): Disruption probability: the chance, each time unit, that a disruption starts. Default is 0.0.
            link_disrupt_time (callable, optional): Time units until the next disruption (a number or a function). If given, it is used instead of link_failure_p.
            link_recovery_time (callable, optional): Time units a disruption lasts (a number or a function). Default is 1 time unit.

        Attributes:
            env (simpy.Environment): The simulation environment.
            ID (str): The ID of the link.
            source (Node): The supplier.
            sink (Node): The buyer.
            name (str): Readable name of the link, made from the source and sink IDs.
            cost (float): Transportation cost of each order.
            lead_time (callable): Function giving the lead time of each order.
            link_failure_p (float): Disruption probability.
            status (str): Status of the link: "active", or "inactive" while disrupted.
            link_recovery_time (callable): Function giving the time units a disruption lasts.
            link_disrupt_time (callable): Function giving the time units until the next disruption.

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
        self.source = source  # the supplier
        self.sink = sink  # the buyer
        self.name = f"{self.source.ID} to {self.sink.ID}"  # name of the link
        self.cost = cost  # transportation cost of each order
        self.lead_time = lead_time  # function giving the lead time of each order
        self.link_failure_p = link_failure_p  # disruption probability
        self.status = "active"  # "active", or "inactive" while disrupted
        self.link_recovery_time = link_recovery_time  # function: time units a disruption lasts
        self.link_disrupt_time = link_disrupt_time  # function: time units until the next disruption, if given
        self.rng = rng if rng is not None else _rng  # random number generator for random disruptions; the library's default if none is given

        # Register this link with its sink (the buyer) through
        # ``add_supplier_link``, rather than changing ``sink.suppliers``
        # directly. Every Node starts with an empty ``suppliers`` list, so this
        # works for any valid sink.
        self.sink.add_supplier_link(self)
        if(self.link_failure_p>0 or self.link_disrupt_time): # start the disruption process if the link can be disrupted
            self.env.process(self.disruption())
    
    def disruption(self):
        """
        Disrupts the link (its status becomes "inactive") and recovers it after the recovery time, for the whole
        simulation. Disruptions start either at the times given by ``link_disrupt_time``, or at random: each time
        unit, a disruption starts with probability ``link_failure_p``.

        Parameters:
            None

        Attributes:
            None

        Returns:
            None
        """
        # Orders already in transit over this link are not stopped when the
        # link is disrupted; only *new* orders are not sent (see the link checks
        # in InventoryNode.process_order and Manufacturer.process_order).
        # Stopping orders in transit would need each one tracked as its own
        # process; that is left for later.
        while True:
            if(self.status=="active"):
                if(self.link_disrupt_time): # if link_disrupt_time is provided, wait for the disruption time
                    disrupt_time = self.link_disrupt_time() # get the disruption time
                    validate_positive(name="link_disrupt_time", value=disrupt_time) # the disruption time must be positive
                    yield self.env.timeout(disrupt_time)
                    self.status = "inactive" # change the link status to inactive
                    global_logger.info(f"{self.env.now}:{self.ID}: Link disrupted.")
                else:
                    # Random disruption: check once per time unit. The
                    # ``yield env.timeout(1)`` below must run whether or not the
                    # check succeeds (same as in ``Node.disruption``). Without
                    # it, a miss would spin through ``while True`` without
                    # advancing simulation time, making ``link_failure_p`` turn
                    # into near-certain disruption at t=0.
                    if(self.rng.random() < self.link_failure_p):
                        self.status = "inactive"
                        global_logger.info(f"{self.env.now}:{self.ID}: Link disrupted.")
                    yield self.env.timeout(1)
            else:
                recovery_time = self.link_recovery_time() # get the recovery time
                validate_positive(name="link_recovery_time", value=recovery_time) # the recovery time must be positive
                yield self.env.timeout(recovery_time)
                self.status = "active"
                global_logger.info(f"{self.env.now}:{self.ID}: Link recovered from disruption.")

    def available_quantity(self) -> float:
        """
        The supplier's inventory level: how many units it has right now.

        Supplier-selection policies (such as ``SelectAvailable``) use it to
        compare suppliers without reading ``link.source.inventory.level``
        directly.

        Returns:
            float: The supplier's inventory level.
        """
        return self.source.inventory.level

class _InventoryGet(ContainerGet):
    """
    A request to take units out of an `_InventoryContainer` (internal helper for `Inventory`).

    `Inventory.get` creates one of these for every order that takes units out
    of an inventory: a replenishment order from a buyer, or a customer order.
    "Request" is the SimPy word for it: if there are not enough units yet,
    the request waits until enough arrive. On top of what SimPy keeps for
    every request (mainly the number of units asked for), it carries two
    labels:

    - ``site_order``: True when the request is a replenishment order from
      another site, as opposed to a customer order.
      `Inventory.waiting_site_orders` uses it to tell those orders apart from
      other requests that are waiting.
    - ``batches``: for perishable goods, the batches the units came from, as
      ``(manufacturing_date, quantity)``. It starts empty and is filled in by
      `_InventoryContainer._do_get` at the moment the units leave the
      inventory (see `_InventoryContainer` for why). For goods that are not
      perishable it stays empty.
    """

    def __init__(self, container, amount, site_order=False):
        # These must be set before SimPy's own setup below: if the inventory
        # level is high enough, SimPy hands the units out during that setup,
        # and `_InventoryContainer._do_get` then writes into `batches`.
        self.site_order = site_order
        self.batches = []
        super().__init__(container, amount)

class _InventoryContainer(simpy.Container):
    """
    The SimPy container that holds the units of an `Inventory` (internal helper).

    Every `Inventory` uses one, for perishable and non-perishable goods alike;
    it is reached as ``inventory.inventory``. It is a ``simpy.Container`` with
    two additions. For goods that are not perishable the first addition does
    nothing, so the container behaves exactly like a plain
    ``simpy.Container``, apart from `remove_now`.

    **How a SimPy container hands out units.** Asking for units creates a
    request. If the inventory level is high enough, SimPy takes the units out
    at once. If not, the request waits in a line (``get_queue``), and each
    time units are added, SimPy goes through the line in order and serves
    every request it now can. Whether a request is served at once or several
    time units later, the units leave the inventory in one place: the method
    ``_do_get``.

    **Why perishable goods need more.** A perishable inventory keeps two
    records of the same units: the inventory level (kept by this container),
    and the list of batches (``Inventory.perish_queue``, oldest first). The
    two must always agree. Picture an inventory holding 5 units made at time
    0, and a replenishment order for 20 that has to wait until 30 new units
    (made at time 2) arrive. When it is served, the order must get the 5 old
    units and 15 of the new ones, and both records must then say "15 units
    made at time 2". If the batches were picked when the order was *placed*,
    the order would get batches for only the 5 units in the inventory at that
    moment, and the two records would no longer agree.

    **Addition 1: the batches are picked in** ``_do_get``. At the same moment
    the units leave the inventory, the same number of units is taken off the
    list of batches, oldest first, and stored on the request
    (`_InventoryGet.batches`). The picking itself is done by the inventory's
    own method (`Inventory._pick_oldest_batches`), passed in as
    ``pick_batches``; for goods that are not perishable it returns an empty
    list.

    **Addition 2:** `remove_now` **removes units without waiting in line.** It
    is for units that must leave the inventory right away, even when an order
    is waiting: `Inventory.remove_expired` uses it to throw away expired units,
    and `Inventory.destroy` uses it to remove units lost in a disruption
    (perishable or not). An ordinary request would wait behind the waiting
    order, so the units would stay in the inventory in the meantime: expired
    units could then be handed to that order, and destroyed units would only
    really disappear when the next delivery came in.

    Parameters:
        env (simpy.Environment): Simulation environment.
        capacity (float): The largest inventory level the container can hold.
        init (float): The inventory level at the start.
        pick_batches (callable): Called as ``pick_batches(amount)`` each time
            units leave the inventory. Takes that many units off the list of
            batches, oldest first, and returns them as a list of
            ``(manufacturing_date, quantity)``.
    """

    # Make `get(...)` create an `_InventoryGet` instead of SimPy's plain request.
    get = BoundClass(_InventoryGet)

    def __init__(self, env, capacity, init, pick_batches):
        super().__init__(env, capacity=capacity, init=init)
        self._pick_batches = pick_batches

    def _do_get(self, event):
        # SimPy calls this to try to serve a request: straight away when the
        # request is made, and again each time units are added while it waits.
        # It is the same as simpy.Container._do_get, plus one line: the batches
        # are picked here, at the moment the units leave the inventory.
        if self._level >= event.amount:
            self._level -= event.amount
            event.batches.extend(self._pick_batches(event.amount))
            event.succeed()
            return True
        return None  # not enough units yet: the request keeps waiting

    def remove_now(self, amount):
        """
        Remove units from the inventory at once, without waiting in line.

        Used by `Inventory.remove_expired` (expired units) and
        `Inventory.destroy` (units lost in a disruption). Requests already
        waiting stay where they are and are served later, from later
        deliveries. The caller takes the same units off the list of batches
        itself, so the two records still agree.

        Parameters:
            amount (float): units to remove; reduced to the inventory level if larger.

        Returns:
            float: the units removed.
        """
        amount = min(amount, self._level)
        if amount > 0:
            # SimPy would normally check here whether a request waiting to
            # *add* units can now go ahead. There never is one:
            # Inventory.put never adds more than the free capacity.
            self._level -= amount
        return max(amount, 0)

class Inventory(NamedEntity, InfoMixin):
    """
    The `Inventory` class holds the units at a node and its records about them. It keeps the inventory level
    within the capacity, keeps the inventory position (``on_hand``), and tells the node when its inventory drops,
    so that its replenishment policy can check whether to order. For perishable goods it keeps the list of
    batches and throws away expired units. It also works out the holding cost, and can record the inventory
    level once per time unit.

    Parameters:
        env (simpy.Environment): Simulation environment.
        capacity (float): The largest inventory level the node can hold.
        initial_level (float): Inventory level at the start.
        node (Node): Node to which this inventory belongs.
        replenishment_policy (InventoryReplenishment): The node's replenishment policy.
        holding_cost (float): Holding cost per unit per time unit.
        shelf_life (float): Shelf life of perishable goods, in time units.
        inv_type (str): Type of the inventory, either "non-perishable" or "perishable".
        record_inv_levels (bool): If True, record the inventory level once per time unit (in ``instantaneous_levels``).

    Attributes:
        _info_keys (list): Keys included in the information dictionary.
        _stats_keys (list): Keys included in the statistics dictionary.
        env (simpy.Environment): Simulation environment.
        capacity (float): The largest inventory level the node can hold.
        init_level (float): Inventory level at the start.
        level (float): Current inventory level.
        on_hand (float): Despite its name, not the units physically here: the inventory position before units owed to waiting customers are taken off (inventory level, plus units in transit, minus units owed to other sites). See ``Node.position``.
        inv_type (str): Inventory type ("non-perishable" or "perishable").
        holding_cost (float): Holding cost per unit per time unit.
        carry_cost (float): Holding cost so far.
        replenishment_policy (InventoryReplenishment): The node's replenishment policy.
        inventory (simpy.Container): The SimPy container that holds the units (an ``_InventoryContainer``).
        last_update_t (float): Time of the last holding-cost update.
        shelf_life (float): Shelf life of perishable goods, in time units (perishable goods only).
        perish_queue (list): The list of batches, as ``(manufacturing_date, quantity)`` tuples, kept as a heap (Python's ``heapq``) so the oldest batch (the first to expire) is always at index 0. ``put`` adds a batch; a batch leaves the list (oldest first) at the moment its units leave the inventory, so the list always adds up to the inventory level.
        perish_changed (simpy.Event): Wake-up signal for ``remove_expired``. ``put`` fires it when a new batch becomes the oldest one (or arrives while the list is empty), so ``remove_expired`` works out the next expiry again instead of checking every time unit. Replaced with a fresh event on each wake-up.
        waste (float): Expired units thrown away so far.
        instantaneous_levels (list): ``(time, inventory level)`` pairs, recorded once per time unit if ``record_inv_levels`` is True.

    Functions:
        __init__: Initializes the inventory object.
        waiting_orders: Units asked for by orders still waiting at this inventory.
        waiting_site_orders: The same, for replenishment orders from other sites only.
        record_inventory_levels: Records the inventory level once per time unit.
        put: Adds units (for perishable goods, as a new batch with its manufacturing date).
        get: Takes units out for an order (oldest batch first, for perishable goods).
        remove_expired: Throws away expired units (perishable goods only).
        update_carry_cost: Adds the holding cost since the last update.
        destroy: Removes units lost in a disruption.
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
            capacity (float): The largest inventory level the node can hold.
            initial_level (float): Inventory level at the start.
            node (Node): Node to which this inventory belongs.
            replenishment_policy (InventoryReplenishment): The node's replenishment policy.
            holding_cost (float): Holding cost per unit per time unit.
            shelf_life (float): Shelf life of perishable goods, in time units.
            inv_type (str): Type of the inventory, either "non-perishable" or "perishable".
            record_inv_levels (bool): If True, record the inventory level once per time unit.

        Attributes:
            _info_keys (list): Keys included in the information dictionary.
            _stats_keys (list): Keys included in the statistics dictionary.
            env (simpy.Environment): Simulation environment.
            capacity (float): The largest inventory level the node can hold.
            init_level (float): Inventory level at the start.
            level (float): Current inventory level.
            on_hand (float): Despite its name, not the units physically here: the inventory position before units owed to waiting customers are taken off (inventory level, plus units in transit, minus units owed to other sites). See ``Node.position``.
            inv_type (str): Inventory type ("non-perishable" or "perishable").
            holding_cost (float): Holding cost per unit per time unit.
            carry_cost (float): Holding cost so far.
            replenishment_policy (InventoryReplenishment): The node's replenishment policy.
            inventory (simpy.Container): The SimPy container that holds the units (an ``_InventoryContainer``).
            last_update_t (float): Time of the last holding-cost update.
            shelf_life (float): Shelf life of perishable goods, in time units (perishable goods only).
            perish_queue (list): The list of batches, as ``(manufacturing_date, quantity)`` tuples, kept as a heap (Python's ``heapq``) so the oldest batch (the first to expire) is always at index 0. ``put`` adds a batch; a batch leaves the list (oldest first) at the moment its units leave the inventory, so the list always adds up to the inventory level.
            waste (float): Expired units thrown away so far.
            instantaneous_levels (list): ``(time, inventory level)`` pairs, recorded once per time unit.

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
        self.on_hand = initial_level # the inventory position (see on_hand above); starts at the initial level
        self.inv_type = inv_type
        self.holding_cost = holding_cost
        self.carry_cost = 0 # holding cost so far
        self.replenishment_policy = replenishment_policy
        # The SimPy container that holds the units. For perishable goods it
        # picks the batches for each order at the moment the units leave the
        # inventory (see _InventoryContainer).
        self.inventory = _InventoryContainer(env=self.env, capacity=capacity, init=self.init_level,
                                pick_batches=self._pick_oldest_batches)
        self.last_update_t = self.env.now # last time the holding cost was updated
        
        if self.inv_type == "perishable":
            validate_positive("Shelf life", shelf_life)
            self.shelf_life = shelf_life
            self.perish_queue = [(0, initial_level)]  # the initial units count as made at time 0
            self.waste = 0
            # Wake-up signal for the ``remove_expired`` helper. ``put`` fires
            # this event when a newly added batch becomes the oldest one (so the
            # next expiry comes sooner), and the helper makes a fresh event each
            # time it wakes — the same pattern as ``Node.wait_for_drop``.
            self.perish_changed = self.env.event()
            self.env.process(self.remove_expired())

        self.instantaneous_levels = []
        if record_inv_levels:
            self.env.process(self.record_inventory_levels())  # record the inventory level once per time unit

    @property
    def level(self):
        """Current inventory level, read from the SimPy container that holds the units."""
        return self.inventory.level

    @property
    def capacity(self):
        """The largest inventory level the node can hold, read from the SimPy container."""
        return self.inventory.capacity

    def waiting_orders(self):
        """
        How many units are asked for by orders still waiting at this inventory.

        An order the inventory cannot fill right away (for example, a
        replenishment order bigger than the inventory level) joins a line and
        is served, in turn, when enough units arrive. Orders are served strictly
        in the order they arrived, so an order can also wait behind an earlier
        one. Besides replenishment orders from other sites, the line can hold
        other orders made with `get`. All of these units have already been
        taken off `on_hand` but have not left the inventory yet. (Expired and
        destroyed units never wait in this line: they are removed at once.)

        Returns:
            float: the units asked for by all waiting orders, or 0 if none are waiting.
        """
        return sum(request.amount for request in self.inventory.get_queue)

    def waiting_site_orders(self):
        """
        How many units are owed to other sites whose replenishment orders are still waiting at this inventory.

        Only the orders made with `get(..., site_order=True)` count. These
        orders are also part of the node's backorders.

        Returns:
            float: the units asked for by the waiting replenishment orders from other sites, or 0 if none are waiting.
        """
        return sum(request.amount for request in self.inventory.get_queue
                   if getattr(request, "site_order", False))

    def record_inventory_levels(self):
        """
        Record the inventory level once per time unit, in ``instantaneous_levels``.

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
        Add units to the inventory. For perishable goods, they are added as a new
        batch with their manufacturing date.

        Parameters:
            amount (float): units to add
            manufacturing_date (float): the units' manufacturing date (needed for perishable goods only)

        Returns:
            float: the units actually accepted. Less than ``amount`` when they do
                not all fit within the capacity, and 0 when the inventory is
                infinite, already full, or ``amount <= 0``. Callers that keep
                ``on_hand`` must take any shortfall (``requested - accepted``)
                back off it.
        """
        # Use ``>=``, not ``==``. When the inventory is filled exactly to
        # capacity, floating-point rounding can leave the level a hair ABOVE
        # capacity (e.g. 99.99000000000001 for a capacity of 99.99). A plain
        # ``== capacity`` check would miss that case, so ``>=`` is used to
        # correctly spot an inventory that is already full.
        if self.inventory.level == float('inf') or amount <= 0 or self.inventory.level >= self.capacity:
            return 0

        if amount + self.inventory.level > self.capacity: # adjust amount if it exceeds capacity
            old_amount = amount
            amount = self.capacity - self.inventory.level
            # Safety net: if the rounding above left the level just over
            # capacity, this leftover space comes out as zero or negative.
            # SimPy's Container.put rejects a non-positive amount with an error,
            # so we treat the inventory as already full and simply accept nothing.
            if amount <= 0:
                return 0
            self.node.logger.warning(f"Inventory capacity exceeded. Only {amount} of {old_amount} units added to inventory.")

        if self.inv_type == "perishable":
            if manufacturing_date is None:
                self.node.logger.error("Manufacturing date must be provided for perishable inventory.")
                raise ValueError("Manufacturing date must be provided for perishable inventory.")
            # ``perish_queue`` is a heap ordered by manufacturing date, so the
            # oldest batch (the first to expire) is always at position 0. Adding
            # a batch with ``heapq.heappush`` is fast.
            new_batch = (manufacturing_date, amount)
            heapq.heappush(self.perish_queue, new_batch)
            # Only wake ``remove_expired`` when this new batch becomes the oldest
            # one (position 0) — either because the list was empty, or because
            # this batch is older than every batch already there. For ordinary
            # deliveries (newer dates than what is there) the oldest batch does
            # not change, so ``remove_expired`` is left alone.
            if self.perish_queue[0] is new_batch and not self.perish_changed.triggered:
                self.perish_changed.succeed()
        self.update_carry_cost()  # add the holding cost up to now, before the level changes
        self.inventory.put(amount)
        if(not self.node.inventory_raised.triggered):
            self.node.inventory_raised.succeed()  # signal that inventory has been raised
        return amount

    def get(self, amount: float, site_order: bool = False):
        """
        Take units out of the inventory for an order. For perishable goods, the
        units come from the oldest batch first.

        If the inventory level is too low, the order waits until enough units
        arrive (see `_InventoryContainer`). Either way, the units are taken off
        the inventory position (``on_hand``) straight away.

        Parameters:
            amount (float): units to take.
            site_order (bool): True for a replenishment order from another site,
                False for a customer order (see `waiting_site_orders`).
                Defaults to False.

        Returns:
            tuple: (SimPy event, list of (manufacturing_date, quantity)). The
                event fires when the order is served. The list holds the batches
                the units came from (perishable goods only; empty otherwise). It
                is filled in when the units really leave the inventory: at once
                if the inventory level is high enough, or later, when an order
                that had to wait is served. So read it after yielding the event.
        """
        # The order is labelled, so that among the orders still waiting the
        # node can tell replenishment orders from other sites apart from
        # customer orders (see `waiting_site_orders`).
        if self.inventory.level == float('inf'):
            get_event = self.inventory.get(amount, site_order=site_order)
            return get_event, get_event.batches

        self.update_carry_cost()
        get_event = self.inventory.get(amount, site_order=site_order)
        self.on_hand -= amount  # the inventory position drops at once
        self._signal_inventory_drop()
        return get_event, get_event.batches

    def _signal_inventory_drop(self):
        """
        Tell the node that its inventory dropped (or is about to, for an order that waits).

        Its replenishment policy (if it has one) checks whether to place a
        replenishment order, a raw-material supplier whose inventory was full
        starts mining again, and a manufacturer that stopped because its
        inventory was full carries on.
        """
        # Every node is told, not only those with a replenishment policy: a
        # raw-material supplier has none, and without this signal it would
        # never mine again once its inventory had been full.
        inventory_drop = getattr(self.node, "inventory_drop", None)
        if inventory_drop is not None and not inventory_drop.triggered:
            inventory_drop.succeed()
        # Only manufacturers have this method.
        wake_production = getattr(self.node, "wake_production", None)
        if wake_production is not None:
            wake_production()

    def _pick_oldest_batches(self, amount):
        """
        Take `amount` units off the list of batches, oldest first.

        This is the "oldest units first" rule: an order gets the units with the
        least shelf life left, then units from the next oldest batch, and so on.
        It only updates the list of batches (``perish_queue``); the caller takes
        the same units out of the inventory at the same moment, so the two
        always agree.

        Parameters:
            amount (float): units to take.

        Returns:
            list: the batches taken, as (manufacturing_date, quantity). Empty for
                goods that are not perishable, and for an infinite supplier.
        """
        if self.inv_type != "perishable" or self.inventory.level == float('inf'):
            return []
        taken = []
        x_amount = amount
        while x_amount > 0 and self.perish_queue:
            mfg_date, qty = self.perish_queue[0]  # peek at the oldest batch
            if qty <= x_amount:
                if qty > 0:
                    taken.append((mfg_date, qty))
                x_amount -= qty
                heapq.heappop(self.perish_queue)  # remove the oldest batch (fast)
            else:
                taken.append((mfg_date, x_amount))
                # We only need part of this oldest batch. Replace it with the
                # same date and the smaller leftover quantity. It is still the
                # oldest batch, so the heap order stays correct.
                self.perish_queue[0] = (mfg_date, qty - x_amount)
                x_amount = 0
        return taken

    def remove_expired(self):
        """
        Throw away expired units (perishable goods only).

        This runs as a SimPy process for the whole simulation. Instead of
        checking every time unit, it sleeps exactly until the oldest batch is
        due to expire. It wakes up early through the ``perish_changed`` event
        when ``put`` adds a batch that becomes the new oldest one (or arrives
        while the list is empty), so a batch that expires sooner is handled
        without waiting for the old timer. After each wake-up it creates a fresh ``perish_changed`` event so
        an already-used one cannot fire again by mistake — the same pattern as
        ``Node.wait_for_drop``.
        """
        while True:
            if not self.perish_queue:
                # Nothing to expire: wait until ``put`` adds a batch.
                yield self.perish_changed
                self.perish_changed = self.env.event()
                continue
            # The oldest batch sits at position 0 of the heap, so one look is
            # enough to find when the next expiry is due. ``max(0, ...)`` keeps
            # the sleep time from going negative for a batch whose expiry time
            # has already passed (e.g. one given an old manufacturing date).
            next_expiry = self.perish_queue[0][0] + self.shelf_life
            sleep_dt = max(0, next_expiry - self.env.now)
            timer = self.env.timeout(sleep_dt)
            result = yield timer | self.perish_changed
            if self.perish_changed in result:
                # A new oldest batch arrived (or the list was empty and now has
                # a batch). Make a fresh event and start over from the new
                # oldest batch — even if the timer also fired, the next loop will
                # see a sleep time of 0 and remove the expired units right away.
                self.perish_changed = self.env.event()
                continue
            # The timer fired — remove every batch that has now expired. The
            # test is written as ``env.now >= mfg_date + shelf_life`` to match
            # how the expiry time was worked out above. The other form,
            # ``env.now - mfg_date >= shelf_life``, is unreliable with
            # fractional shelf lives because of floating-point rounding (e.g.
            # ``9.2 - 8`` becomes ``1.1999999999999993`` and fails a ``>= 1.2``
            # check), which could make this helper skip the removal and loop
            # forever at the same time.
            #
            # Expired units are thrown away at once, even when an order is
            # waiting. Every batch in the list is still physically in the
            # inventory (a batch leaves the list only when its units leave the
            # inventory), so the units are there to remove. Queueing the
            # removal behind a waiting order would leave the expired units in
            # the inventory, where that order could take them once it is served.
            while self.perish_queue and self.env.now >= self.perish_queue[0][0] + self.shelf_life:
                mfg_date, qty = heapq.heappop(self.perish_queue)  # take the oldest batch off the list
                if qty > 0:
                    self.update_carry_cost()
                    removed = self.inventory.remove_now(qty)  # and the same units out of the inventory
                    self.on_hand -= removed
                    self.waste += removed  # expired units thrown away so far
                    self.node.logger.info(f"{self.env.now:.4f}: {removed} units expired (Mgf date:{mfg_date}).")
                    self._signal_inventory_drop()

    def update_carry_cost(self):
        """
        Add the holding cost since the last update: inventory level × time units
        since then × holding cost per unit per time unit. It is called before
        every change of the inventory level, so each stretch of time is charged
        at the level the inventory really had.
        """
        carry_period = self.env.now - self.last_update_t
        self.carry_cost += self.inventory.level * (carry_period) * self.holding_cost  # holding cost for the time since the last update
        self.last_update_t = self.env.now  # update the last update time

    def destroy(self, amount: float = None, reason: str = "disruption") -> float:
        """
        Destroy units now, for a physical loss in a disruption (natural
        disaster, contamination, theft, etc.).

        Removes the units right away, even when orders are waiting,
        so the caller (usually a ``Node`` disruption handler) sees the new
        ``level`` on the very next line. The method does **not** fire
        ``inventory_drop`` for nodes with a replenishment policy — that event is
        what triggers replenishment policies, and new orders are already blocked
        while the node is ``"inactive"``. Firing it here would line up
        replenishment orders that all go out the moment the node recovers, which
        is exactly the kind of unwanted coupling we removed earlier. It does
        wake a raw-material supplier (which then mines to refill its inventory,
        as it does whenever its inventory drops) and a manufacturer (which can
        make more now that there is free capacity).

        For perishable goods the oldest batches are destroyed first, the same as
        for orders: destroying part of the oldest batch lowers its quantity but
        keeps its manufacturing date. ``waste`` (which counts only expired
        units) is left unchanged — destroyed units are counted separately, in
        ``Statistics.destroyed_qty`` / ``destroyed_value``, which the caller
        fills in.

        For an infinite supplier (``level == float('inf')``) this does nothing:
        it stands for an unlimited supply of raw material, not a real pile that
        can be destroyed.

        Parameters:
            amount (float, optional): Units to destroy. ``None`` (default)
                destroys all units (the whole inventory level). Values larger
                than the inventory level are reduced to it. Zero or negative
                values do nothing.
            reason (str, optional): Free-form label written to the per-node
                logger so the trace makes the distinction between expiry,
                consumption, and destruction visible. Default ``"disruption"``.

        Returns:
            float: The units actually destroyed (``0`` in the cases above where
            nothing happens). Callers usually multiply this by the value of one
            unit to record ``destroyed_value`` on ``Statistics``.
        """
        if self.inventory.level == float('inf'):
            return 0  # infinite_supplier — nothing physical to destroy
        available = self.inventory.level
        if amount is None:
            amount = available
        amount = max(0.0, min(amount, available))
        if amount <= 0:
            return 0

        # Add the holding cost up to now, so the destroyed units are not
        # charged holding cost afterwards.
        self.update_carry_cost()

        # Destroy the oldest batches first (perishable goods only), and take the
        # same units out of the inventory at once — even when an order is
        # waiting. An ordinary request would wait in line behind that order,
        # so the units would stay in the inventory and would instead be
        # taken from the next delivery.
        self._pick_oldest_batches(amount)
        amount = self.inventory.remove_now(amount)
        self.on_hand -= amount
        self.node.logger.info(
            f"{self.env.now:.4f}:{self.node.ID}: {amount} units destroyed ({reason}). "
            f"Level={self.inventory.level}, on_hand={self.on_hand}."
        )
        # There is free capacity again. A raw-material supplier whose inventory
        # was full starts mining again, and a manufacturer that stopped because
        # its inventory was full carries on. Other nodes are not told, so their
        # replenishment policies do not place replenishment orders (see above).
        # Raw-material suppliers have no replenishment policy, so for them the
        # "inventory dropped" signal only restarts mining.
        if isinstance(self.node, Supplier):
            inventory_drop = getattr(self.node, "inventory_drop", None)
            if inventory_drop is not None and not inventory_drop.triggered:
                inventory_drop.succeed()
        wake_production = getattr(self.node, "wake_production", None)
        if wake_production is not None:
            wake_production()
        return amount

class Supplier(Node):
    """
    The `Supplier` class represents a raw-material supplier: a site at the start of the network that mines
    one raw material and sells it to manufacturers. It has no supplier of its own.

    A raw-material supplier with finite inventory (``node_type="supplier"``) mines
    `RawMaterial.extraction_quantity` units every `RawMaterial.extraction_time` time units, as long as its
    inventory is not full. When its inventory is full it stops, and starts mining again as soon as its
    inventory drops. An infinite supplier (``node_type="infinite_supplier"``) never runs out, so it does not
    mine at all.

    Parameters:
        env (simpy.Environment): simulation environment
        ID (str): unique identifier for the raw-material supplier
        name (str): name of the raw-material supplier
        node_type (str): "supplier" (finite inventory, mines raw material) or "infinite_supplier" (never runs out)
        capacity (float): the largest inventory level it can hold (ignored for an infinite supplier)
        initial_level (float): inventory level at the start (ignored for an infinite supplier)
        inventory_holding_cost (float): holding cost per unit per time unit
        raw_material (RawMaterial): the raw material it mines and sells
        **kwargs: any additional keyword arguments for the Node class and logger. Also accepts
            ``periodic_stats`` (bool, default False: if True, its statistics are updated every
            ``stats_period`` time units) and ``stats_period`` (float, default 1).

    Attributes:
        _info_keys (list): list of keys to include in the info dictionary.
        raw_material (RawMaterial): the raw material it mines and sells
        sell_price (float): sell price per unit (the raw material's ``cost``)
        inventory (Inventory): its inventory (infinite for an infinite supplier)
        inventory_drop (simpy.Event): fires when its inventory drops (finite inventory only)
        inventory_raised (simpy.Event): fires when units are added to its inventory (finite inventory only)
        stats (Statistics): its statistics. Besides the usual ones, ``total_raw_materials_mined`` (units
            mined so far) and ``total_material_cost`` (mining cost so far, part of ``node_cost``).

    Functions:
        __init__: Initializes the supplier object.
        behavior: Mines raw material whenever the inventory is not full (finite inventory only).
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
            ID (str): unique identifier for the raw-material supplier
            name (str): name of the raw-material supplier
            node_type (str): "supplier" (finite inventory, mines raw material) or "infinite_supplier" (never runs out)
            capacity (float): the largest inventory level it can hold (ignored for an infinite supplier)
            initial_level (float): inventory level at the start (ignored for an infinite supplier)
            inventory_holding_cost (float): holding cost per unit per time unit
            raw_material (RawMaterial): the raw material it mines and sells
            **kwargs: any additional keyword arguments for the Node class and logger. Also accepts
                ``periodic_stats`` (bool, default False: if True, its statistics are updated every
                ``stats_period`` time units) and ``stats_period`` (float, default 1).
        
        Attributes:
            _info_keys (list): list of keys to include in the info dictionary.
            raw_material (RawMaterial): the raw material it mines and sells
            sell_price (float): sell price per unit (the raw material's ``cost``)
            inventory (Inventory): its inventory (infinite for an infinite supplier)
            inventory_drop (simpy.Event): fires when its inventory drops (finite inventory only)
            inventory_raised (simpy.Event): fires when units are added to its inventory (finite inventory only)
            stats (Statistics): its statistics. Besides the usual ones, ``total_raw_materials_mined`` (units
                mined so far) and ``total_material_cost`` (mining cost so far, part of ``node_cost``).

        Returns:
            None
        """
        # Take the statistics options out of kwargs before passing the rest on
        # to Node. They belong to Statistics, but are accepted here so users can
        # ask for regular statistics updates without subclassing. By default a
        # raw-material supplier's statistics are not updated regularly.
        periodic_stats = kwargs.pop('periodic_stats', False)
        stats_period = kwargs.pop('stats_period', 1)
        if periodic_stats:
            validate_positive(name="stats_period", value=stats_period)
        super().__init__(env=env,ID=ID,name=name,node_type=node_type,**kwargs)
        self.raw_material = raw_material # the raw material it mines and sells
        self.sell_price = 0
        if(self.raw_material):
            self.sell_price = self.raw_material.cost # sell price per unit
        if(self.node_type!="infinite_supplier"):
            inventory_kwargs = {k: v for k, v in kwargs.items() if k not in _LOGGER_KWARGS and k not in _NODE_KWARGS}
            self.inventory = Inventory(env=self.env, capacity=capacity, initial_level=initial_level, node=self, holding_cost=inventory_holding_cost, replenishment_policy=None, **inventory_kwargs)
            self.inventory_drop = self.env.event()  # fires when the inventory drops
            self.inventory_raised = self.env.event() # fires when units are added
            if(self.raw_material):
                self.env.process(self.behavior()) # start mining
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
        Mine raw material for the whole simulation: `extraction_quantity` units every `extraction_time` time
        units, as long as the inventory is not full. When it is full, wait until the inventory drops, then mine
        again. A raw-material supplier mines a single raw material.

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
                if((self.inventory.level+self.raw_material.extraction_quantity)>self.inventory.capacity): # mine only what fits within the capacity
                    mined_quantity = self.inventory.capacity - self.inventory.level
                self.inventory.put(mined_quantity)
                self.stats.update_stats(total_raw_materials_mined=mined_quantity, total_material_cost=mined_quantity*self.raw_material.mining_cost)
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:Raw material mined/extracted. Inventory level:{self.inventory.level}")
                yield self.env.timeout(self.raw_material.extraction_time)
            else:
                # The inventory is full. Wait until it drops (a buyer takes
                # units, and Inventory.get signals inventory_drop), then mine
                # again, instead of checking the inventory every time unit.
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
            # Make a full copy so each InventoryNode that "sells" the same
            # Product can set its own sell_price / buy_price without changing the
            # original (or any other node's copy). Without the copy, two nodes
            # sharing one Product would overwrite each other's prices in the
            # assignments below.
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
        # Check the order against the shelf's capacity using the inventory
        # position (stock on the shelf and in transit, minus units owed to
        # waiting customers). Units owed to customers leave the shelf as soon
        # as the next delivery lands, so they do not take up space and must not
        # count against the capacity.
        gross = self.position()
        if(gross + reorder_quantity > self.inventory.capacity): # check if the inventory can accommodate the reordered quantity
                reorder_quantity = self.inventory.capacity - gross # if not, adjust reorder quantity to order only what can fit

        if reorder_quantity <= 0:
            return  # no need to place an order if reorder quantity is zero

        # A new order cannot be sent while the transport link is down. Shipments
        # that already passed this check are not interrupted — a down link only
        # blocks *new* orders. Checking here (before the shortage bookkeeping and
        # before pending_orders is increased) means a blocked order is not
        # counted as in transit and does not create a fake backorder on the
        # supplier. The replenishment policy tries again when inventory drops
        # again or on the next periodic check.
        if supplier.status == "inactive":
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Link:{supplier.ID} from {supplier.source.name} is disrupted. Order not placed.")
            return

        self.pending_orders += 1  # count this order as in flight; decremented when delivery completes (or supplier disrupted)

        if(supplier.source.node_status == "active"):
            # The supplier is short if it cannot fill the whole order from its
            # shelf right now. This is checked only here, once we know the
            # order is really placed: a supplier whose site is down never
            # receives the order, so it must not be counted as short for it.
            if supplier.source.inventory.level < reorder_quantity:
                shortage = reorder_quantity - supplier.source.inventory.level
                supplier.source.stats.update_stats(shortage=[1,shortage])

            self.stats.update_stats(demand_placed=[1,reorder_quantity],transportation_cost=supplier.cost)
            supplier.source.stats.update_stats(demand_received=[1,reorder_quantity])

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing inventory from supplier:{supplier.source.name}, order placed for {reorder_quantity} units.")
            event, man_date_ls = supplier.source.inventory.get(reorder_quantity, site_order=True)
            self.inventory.on_hand += reorder_quantity

            # The supplier's backorders show what it owes *right now*: an order
            # is counted while it waits for stock and removed once it is served.
            # The shelf hands out a request on the spot if it can, so a request
            # that has not been served at this point is really waiting — either
            # the shelf is short, or an earlier request is ahead of it in line.
            # (The whole order counts, because the shelf never sends part of a
            # request: it waits until it can send all of it.)
            order_waits = not event.triggered
            if order_waits:
                supplier.source.stats.update_stats(backorder=[1,reorder_quantity])
            yield event
            if order_waits:
                # Served at last: the supplier no longer owes this order.
                supplier.source.stats.update_stats(backorder=[-1,-reorder_quantity])

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.") # log the shipment
            lead_time = supplier.lead_time() # get the lead time from the supplier
            validate_non_negative(name="lead_time", value=lead_time) # check if lead_time is non-negative
            yield self.env.timeout(lead_time) # lead time for the order

            # Add the delivered units to the shelf, one fitting chunk at a time.
            #
            # Why loop instead of a single put()? A replenishment order can be
            # bigger than the free space on the shelf. This is normal, not a
            # mistake: when the node owes units to waiting customers (backorders),
            # the (s, S) policy orders enough to BOTH refill the shelf AND cover
            # those backorders. That combined amount can be larger than the shelf
            # can hold at once, because the backordered units are meant to pass
            # straight through to customers, not to sit on the shelf. A single
            # put() would simply drop whatever did not fit — and the node would
            # still have paid for those dropped units.
            #
            # So we add what fits right now, then pause for one instant of
            # simulation time. `env.timeout(0)` does not advance the clock; it just
            # lets other events scheduled for this same instant run. During that
            # pause, the units we just shelved are handed to the waiting customers,
            # which empties shelf space again. We then add the next chunk, and
            # repeat until the whole order has been shelved or handed out.
            #
            # Safety stop: if a pause frees no shelf space at all, the shelf is
            # genuinely full and the leftover cannot be stored. We stop there (so
            # the loop can never run forever inside a single instant) and drop the
            # leftover. `on_hand` is the node's inventory position (units on the
            # shelf plus units still in transit); it was increased by the full
            # order amount when the order was placed, so we subtract the
            # undeliverable leftover back out to keep it correct.
            if man_date_ls:                                  # supplier sent dated batches (perishable goods)
                batches = [(ele[0], ele[1]) for ele in man_date_ls]
            elif self.inventory.inv_type == "perishable":    # perishable, but we set the made-on date ourselves
                mfg = self.manufacture_date(self.env.now) if self.manufacture_date else self.env.now
                batches = [(mfg, reorder_quantity)]
            else:                                            # ordinary (non-perishable) goods
                batches = [(None, reorder_quantity)]

            accepted = 0  # how many units actually made it onto the shelf
            for mfg_date, qty in batches:
                # `remaining > 1e-9` rather than `> 0`: a tiny tolerance so
                # floating-point rounding dust never triggers one extra loop.
                remaining = qty
                while remaining > 1e-9:
                    # put() returns how many units it actually accepted — it
                    # never overfills the shelf, so this can be less than asked.
                    if mfg_date is None:
                        put_now = self.inventory.put(remaining)
                    else:
                        put_now = self.inventory.put(remaining, mfg_date)
                    accepted += put_now
                    remaining -= put_now
                    if remaining <= 1e-9:
                        break  # the whole chunk is shelved; done
                    # Shelf is full. Pause one instant so the units we just added
                    # can be handed to waiting customers (freeing space), then retry.
                    prev_level = self.inventory.level
                    yield self.env.timeout(0)
                    if self.inventory.level >= prev_level:
                        # The pause freed nothing, so nothing more can be stored.
                        # Drop the leftover and correct the inventory position.
                        # Warn the user: the node paid for these units but has
                        # nowhere to put them and no waiting customer to hand
                        # them to. This usually means the node's storage
                        # capacity is too small for the order sizes flowing
                        # through it.
                        self.logger.warning(
                            f"{self.env.now:.4f}:{self.ID}:Dropped {remaining} units from the "
                            f"delivered shipment — the shelf is full and no waiting customer "
                            f"could take them. The node's storage capacity "
                            f"({self.inventory.capacity}) may be too small for this order size."
                        )
                        self.inventory.on_hand -= remaining
                        remaining = 0
                        break

            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Inventory replenished. reorder_quantity={reorder_quantity}, accepted={accepted}, Inventory levels:{self.inventory.level}")

            # Record what actually arrived (`accepted`), not what was ordered.
            # In the normal case these are equal. They differ only when part of an
            # order could not be stored (the "safety stop" above), and in that case
            # the node should be billed for, and credited with, only the units it
            # truly received.
            self.stats.update_stats(fulfillment_received=[1,accepted],inventory_spend_cost=accepted*self.buy_price)
            supplier.source.stats.update_stats(demand_fulfilled=[1,accepted])
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
        pending_orders (int): Number of raw-material orders currently in flight (dispatched but not yet delivered).
        selection_policy (SupplierSelectionPolicy): Supplier selection policy object.
        stats (Statistics): Statistics tracking object for the manufacturer.
        production_wake (simpy.Event): Event that wakes the production loop when it is waiting (see `wake_production`).

    Functions:
        __init__: Initializes the Manufacturer object.
        manufacture_product: Makes one batch of the product, consuming raw materials and adding the batch to the inventory.
        behavior: Production loop that keeps making batches while there are planned units left to make.
        wake_production: Wakes the production loop if it is waiting.
        process_order: Places an order for raw materials based on the quantity of products to be manufactured.
        process_order_raw: Places an individual order for a specific raw material from a supplier.

    Behavior:
        When the replenishment policy asks for more stock, the manufacturer plans that many units and orders the raw
        materials needed to make them. It then makes the planned units in batches: each batch makes at most
        `product.batch_size` units and takes `product.manufacturing_time`. Batches follow one another until every
        planned unit is made. If a batch cannot start (no raw material yet, or no free space on the shelf), the
        manufacturer waits until raw material arrives, a new plan comes in, or stock leaves the shelf, and then
        carries on.

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
            pending_orders (int): Number of raw-material orders currently in flight (dispatched but not yet delivered).
            selection_policy (SupplierSelectionPolicy): Supplier selection policy object.
            stats (Statistics): Statistics tracking object for the manufacturer.
            production_wake (simpy.Event): Event that wakes the production loop when it is waiting (see `wake_production`).

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
        # Wakes the production loop when it is waiting because it could not
        # make anything. It is set off by anything that may let production go
        # on: raw material arriving, a new production plan, or stock leaving
        # the shelf (which frees space). See `wake_production`.
        self.production_wake = self.env.event()
        self.product = product # product manufactured by the manufacturer
        # self.suppliers is already initialised to [] in Node.__init__.
        self.product.sell_price = product_sell_price
        self.sell_price = product_sell_price # set the sell price of the product
        
        self.production_cycle = False # production cycle status
        self.raw_inventory_counts = {} # dictionary to store inventory counts for raw products inventory
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
        Make one batch of the product.
        A batch makes at most `product.batch_size` units and takes `product.manufacturing_time`. It can be smaller
        when there is only raw material, shelf space, or planned work left for fewer units. The raw materials are
        used up when the batch starts, and the finished units go on the shelf when it ends.

        Parameters:
            None

        Attributes:
            None

        Returns:
            int: Number of units made in this batch (0 if nothing could be made).
        """
        max_producible_units = self.product.batch_size 
        for raw_material in self.product.raw_materials:
            raw_mat_id = raw_material[0].ID
            required_amount = raw_material[1]
            current_raw_material_level = self.raw_inventory_counts[raw_mat_id]
            max_producible_units = min(max_producible_units,int(current_raw_material_level/required_amount))
        if((self.inventory.level + max_producible_units)>self.inventory.capacity): # check if the inventory can accommodate the maximum producible units
            max_producible_units = self.inventory.capacity - self.inventory.level
        # Don't make more than the factory has planned to make. When the factory
        # plans a production run, it adds those units to on_hand straight away
        # (§3.11), so on_hand = shelf + units still to be made - orders from
        # other sites that are waiting at the shelf (those were taken off
        # on_hand when they were placed). Units still to be made is therefore
        # on_hand - shelf + waiting orders.
        #
        # Leaving out the waiting orders makes this number too small, by
        # exactly the amount the factory owes. Picture a factory with 10 on
        # the shelf that receives an order for 50. on_hand drops from 10 to
        # -40, and the factory plans a run of 50 (to fill the order and refill
        # its shelf), which brings on_hand back to 10. Then on_hand - shelf =
        # 10 - 10 = 0, so it would make nothing and the order would wait
        # forever. Adding the 50 waiting units gives the correct 50.
        pending = self.inventory.on_hand - self.inventory.level + self.inventory.waiting_orders()
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
            return max_producible_units
        return 0

    def wake_production(self):
        """
        Wake the production loop if it is waiting because it could not make anything.
        Called when raw material arrives, when a new production plan comes in, and when stock leaves the shelf
        (which frees space). Calling it while the loop is busy does no harm: the loop just checks once more
        when it next stops.

        Returns:
            None
        """
        if not self.production_wake.triggered:
            self.production_wake.succeed()

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
                
        if(len(self.suppliers)<len(self.product.raw_materials)):
            self.logger.warning(f"{self.ID}: {self.name}: The number of suppliers are less than the number of raw materials required to manufacture the product! This leads to no products being manufactured.")

        # Production loop: make one batch after another for as long as there
        # are planned units left to make. The factory makes only one batch at a
        # time (we wait for each batch to finish before starting the next).
        #
        # When nothing can be made (nothing planned, no raw material yet, or no
        # free space on the shelf), wait for something that may change that:
        # raw material arriving, a new production plan, or stock leaving the
        # shelf. Waking only on raw-material deliveries is not enough. Picture
        # a factory that plans 25 units with a batch size of 5: one delivery
        # of raw material covers all 25, but would start only the first batch,
        # leaving the factory idle with raw material for 20 units on hand.
        while len(self.suppliers) >= len(self.product.raw_materials): # check if required number of suppliers are connected
            made = yield self.env.process(self.manufacture_product())
            if made > 0:
                continue # go straight on to the next batch
            yield self.production_wake
            # Replace the used event with a new one for the next wait.
            self.production_wake = self.env.event()

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
        # This order is always placed. `process_order` has already checked that
        # the link and the supplier are working, and has already counted the
        # units this raw material is for as planned production. This process
        # starts at the same moment, before the clock moves on, so neither can
        # have broken down in between.
        #
        # Raw material the factory already holds is not a reason to skip the
        # order: it is set aside for units planned earlier. Using it for these
        # new units would leave some planned units with no raw material to make
        # them from, and the factory would wait for them forever.
        if supplier.source.inventory.level < reorder_quantity:  # the supplier cannot fill this order right away: record the shortage
            shortage = reorder_quantity - supplier.source.inventory.level
            supplier.source.stats.update_stats(shortage=[1,shortage])

        self.pending_orders += 1  # count this raw-material order as in flight
        self.logger.info(f"{self.env.now:.4f}:{self.ID}:Replenishing raw material:{supplier.source.raw_material.name} from supplier:{supplier.source.ID}, order placed for {reorder_quantity} units. Current inventory level: {self.raw_inventory_counts}.")
        event, man_date_ls = supplier.source.inventory.get(reorder_quantity, site_order=True)
        supplier.source.stats.update_stats(demand_received=[1,reorder_quantity]) # update the supplier statistics for demand received
        # The supplier owes this order only while it waits for stock: count
        # it as a backorder now and remove it once it is served (the same
        # as for orders between sites, see InventoryNode.process_order).
        order_waits = not event.triggered
        if order_waits:
            supplier.source.stats.update_stats(backorder=[1,reorder_quantity])
        yield event
        if order_waits:
            # Served at last: the supplier no longer owes this order.
            supplier.source.stats.update_stats(backorder=[-1,-reorder_quantity])

        self.stats.update_stats(demand_placed=[1,reorder_quantity],transportation_cost=supplier.cost)
        self.logger.info(f"{self.env.now:.4f}:{self.ID}:shipment in transit from supplier:{supplier.source.name}.")
        lead_time = supplier.lead_time() # get the lead time from the supplier
        validate_non_negative(name="lead_time", value=lead_time) # check if lead_time is non-negative
        yield self.env.timeout(lead_time) # lead time for the order

        self.stats.update_stats(fulfillment_received=[1,reorder_quantity],inventory_spend_cost=reorder_quantity*supplier.source.sell_price)
        supplier.source.stats.update_stats(demand_fulfilled=[1,reorder_quantity]) # update the supplier statistics for demand fulfilled
        self.raw_inventory_counts[raw_mat_id] += reorder_quantity
        self.logger.info(f"{self.env.now:.4f}:{self.ID}:Order received from supplier:{supplier.source.name}, inventory levels: {self.raw_inventory_counts}")
        self.pending_orders -= 1
        self.wake_production() # raw material just arrived

    def process_order(self, supplier, reorder_quantity):
        """
        Plan the production of more product units and order the raw materials needed to make them.
        Each raw material is ordered from the first connected supplier of that raw material whose link and site
        are both working. If some raw material has no such supplier, nothing is planned and nothing is ordered;
        the replenishment policy tries again later.

        Parameters:
            supplier (Link): Supplier link picked by the selection policy. Not used: each raw material is ordered
                from its own supplier, as described above.
            reorder_quantity (float): Number of product units to plan.

        Attributes:
            None

        Returns:
            None
        """
        # Check the order against the shelf's capacity using the inventory
        # position, as InventoryNode.process_order does. Units owed to waiting
        # customers leave the shelf on the next delivery, so they do not take
        # up space. See §3.10 for details.
        gross = self.position()
        if(gross + reorder_quantity > self.inventory.capacity): # check if the inventory can accommodate the reordered quantity
                reorder_quantity = self.inventory.capacity - gross # if not, adjust reorder quantity to order only what can fit
        if reorder_quantity <= 0:
            return # no need to place an order if reorder quantity is zero

        # Units count as planned only if all their raw materials really get
        # ordered. Otherwise the factory would count on units it can never
        # make: its inventory position would include them, so the policy would
        # not order again, and orders waiting for those units would wait
        # forever. So first find a working supplier for every raw material,
        # and plan nothing if any raw material cannot be ordered right now (a
        # disrupted link or supplier). A distributor does the same: it places
        # no order while its link is down. The replenishment policy tries
        # again when stock drops again, or at its next periodic check.
        raw_orders = [] # (raw material ID, supplier link, quantity to order)
        for raw_mat, qty_per_unit in self.product.raw_materials:
            supplier_link = None
            for link in self.suppliers:
                if (link.source.raw_material.ID == raw_mat.ID
                        and link.status == "active" and link.source.node_status == "active"):
                    supplier_link = link # order from the first working supplier only
                    break
            if supplier_link is None:
                self.logger.info(f"{self.env.now:.4f}:{self.ID}:No working supplier for raw material {raw_mat.name} (link or supplier disrupted). No production planned.")
                return
            raw_orders.append((raw_mat.ID, supplier_link, qty_per_unit*reorder_quantity))

        # Count the planned production in on_hand right away (the same thing
        # InventoryNode.process_order does). Without this, the replenishment
        # policy could run again before the next production cycle, see an
        # out-of-date on_hand, and order raw materials a second time for product
        # units that are already on the way.
        self.inventory.on_hand += reorder_quantity
        # New units are planned, so let the production loop know. Raw material
        # already on hand may be enough to start on them.
        self.wake_production()

        # Order the raw materials for these units. This happens even if an
        # earlier raw-material order is still on its way: that order is for
        # units planned earlier, so these new units need their own.
        for raw_mat_id, supplier_link, quantity in raw_orders:
            self.env.process(self.process_order_raw(raw_mat_id, supplier_link, quantity))
        # This method runs via ``env.process``, so it must be a generator and
        # therefore must yield at least once — but it has nothing to wait for.
        # Each raw-material order is started as its own separate process and is
        # not awaited here (the production loop is woken when the raw material
        # arrives, see `wake_production`). So we yield a zero-length timeout, which
        # satisfies that requirement without pausing for any real time. (An
        # earlier version waited one time unit here for no real reason.)
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

    def _process_delivery(self, order_quantity, customer_id, get_event=None):
        """
        Process the delivery of the order, including lead time and delivery cost updates.

        Parameters:
            order_quantity (float): The quantity of the product ordered.
            customer_id (int): Customer ID for logging purposes.
            get_event (optional): the request that has already taken this order's
                units off the shelf, if the caller made one. ``wait_for_order``
                passes one so that the units are taken at the same moment the
                customer checks the shelf. When it is not given, the units are
                taken here.

        Attributes:
            order_quantity (float): The quantity of the product ordered.
            customer_id (int): Customer ID for logging purposes.

        returns:
            None
        """
        del_cost = self.delivery_cost()
        validate_non_negative(name="delivery_cost", value=del_cost) # check if delivery_cost is non-negative
        self.stats.update_stats(transportation_cost=del_cost)
        
        if get_event is None:
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
        While waiting, the customer's order is counted as a backorder at the node.
        The customer checks again each time new stock arrives at the node.
        If the customer tolerance is infinite, the method waits until the order is fulfilled.
        Otherwise, the customer leaves as soon as their tolerance (patience) runs out,
        even if no new stock has arrived, and whatever they were still owed is taken
        off the node's backorders.

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

        # The customer will wait until this moment and no longer.
        deadline = self.env.now + self.customer_tolerance
        while True:
            available = self._available()
            # When there is enough, the units are taken off the shelf right
            # here, in the same step as the check, and not later inside
            # ``_process_delivery``. That process only starts once this step is
            # over. If one delivery of stock wakes several waiting customers at
            # the same moment, each of them would otherwise check the shelf
            # before any of them had taken anything, all would see the same
            # units, and all would think those units were theirs.
            if order_quantity <= available: # check if remaining order quantity is available
                get_event, _ = self.demand_node.inventory.get(order_quantity)
                self.env.process(self._process_delivery(order_quantity, customer_id, get_event))
                self.demand_node.stats.update_stats(backorder=[-1,-order_quantity])
                order_quantity = 0
                break
            # ``partial`` can round down to 0 for a small order, so also check
            # that there is at least one unit to send. Asking the shelf for 0
            # units is an error in SimPy.
            elif available > 0 and available >= partial: # or else at least min required 'partial' is available
                get_event, _ = self.demand_node.inventory.get(available)
                self.env.process(self._process_delivery(available, customer_id, get_event))
                # Partial shipment: backorder count stays 1 (one outstanding customer order)
                # while its quantity ticks down. fulfillment_received and demand_fulfilled
                # each get a compensating -1 on the count so the single eventual completion
                # is counted exactly once — matching the backorder accounting convention.
                self.demand_node.stats.update_stats(backorder=[0,-available], demand_fulfilled=[-1,0])
                self.stats.update_stats(fulfillment_received=[-1,0])
                order_quantity -= available # update order quantity
            else: 
                self.demand_node.stats.update_stats(shortage=[1,order_quantity-available])

            if self.env.now >= deadline:
                break  # the customer's patience has run out

            # Wait for whichever comes first: new stock arriving at the node, or
            # the end of the customer's patience. Without the second part, a
            # customer would only notice that their patience had run out when
            # stock next arrived — and if no stock ever arrived, they would
            # wait (and stay counted as a backorder) forever.
            raised_event = self.demand_node.inventory_raised  # the node's current "inventory raised" signal
            if deadline == float('inf'):
                yield raised_event  # endless patience: only new stock can end the wait
            else:
                yield raised_event | self.env.timeout(deadline - self.env.now)

            # The "stock arrived" signal can fire only once, so after it fires it
            # is swapped for a fresh one. Several customers may be waiting on the
            # same signal; only the first one to wake should swap it. If a later
            # customer swapped it again, the customers who had already moved on
            # to the first fresh signal would be left waiting on one that never
            # fires. Hence the check that the node still holds the signal we
            # waited on. If we woke because our patience ran out instead, the
            # signal has not fired and must be left alone for the others.
            if raised_event.triggered and self.demand_node.inventory_raised is raised_event:
                self.demand_node.inventory_raised = self.env.event()

        if order_quantity > 0: # the customer gives up and leaves without the rest of the order
            # They are no longer waiting, so take what they were still owed off
            # the node's current backorders. (The count drops by 1 even after
            # partial deliveries: one customer is one backorder until they are
            # fully served or leave.) Without this, the node would keep
            # reordering stock for a customer who has already gone.
            self.demand_node.stats.update_stats(backorder=[-1,-order_quantity])
            self.logger.info(f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}: remaining order quantity:{order_quantity} not available! Customer leaves.")

    def _available(self):
        """
        How many units a customer can take from the node's shelf right now.

        Requests for stock are served strictly in the order they were made. If
        an earlier request is still waiting because the shelf cannot fill it yet
        (for example, a site below this node ordered 50 units while only 10 are
        on the shelf), every later request waits behind it, even a small one.
        So while any request is waiting, nothing on the shelf is free for a new
        customer, even though units can be seen on it.

        Returns:
            float: the shelf level, or 0 while an earlier request is still waiting.
        """
        inventory = self.demand_node.inventory
        return 0 if inventory.inventory.get_queue else inventory.level

    # ---- Customer-order helpers -------------------------------------------
    # ``customer`` used to handle four different ways of filling an order all in
    # one method, each with its own style and its own stats updates. Splitting
    # them into separate, named helpers makes each case clear and lets
    # ``customer`` read as a simple router. Every helper is written as a SimPy
    # generator so the router can call them all the same way with ``yield
    # from``; ``_serve_no_tolerance`` does no waiting, but is still written as a
    # generator (``return; yield``) so the router needs no special case for it.
    # The tolerance helper starts ``wait_for_order`` as its own separate process
    # on purpose, so the ``customer`` call returns promptly even when the
    # customer is willing to wait a long time; the stats are still recorded
    # inside ``wait_for_order`` whenever the order is eventually settled.

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

    def _discard_unservable(self, order_quantity, customer_id):
        """Order is too big for the upstream node to ever hold — discard it.

        The smallest piece the customer will accept (the whole order when no
        partial delivery is allowed, otherwise the minimum split chunk) is
        larger than the upstream node's total shelf capacity. Even a completely
        full shelf could not cover it, so this order can never be served. We
        record it as lost demand (a shortage) and log a warning, but we do
        **not** create a backorder and do **not** trigger a replenishment
        order. Backordering it would only make the node order stock from its
        own supplier that, once delivered, would not fit on the shelf and would
        simply be thrown away."""
        capacity = self.demand_node.inventory.capacity
        self.logger.warning(
            f"{self.env.now:.4f}:{self.ID}:Customer{customer_id}: Order quantity:"
            f"{order_quantity} is larger than {self.demand_node.name}'s storage "
            f"capacity ({capacity}) and can never be delivered (no partial delivery "
            f"would help). Order discarded — recorded as lost demand, no backorder "
            f"and no replenishment placed."
        )
        self.demand_node.stats.update_stats(shortage=[1, order_quantity])
        return
        yield  # pragma: no cover — keeps this a generator (see _enqueue_for_tolerance).

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
        available = self._available()
        self.stats.update_stats(demand_placed=[1, order_quantity])
        # The smallest piece this customer will take: the whole order when no
        # partial delivery is allowed (min_split >= 1), otherwise the minimum
        # split chunk. This mirrors how ``wait_for_order`` computes ``partial``.
        min_chunk = order_quantity if self.min_split >= 1 else int(order_quantity * self.min_split)
        if order_quantity <= available:
            yield from self._serve_in_full(order_quantity, customer_id)
        elif self.consume_available and available > 0:
            yield from self._serve_partial_consume(order_quantity, available, customer_id)
        elif self.customer_tolerance > 0:
            if min_chunk > self.demand_node.inventory.capacity:
                # Order can never be served — even a full shelf cannot cover
                # the smallest acceptable piece. Discard it rather than create
                # a backorder that would drive a replenishment the shelf can't
                # hold.
                yield from self._discard_unservable(order_quantity, customer_id)
            else:
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