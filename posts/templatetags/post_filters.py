from django import template

register = template.Library()

@register.filter
def hex_to_rgba(hex_color, alpha):
    """
    Convert hex color to rgba format.
    
    Args:
        hex_color: Hex color string (e.g., "#ffffff")
        alpha: Alpha value as string (e.g., "0.06")
    
    Returns:
        RGBA color string (e.g., "rgba(255, 255, 255, 0.06)")
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r}, {g}, {b}, {alpha})'
