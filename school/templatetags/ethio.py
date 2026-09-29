from django import template

from .. import ethiopic

register = template.Library()


@register.filter
def dict_get(d, key):
    """Look up a dynamic key in a dict from a template — Django's dot lookup
    only works with a literal key, not a loop variable (e.g. column.pk)."""
    if d is None:
        return None
    return d.get(key)


@register.filter
def eth_date(value, with_weekday=False):
    """A Gregorian date/datetime -> its Ethiopian calendar display string."""
    return ethiopic.format_date(value, with_weekday=with_weekday)


@register.filter
def eth_date_weekday(value):
    return ethiopic.format_date(value, with_weekday=True)


@register.filter
def eth_short(value):
    """Compact day/month label — used as a table column header (e.g. attendance)."""
    return ethiopic.format_short(value)


@register.filter
def eth_input(value):
    """dd/mm/yyyy in the Ethiopian calendar — what a date <input> should show."""
    return ethiopic.format_input(value)


@register.simple_tag
def eth_current_year():
    return ethiopic.current_year()


@register.filter
def eth_month_name(month_number):
    try:
        return ethiopic.MONTHS[int(month_number) - 1]
    except (TypeError, ValueError, IndexError):
        return ""

@register.filter(name="add_class")
def add_class(field, css):
    """Applies Tailwind classes to any bound field's widget, regardless of
    type (text, number, date, select, textarea) — used by partials/_field.html
    so the 11-field student form isn't hand-written field by field."""
    return field.as_widget(attrs={"class": css})