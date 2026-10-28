"""Basic arithmetic helpers."""


def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def subtract(a, b):
    """Return the difference of two numbers."""
    return a - b


def multiply(a, b):
    """Return the product of two numbers."""
    return a * b


def divide(a, b):
    """Return a divided by b, raising on division by zero."""
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def average(numbers):
    """Return the arithmetic mean of a non-empty sequence of numbers."""
    if not numbers:
        raise ValueError("average of empty sequence")
    return sum(numbers) / len(numbers)


class Calculator:
    """A tiny stateful calculator."""

    def __init__(self):
        """Start with a total of zero."""
        self.total = 0

    def add_to_total(self, value):
        """Add value to the running total and return the total."""
        self.total = add(self.total, value)
        return self.total
