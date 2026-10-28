"""Text manipulation helpers."""

from .calculator import add


def count_words(text):
    """Return the number of whitespace-separated words in text."""
    return len(text.split())


def reverse_text(text):
    """Return the text reversed character by character."""
    return text[::-1]


def slugify(text):
    """Return a lowercase, hyphen-separated slug for the text."""
    return "-".join(text.lower().split())


def word_count_label(text):
    """Return a label like '3 words' for the given text."""
    count = count_words(text)
    return f"{add(count, 0)} words"
