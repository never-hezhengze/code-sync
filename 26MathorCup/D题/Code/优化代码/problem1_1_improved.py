from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

RANDOM_SEED = 20261016
TOP_CLEARANCE = 3
SUPPORT_LIMIT_PER_CM2 = 500 / 10000


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


@dataclass(frozen=True)
class CargoItem:
    item_id: str
    type_id: str
    category: str
    original_size: Tuple[int, int, int]
    weight: float
    volume: int
    stackable: bool
    fragile: bool
    oriented: bool
    allowed_orientations: Tuple[Orientation, ...]


@dataclass(frozen=True)
class TruckType:
    truck_id: int
    name: str
    length: int
    width: int
    height: int
    max_weight: float
    trip_cost: float

    @property
    def usable_height(self) -> int:
        return self.height - TOP_CLEARANCE

    @property
    def volume(self) -> int:
        return self.length * self.width * self.usable_height


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
    support_by: str | None = None
    support_capacity: float = 0.0
    direct_supported_weight: float = 0.0

    @property
    def top(self) -> int:
        return self.z + self.height


@dataclass
class PackingResult:
    truck: TruckType
    placed: List[PlacedCargo]
    unplaced: List[CargoItem]
    utilized_volume: int
    utilized_weight: float
    score: float

    @property
    def volume_utilization(self) -> float:
        return self.utilized_volume / self.truck.volume if self.truck.volume else 0.0

    @property
    def weight_utilization(self) -> float:
        return self.utilized_weight / self.truck.max_weight if self.truck.max_weight else 0.0


def load_truck_types() -> Dict[int, TruckType]:
    return {
        1: TruckType(1, "车型1", 420, 210, 220, 6000, 450),
        2: TruckType(2, "车型2", 680, 245, 250, 10000, 700),
    }


def load_cargo_types() -> Dict[str, CargoType]:
    return {
        "G1": CargoType("G1", "standard", 60, 40, 30, 12, 80, True, True, False, False),
        "G2": CargoType("G2", "standard", 50, 35, 25, 8, 100, True, True, False, False),
        "G3": CargoType("G3", "fragile", 70, 50, 40, 15, 30, False, True, True, False),
        "G4": CargoType("G4", "oriented", 80, 60, 50, 25, 40, True, False, False, True),
        "G5": CargoType("G5", "oriented", 40, 40, 60, 18, 50, True, False, False, True),
    }


def unique_orientations(size: Tuple[int, int, int], category: str) -> Tuple[Orientation, ...]:
    l, w, h = size
    perms = {
        "standard": [
            ((l, w, h), "LWH"),
            ((l, h, w), "LHW"),
            ((w, l, h), "WLH"),
            ((w, h, l), "WHL"),
            ((h, l, w), "HLW"),
            ((h, w, l), "HWL"),
        ],
        "fragile": [
            ((l, w, h), "LWH"),
            ((w, l, h), "WLH"),
        ],
        "oriented": [
            ((l, w, h), "LWH"),
        ],
    }[category]

    seen, ans = set(), []
    for i, (dims, name) in enumerate(perms, 1):
        if dims in seen:
            continue
        seen.add(dims)
        ans.append(Orientation(i, dims, name))
    return tuple(ans)


def expand_cargo_items(cargo_types: Dict[str, CargoType]) -> List[CargoItem]:
    items = []
    for cargo in cargo_types.values():
        size = (cargo.length, cargo.width, cargo.height)
        orientations = unique_orientations(size, cargo.category)
        volume = cargo.length * cargo.width * cargo.height
        for idx in range(1, cargo.quantity + 1):
            items.append(
                CargoItem(
                    f"{cargo.type_id}_{idx:03d}",
                    cargo.type_id,
                    cargo.category,
                    size,
                    cargo.weight,
                    volume,
                    cargo.stackable,
                    cargo.fragile,
                    cargo.oriented,
                    orientations,
                )
            )
    return items


def overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


def boxes_overlap(x: int, y: int, z: int, dims: Tuple[int, int, int], p: PlacedCargo) -> bool:
    l, w, h = dims
    return (
        overlap(x, x + l, p.x, p.x + p.length)
        and overlap(y, y + w, p.y, p.y + p.width)
        and overlap(z, z + h, p.z, p.z + p.height)
    )


def point_inside_box(point: Tuple[int, int, int], p: PlacedCargo) -> bool:
    x, y, z = point
    return p.x <= x < p.x + p.length and p.y <= y < p.y + p.width and p.z <= z < p.z + p.height


def supporter_for(item: CargoItem, x: int, y: int, z: int, dims: Tuple[int, int, int], placed: List[PlacedCargo]):
    if z == 0:
        return None, None

    l, w, _ = dims
    for c in placed:
        if c.top != z:
            continue
        if not (c.x <= x and x + l <= c.x + c.length and c.y <= y and y + w <= c.y + c.width):
            continue
        if item.fragile and c.category != "standard":
            continue
        if c.category == "fragile":
            continue
        return c.item_id, c
    return None, None


