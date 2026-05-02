from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter(name='thousands_dot')
def thousands_dot(value):
    """Format numbers with dot as thousands separator and no decimals."""
    if value is None or value == '':
        return '0'

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    integer_part = int(number)
    return f"{integer_part:,}".replace(',', '.')
