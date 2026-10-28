"""A minimal inventory, built on the calculator helpers."""

from .calculator import multiply


def total_value(items):
    """Return the total value of items, each a (price, quantity) pair."""
    return sum(multiply(price, qty) for price, qty in items)


def find_item(items, name):
    """Return the first item dict whose 'name' matches, or None."""
    for item in items:
        if item.get("name") == name:
            return item
    return None


def count_items(items):
    """Return how many items are in the inventory list."""
    return len(items)
