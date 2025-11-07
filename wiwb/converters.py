"""For converting one thing into another"""
from pathlib import Path
from datetime import datetime


def snake_to_pascal_case(snake_case: str) -> str:
    """Convert snake_case to PascalCase."""
    words = snake_case.split("_")
    return "".join(i.title() for i in words)


def rename_file(file_name: Path, prefix:str, use: str = "start", datetime_pattern: str = "%Y%m%d%H%M"):
    """Rename a WIWB output file to a different datetime pattern"""
    file_name = Path(file_name)
    _, _, start_str, end_str = file_name.stem.split("_")
    if use == "start":
        date_time = datetime.strptime(start_str, "%Y-%m-%dT%Hh%Mm%Ss")
    elif use == "end":
        date_time = datetime.strptime(end_str, "%Y-%m-%dT%Hh%Mm%Ss")
    else:
        raise ValueError(f"value for use {use} not implemented. Use start or end")

    return f"{prefix}_{date_time.strftime(datetime_pattern)}{file_name.suffix}"
