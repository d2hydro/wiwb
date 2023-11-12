"""For converting one thing into another"""

def snake_to_pascal_case(snake_case: str) -> str:
    """Convert snake_case to PascalCase."""
    words = snake_case.split("_")
    return "".join(i.title() for i in words)