from django import template

register = template.Library()

@register.filter(name='to_seat_name')
def to_seat_name(seat_number):
    """
    Converts a seat integer (e.g., 1, 5) to an alphanumeric name (e.g., A1, B1).
    Assumes 4 seats per row.
    """
    if not isinstance(seat_number, int) or seat_number <= 0:
        return ""
    
    seats_per_row = 4
    row = chr(ord('A') + (seat_number - 1) // seats_per_row)
    col = (seat_number - 1) % seats_per_row + 1
    return f"{row}{col}"

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies the value by the arg."""
    try:
        return value * arg
    except (ValueError, TypeError):
        return ''

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key) 