def can_place(
    item: CargoItem,
    ori: Orientation,
    point: Tuple[int, int, int],
    truck: TruckType,
    placed: List[PlacedCargo],
    current_weight: float,
):
    x, y, z = point
    l, w, h = ori.size

    if x + l > truck.length or y + w > truck.width or z + h > truck.usable_height:
        return False, None, 0.0
    if current_weight + item.weight > truck.max_weight:
        return False, None, 0.0

    for p in placed:
        if boxes_overlap(x, y, z, ori.size, p):
            return False, None, 0.0

    support_id, supporter = supporter_for(item, x, y, z, ori.size, placed)
    if z > 0 and supporter is None:
        return False, None, 0.0

    if supporter is None:
        return True, None, 0.0

    cap = SUPPORT_LIMIT_PER_CM2 * supporter.length * supporter.width
    if supporter.direct_supported_weight + item.weight > cap + 1e-9:
        return False, None, 0.0

    if item.category == "oriented":
        cx, cy = x + l / 2, y + w / 2
        if not (supporter.x <= cx <= supporter.x + supporter.length and supporter.y <= cy <= supporter.y + supporter.width):
            return False, None, 0.0

    return True, support_id, cap


def candidate_points(placed: List[PlacedCargo], truck: TruckType) -> List[Tuple[int, int, int]]:
    """
    改进点：
    1. 极点不再只生成 3 个，而是生成更多组合；
    2. 增加与车壁对齐的候选点；
    3. 过滤掉明显越界或落在箱体内部的点。
    """
    pts = {(0, 0, 0)}

    for p in placed:
        x0, y0, z0 = p.x, p.y, p.z
        x1, y1, z1 = p.x + p.length, p.y + p.width, p.z + p.height

        # 基础 3 个
        pts.update({
            (x1, y0, z0),
            (x0, y1, z0),
            (x0, y0, z1),
        })

        # 扩展极点
        pts.update({
            (x1, y1, z0),
            (x1, y0, z1),
            (x0, y1, z1),
            (x1, y1, z1),
        })

        # 与地板/侧壁对齐的辅助点
        pts.update({
            (x1, y0, 0),
            (x0, y1, 0),
            (x1, 0, z0),
            (0, y1, z0),
        })

    filtered = []
    for pt in pts:
        x, y, z = pt
        if x < 0 or y < 0 or z < 0:
            continue
        if x > truck.length or y > truck.width or z > truck.usable_height:
            continue
        if any(point_inside_box(pt, p) for p in placed):
            continue
        filtered.append(pt)

    return sorted(set(filtered), key=lambda t: (t[2], t[0] + t[1], t[0], t[1]))


def estimate_fragmentation(point: Tuple[int, int, int], ori: Orientation, truck: TruckType) -> float:
    """
    简化的碎片度估计：
    越靠内部、越不贴边，越容易制造碎片。
    """
    x, y, z = point
    l, w, h = ori.size

    gap_x = min(x, max(0, truck.length - (x + l)))
    gap_y = min(y, max(0, truck.width - (y + w)))
    gap_z = min(z, max(0, truck.usable_height - (z + h)))

    return 0.000015 * (gap_x * gap_y + gap_x * gap_z + gap_y * gap_z)


def placement_score(
    item: CargoItem,
    ori: Orientation,
    point: Tuple[int, int, int],
    truck: TruckType,
    alpha: float,
    beta: float,
) -> float:
    x, y, z = point
    l, w, h = ori.size

    volume_ratio = (l * w * h) / truck.volume
    weight_ratio = item.weight / truck.max_weight

    boundary_bonus = 0.03 if (x == 0 or y == 0 or z == 0) else 0.0
    floor_bonus = 0.015 if z == 0 else 0.0
    footprint_bonus = 0.012 * (l * w) / (truck.length * truck.width)

    # 更重视难装货
    difficulty_bonus = {
        "fragile": 0.035,
        "oriented": 0.020,
        "standard": 0.0,
    }[item.category]

    compact_penalty = 0.00035 * (z + 0.30 * x + 0.18 * y)
    frag_penalty = estimate_fragmentation(point, ori, truck)

    return (
        alpha * volume_ratio
        + beta * weight_ratio
        + boundary_bonus
        + floor_bonus
        + footprint_bonus
        + difficulty_bonus
        - compact_penalty
        - frag_penalty
    )


def difficulty_rank(item: CargoItem) -> int:
    return {
        "fragile": 3,
        "oriented": 2,
        "standard": 1,
    }[item.category]


