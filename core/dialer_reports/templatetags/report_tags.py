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