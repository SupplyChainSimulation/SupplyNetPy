"""
Public API for SupplyNetPy.

Users import from this package (conventionally ``import SupplyNetPy.Components
as scm``). Every supported name is re-exported explicitly below — wildcard
imports were removed so that module-level imports (``simpy``, ``random``,
``copy``, ``numbers``, ``networkx``, ``matplotlib.pyplot``, ``logging``) and
internal state (``global_logger``, ``_rng``, ``_LOGGER_KWARGS``,
``_NODE_KWARGS``) no longer leak onto ``scm``.

Adding a new public symbol? Three steps: add it to its module's ``__all__``,
add it to the matching ``from ... import`` block below, and add it to
``__all__`` at the bottom of this file.
"""

from SupplyNetPy.Components.core import (
    set_seed,
    validate_positive,
    validate_non_negative,
    validate_number,
    NamedEntity,
    InfoMixin,
    Statistics,
    RawMaterial,
    Product,
    InventoryReplenishment,
    SSReplenishment,
    RQReplenishment,
    PeriodicReplenishment,
    SupplierSelectionPolicy,
    SelectFirst,
    SelectAvailable,
    SelectCheapest,
    SelectFastest,
    Node,
    Link,
    Inventory,
    Supplier,
    InventoryNode,
    Manufacturer,
    Demand,
    global_logger,
)
from SupplyNetPy.Components.logger import GlobalLogger
from SupplyNetPy.Components.utilities import (
    check_duplicate_id,
    process_info_dict,
    visualize_sc_net,
    get_sc_net_info,
    create_sc_net,
    simulate_sc_net,
    print_node_wise_performance,
)

__all__ = [
    # core — RNG
    "set_seed",
    # core — validators
    "validate_positive",
    "validate_non_negative",
    "validate_number",
    # core — mixins
    "NamedEntity",
    "InfoMixin",
    # core — stats / products
    "Statistics",
    "RawMaterial",
    "Product",
    # core — replenishment policies
    "InventoryReplenishment",
    "SSReplenishment",
    "RQReplenishment",
    "PeriodicReplenishment",
    # core — supplier-selection policies
    "SupplierSelectionPolicy",
    "SelectFirst",
    "SelectAvailable",
    "SelectCheapest",
    "SelectFastest",
    # core — graph primitives
    "Node",
    "Link",
    "Inventory",
    # core — concrete nodes
    "Supplier",
    "InventoryNode",
    "Manufacturer",
    "Demand",
    # core — bulk logging handle (per-docs)
    "global_logger",
    # logger
    "GlobalLogger",
    # utilities
    "check_duplicate_id",
    "process_info_dict",
    "visualize_sc_net",
    "get_sc_net_info",
    "create_sc_net",
    "simulate_sc_net",
    "print_node_wise_performance",
]