def initial_sequence(items: Sequence[CargoItem], rng: random.Random) -> List[CargoItem]:
    """
    改进点：
    1. 先放更难装的货；
    2. 大件优先；
    3. 对部分块做轻微扰动，保留多样性。
    """
    seq = list(items)
    seq.sort(
        key=lambda item: (
            -difficulty_rank(item),
            -item.volume,
            -item.weight,
            -item.weight / max(item.volume, 1),
            item.type_id,
            item.item_id,
        )
    )

    # 分段扰动：不完全打散，保留层次
    block = max(6, len(seq) // 15)
    for start in range(0, len(seq), block):
        end = min(len(seq), start + block)
        chunk = seq[start:end]
        rng.shuffle(chunk)
        seq[start:end] = chunk
    return seq


def pack_single_truck(items: Sequence[CargoItem], truck: TruckType, alpha: float = 0.5, beta: float = 0.5) -> PackingResult:
    placed: List[PlacedCargo] = []
    unplaced: List[CargoItem] = []
    current_weight = 0.0
    current_volume = 0

    for item in items:
        best = None
        for point in candidate_points(placed, truck):
            for ori in item.allowed_orientations:
                feasible, support_id, cap = can_place(item, ori, point, truck, placed, current_weight)
                if not feasible:
                    continue
                score = placement_score(item, ori, point, truck, alpha, beta)
                if best is None or score > best[0]:
                    best = (score, point, ori, support_id, cap)

        if best is None:
            unplaced.append(item)
            continue

        _, (x, y, z), ori, support_id, cap = best
        placed_item = PlacedCargo(
            item.item_id,
            item.type_id,
            item.category,
            x,
            y,
            z,
            ori.size[0],
            ori.size[1],
            ori.size[2],
            item.weight,
            ori.orient_id,
            ori.rotation,
            support_id,
            cap,
        )
        placed.append(placed_item)
        current_weight += item.weight
        current_volume += item.volume

        if support_id is not None:
            for p in placed:
                if p.item_id == support_id:
                    p.direct_supported_weight += item.weight
                    break

    score = alpha * (current_volume / truck.volume) + beta * (current_weight / truck.max_weight)
    return PackingResult(truck, placed, unplaced, current_volume, current_weight, score)


def mutate(sequence: List[CargoItem], rng: random.Random, swaps: int = 3) -> List[CargoItem]:
    child = sequence[:]
    if len(child) < 2:
        return child
    for _ in range(swaps):
        i, j = rng.sample(range(len(child)), 2)
        child[i], child[j] = child[j], child[i]
    return child


def order_crossover(parent1: Sequence[CargoItem], parent2: Sequence[CargoItem], rng: random.Random) -> List[CargoItem]:
    n = len(parent1)
    if n < 2:
        return list(parent1)

    left, right = sorted(rng.sample(range(n), 2))
    child: List[CargoItem | None] = [None] * n
    child[left:right + 1] = list(parent1[left:right + 1])

    used = {item.item_id for item in parent1[left:right + 1]}
    fill = [item for item in parent2 if item.item_id not in used]
    ptr = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[ptr]
            ptr += 1
    return [item for item in child if item is not None]


def tournament_select(population: Sequence[List[CargoItem]], scores: Sequence[float], rng: random.Random, k: int = 3) -> List[CargoItem]:
    cand = rng.sample(range(len(population)), k)
    return population[max(cand, key=lambda idx: scores[idx])]


def genetic_optimize_single_truck(
    items: Sequence[CargoItem],
    truck: TruckType,
    alpha: float = 0.5,
    beta: float = 0.5,
    population_size: int = 20,
    generations: int = 28,
    seed: int = RANDOM_SEED,
) -> PackingResult:
    if len(items) <= 1:
        return pack_single_truck(items, truck, alpha, beta)

    rng = random.Random(seed + truck.truck_id)
    base = initial_sequence(items, rng)
    population = [base] + [mutate(base, rng, swaps=6) for _ in range(population_size - 1)]

    best = None
    elite_count = max(2, population_size // 5)

    for _ in range(generations):
        scored = []
        for seq in population:
            result = pack_single_truck(seq, truck, alpha, beta)
            scored.append((result.score, result, seq))
            if best is None or result.score > best.score:
                best = result

        scored.sort(key=lambda x: x[0], reverse=True)
        elites = [row[2][:] for row in scored[:elite_count]]

        raw_population = [row[2] for row in scored]
        raw_scores = [row[0] for row in scored]
        next_population = elites[:]

        while len(next_population) < population_size:
            p1 = tournament_select(raw_population, raw_scores, rng)
            p2 = tournament_select(raw_population, raw_scores, rng)
            child = order_crossover(p1, p2, rng)
            if rng.random() < 0.85:
                child = mutate(child, rng, swaps=rng.randint(2, 6))
            next_population.append(child)

        population = next_population

    return best if best is not None else pack_single_truck(items, truck, alpha, beta)


def result_to_dict(result: PackingResult) -> Dict[str, object]:
    return {
        "truck": asdict(result.truck),
        "summary": {
            "loaded_items": len(result.placed),
            "unloaded_items": len(result.unplaced),
            "space_utilization": round(result.volume_utilization, 6),
            "weight_utilization": round(result.weight_utilization, 6),
            "composite_score": round(result.score, 6),
            "used_volume_cm3": result.utilized_volume,
            "used_weight_kg": round(result.utilized_weight, 3),
        },
        "placements": [asdict(item) for item in result.placed],
        "unplaced_items": [item.item_id for item in result.unplaced],
    }