"""
Pytest configuration for SupplyNetPy tests.

Forces the test suite to import the in-tree source (src/SupplyNetPy/...) rather
than a potentially-stale pip-installed copy. This is belt-and-braces — an
editable install (`pip install -e .`) already points at src/, but this ensures
tests still resolve to the source under edit in environments where the package
is not installed (e.g. fresh clones, CI before `pip install -e .`).
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
