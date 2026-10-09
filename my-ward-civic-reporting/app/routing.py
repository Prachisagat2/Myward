"""Category -> department / priority routing and ward lookup.

This is the single place to change when the YOLO model replaces manual
category selection: the model only has to return a Category.
"""
import math

from .enums import Category, Priority

ROUTING: dict[Category, tuple[str, Priority]] = {
    Category.POTHOLE: ("Road Maintenance Department", Priority.HIGH),
    Category.GARBAGE: ("Solid Waste Management Department", Priority.MEDIUM),
    Category.STREETLIGHT: ("Electrical Department", Priority.MEDIUM),
    Category.WATER_LEAKAGE: ("Water Supply Department", Priority.HIGH),
    Category.DRAINAGE: ("Drainage and Sewerage Department", Priority.HIGH),
    Category.ILLEGAL_DUMPING: ("Sanitation Enforcement Department", Priority.MEDIUM),
}

WARD_COUNT = 20


def route_complaint(category: Category) -> tuple[str, Priority]:
    return ROUTING[category]


def ward_from_coordinates(latitude: float, longitude: float) -> int:
    """PLACEHOLDER ward lookup.

    Splits the map into ~1 km grid cells and maps each cell to one of
    WARD_COUNT wards, so nearby complaints get the same ward number.
    Replace with a real point-in-polygon lookup against your city's ward
    boundary GeoJSON for production use.
    """
    row = math.floor(latitude * 100)
    col = math.floor(longitude * 100)
    return (row * 31 + col) % WARD_COUNT + 1
