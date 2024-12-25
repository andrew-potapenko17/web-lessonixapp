from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def format_date(date_string):
    """Convert a date string from 'YYYY-MM-DD' to 'DD/MM' and handle suffixes like 'YYYY-MM-DD-suffix'."""
    if '-' in date_string:
        parts = date_string.split('-')
        if len(parts) >= 3:
            formatted_date = f"{parts[2]}/{parts[1]}"
            if len(parts) > 3:
                suffix = '-'.join(parts[3:])
                return f"{formatted_date}-{suffix}"
            return formatted_date
    return date_string
