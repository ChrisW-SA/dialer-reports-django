from django import template

register = template.Library()


@register.filter
def seconds_to_hms(seconds):
    if not seconds:
        return 0
    seconds = int(seconds)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)


@register.filter
def dial_result_badge_color(value):
    color_map = {
        'F-Failed': 'danger',
        'R-Abandon': 'danger',
        'R-No Answer': 'warning',
        'C-Completed': 'success',
        'R-Timeout': 'warning',
        # Add other mappings as needed
    }
    return color_map.get(value, 'secondary')

@register.filter
def disposition_badge_color(value):
    color_map = {
        '': 'danger',
        # Add other mappings as needed
    }
    return color_map.get(value, 'info')