# mathorcup_d_common.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Orientation:
    orient_id: int
    size: Tuple[int, int, int]
    rotation: str


@dataclass(frozen=True)
class CargoType:
    type_id: str
    category: str
    length: int
    width: int
    height: int
    weight: float
    quantity: int
    stackable: bool
    can_rotate: bool
    fragile: bool
    oriented: bool
    max_support_pressure: float = 500.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class Truck:
    name: str
    length: int
    width: int
    height: int
    max_weight: float
    cost: float
    top_clearance: int = 3

    @property
    def effective_height(self) -> int:
        return self.height - self.top_clearance

    @property
    def effective_volume(self) -> int:
        return self.length * self.width * self.effective_height


@dataclass
class PlacedCargo:
    item_id: str
    type_id: str
    category: str
    x: int
    y: int
    z: int
    length: int
    width: int
    height: int
    weight: float
    orientation_id: int
    rotation: str
    truck_id: str

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


@dataclass
class VehicleResult:
    vehicle_id: str
    placed: List[PlacedCargo]
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int


TRUCKS: Dict[str, Truck] = {
    "车型1": Truck("车型1", 420, 210, 220, 6000.0, 450.0),
    "车型2": Truck("车型2", 680, 245, 250, 10000.0, 700.0),
}

CARGO_TYPES: Dict[str, CargoType] = {
    "G1": CargoType("G1", "standard", 60, 40, 30, 12, 800, True, True, False, False),
    "G2": CargoType("G2", "standard", 50, 35, 25, 8, 1000, True, True, False, False),
    "G3": CargoType("G3", "fragile", 70, 50, 40, 15, 300, False, True, True, False),
    "G4": CargoType("G4", "oriented", 80, 60, 50, 25, 400, True, False, False, True),
    "G5": CargoType("G5", "oriented", 40, 40, 60, 18, 500, True, False, False, True),
}

TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]
TYPE_ORDER_MAIN = ["G4", "G5", "G1", "G2"]


def generate_orientations(cargo: CargoType) -> Tuple[Orientation, ...]:
    l, w, h = cargo.length, cargo.width, cargo.height
    dims = [
        (l, w, h, "LWH"),
        (l, h, w, "LHW"),
        (w, l, h, "WLH"),
        (w, h, l, "WHL"),
        (h, l, w, "HLW"),
        (h, w, l, "HWL"),
    ]
    if cargo.oriented:
        dims = [(l, w, h, "LWH")]

    out = []
    seen = set()
    for a, b, c, name in dims:
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            out.append(Orientation(len(out) + 1, key, name))
    return tuple(out)


ORIENTATIONS: Dict[str, Tuple[Orientation, ...]] = {
    k: generate_orientations(v) for k, v in CARGO_TYPES.items()
}


def truck_score(truck: Truck, used_volume: int, used_weight: float):
    sv = used_volume / truck.effective_volume
    wv = used_weight / truck.max_weight
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs