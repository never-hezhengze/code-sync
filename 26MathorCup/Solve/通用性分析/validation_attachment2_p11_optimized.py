#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import os
import random
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

@dataclass(frozen=True)
class Orientation:
    orient_id: int
    size: Tuple[int, int, int]
    rotation: str

@dataclass(frozen=True)
class CargoType:
    type_id: str
    name: str
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

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def base_area(self) -> int:
        return self.length * self.width

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
    support_by: Optional[str] = None
    truck_id: Optional[str] = None

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
    top_clearance: int = 0

    @property
    def effective_height(self) -> int:
        return self.height - self.top_clearance

    @property
    def effective_volume(self) -> int:
        return self.length * self.width * self.effective_height

@dataclass
class Space:
    x: int
    y: int
    z: int
    length: int
    width: int
    height: int

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

@dataclass
class LayoutState:
    spaces: List[Space]
    placed: List[PlacedCargo]
    remaining: List[CargoItem]
    used_weight: float
    used_volume: int
    score: float = 0.0
    packed_ratio: float = 0.0

QUANTITY_EACH = 100

CARGO_TYPES: Dict[str, CargoType] = {
    "P1": CargoType("P1", "3.68L*4", "standard", 301, 301, 347, 0.0, QUANTITY_EACH, True, True, False, False),
    "P2": CargoType("P2", "1.8L*6", "standard", 347, 238, 320, 0.0, QUANTITY_EACH, True, True, False, False),
    "P3": CargoType("P3", "4L*4", "standard", 318, 265, 380, 0.0, QUANTITY_EACH, True, True, False, False),
    "P4": CargoType("P4", "5L*4(异形瓶)", "standard", 345, 345, 395, 0.0, QUANTITY_EACH, True, True, False, False),
    "P5": CargoType("P5", "5L*4(常规品)", "standard", 323, 322, 385, 0.0, QUANTITY_EACH, True, True, False, False),
    "P6": CargoType("P6", "8L*2", "standard", 435, 226, 370, 0.0, QUANTITY_EACH, True, True, False, False),
    "P7": CargoType("P7", "10L*2", "standard", 438, 225, 430, 0.0, QUANTITY_EACH, True, True, False, False),
    "P8": CargoType("P8", "20L(软)", "standard", 306, 178, 495, 0.0, QUANTITY_EACH, True, True, False, False),
}

TRUCKS: Dict[str, Truck] = {
    "单节柜": Truck("单节柜", 5900, 2350, 2390, 1e18, 3625),
    "集装箱": Truck("集装箱", 12000, 2350, 2390, 1e18, 2000),
    "超高柜": Truck("超高柜", 12000, 2350, 2690, 1e18, 3900),
    "4.2米箱货": Truck("4.2米箱货", 4100, 1900, 2000, 1e18, 2800),
    "6.2米箱货": Truck("6.2米箱货", 6000, 2000, 1900, 1e18, 4500),
    "6.8米箱货": Truck("6.8米箱货", 6800, 2500, 2200, 1e18, 5000),
    "9.6米箱货": Truck("9.6米箱货", 9500, 2500, 2200, 1e18, 6500),
    "17米箱货": Truck("17米箱货", 17000, 2500, 2200, 1e18, 11000),
}

TYPE_ORDER = list(CARGO_TYPES.keys())

def generate_orientations(cargo: CargoType) -> Tuple[Orientation, ...]:
    l, w, h = cargo.length, cargo.width, cargo.height
    dims = [(l, w, h, "LWH"), (l, h, w, "LHW"), (w, l, h, "WLH"), (w, h, l, "WHL"), (h, l, w, "HLW"), (h, w, l, "HWL")]
    uniq: List[Orientation] = []
    seen = set()
    for a, b, c, name in dims:
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            uniq.append(Orientation(len(uniq), key, name))
    return tuple(uniq)

def truck_score(truck: Truck, used_volume: int) -> Tuple[float, float, float]:
    space_util = used_volume / truck.effective_volume if truck.effective_volume > 0 else 0.0
    return space_util, 0.0, space_util

def expand_items(counts: Dict[str, int]) -> List[CargoItem]:
    items: List[CargoItem] = []
    for type_id in TYPE_ORDER:
        cargo = CARGO_TYPES[type_id]
        n = counts.get(type_id, 0)
        if n <= 0:
            continue
        oris = generate_orientations(cargo)
        for i in range(1, n + 1):
            items.append(CargoItem(f"{type_id}_{i:03d}", type_id, cargo.category, (cargo.length, cargo.width, cargo.height), 0.0, cargo.volume, True, False, False, oris))
    return items

def alignment_score(truck: Truck, counts: Dict[str, int]) -> float:
    score = 0.0
    active = 0
    for t, n in counts.items():
        if n <= 0:
            continue
        c = CARGO_TYPES[t]
        best_local = 0.0
        for ori in generate_orientations(c):
            l, w, h = ori.size
            rx = truck.length % l
            ry = truck.width % w
            rz = truck.effective_height % h
            local = (1.0 / (1.0 + rx)) + (1.0 / (1.0 + ry)) + (1.0 / (1.0 + rz))
            if local > best_local:
                best_local = local
        score += best_local
        active += 1
    return score / max(1, active)

def count_score(truck: Truck, counts: Dict[str, int]) -> float:
    total_volume = sum(CARGO_TYPES[k].volume * v for k, v in counts.items())
    space_util, _, fullness = truck_score(truck, total_volume)
    if total_volume == 0:
        return -1e18
    vol_share = []
    for k in TYPE_ORDER:
        v = counts.get(k, 0) * CARGO_TYPES[k].volume
        if v > 0:
            vol_share.append(v / total_volume)
    concentration = sum(p * p for p in vol_share) if vol_share else 1.0
    align = alignment_score(truck, counts)
    return 0.90 * fullness - 0.03 * concentration + 0.07 * align

def best_grid_count(truck: Truck, cargo: CargoType) -> int:
    best = 0
    for ori in generate_orientations(cargo):
        l, w, h = ori.size
        nx = truck.length // l
        ny = truck.width // w
        nz = truck.effective_height // h
        best = max(best, nx * ny * nz)
    return best

def compute_upper_bounds(truck: Truck) -> Dict[str, int]:
    bounds: Dict[str, int] = {}
    for type_id, cargo in CARGO_TYPES.items():
        by_volume = truck.effective_volume // cargo.volume
        by_grid = best_grid_count(truck, cargo)
        bounds[type_id] = max(0, min(cargo.quantity, by_volume, by_grid))
    return bounds

def generate_count_candidates(truck: Truck, upper_bounds: Dict[str, int], trials: int = 180, keep: int = 24, seed: int = 2026) -> List[Dict[str, int]]:
    rng = random.Random(seed)
    seen = set()
    pool: List[Tuple[float, Dict[str, int]]] = []
    for trial in range(trials):
        counts = {t: 0 for t in TYPE_ORDER}
        used_volume = 0
        attempts = 0
        while attempts < 2500:
            feasible: List[Tuple[float, str]] = []
            for t in TYPE_ORDER:
                if counts[t] >= upper_bounds[t]:
                    continue
                c = CARGO_TYPES[t]
                if used_volume + c.volume > truck.effective_volume:
                    continue
                new_counts = counts.copy()
                new_counts[t] += 1
                score = count_score(truck, new_counts) + rng.uniform(-0.003, 0.003)
                feasible.append((score, t))
            if not feasible:
                break
            feasible.sort(key=lambda x: (x[0], CARGO_TYPES[x[1]].volume, CARGO_TYPES[x[1]].base_area), reverse=True)
            rcl_size = 2 + (trial % 3)
            chosen = rng.choice(feasible[: min(rcl_size, len(feasible))])[1]
            counts[chosen] += 1
            used_volume += CARGO_TYPES[chosen].volume
            attempts += 1
        best_counts = counts.copy()
        best_score = count_score(truck, best_counts)
        for _ in range(40):
            cand = best_counts.copy()
            move = rng.choice(["add", "remove", "swap"])
            if move == "add":
                candidates = sorted(TYPE_ORDER, key=lambda t: (CARGO_TYPES[t].volume, CARGO_TYPES[t].base_area), reverse=True)
                for t in candidates:
                    c = CARGO_TYPES[t]
                    if cand[t] < upper_bounds[t]:
                        cur_vol = sum(CARGO_TYPES[k].volume * cand[k] for k in TYPE_ORDER)
                        if cur_vol + c.volume <= truck.effective_volume:
                            cand[t] += 1
                            break
            elif move == "remove":
                nz = [t for t in TYPE_ORDER if cand[t] > 0]
                if nz:
                    cand[rng.choice(nz)] -= 1
            else:
                srcs = [t for t in TYPE_ORDER if cand[t] > 0]
                if srcs:
                    src = rng.choice(srcs)
                    dsts = sorted(TYPE_ORDER, key=lambda t: (CARGO_TYPES[t].volume, CARGO_TYPES[t].base_area), reverse=True)
                    for dst in dsts:
                        if src == dst or cand[dst] >= upper_bounds[dst]:
                            continue
                        cand[src] -= 1
                        cur_vol = sum(CARGO_TYPES[k].volume * cand[k] for k in TYPE_ORDER)
                        if cur_vol + CARGO_TYPES[dst].volume <= truck.effective_volume:
                            cand[dst] += 1
                            break
                        cand[src] += 1
            s = count_score(truck, cand)
            if s > best_score:
                best_score = s
                best_counts = cand
        key = tuple(best_counts[t] for t in TYPE_ORDER)
        if key not in seen and sum(best_counts.values()) > 0:
            seen.add(key)
            pool.append((best_score, best_counts))
    pool.sort(key=lambda x: x[0], reverse=True)
    return [counts for _, counts in pool[:keep]]

def sort_spaces_dblf(spaces: Sequence[Space]) -> List[Space]:
    return sorted(spaces, key=lambda s: (s.z, s.y, s.x, s.volume))

def remove_contained_spaces(spaces: List[Space]) -> List[Space]:
    result: List[Space] = []
    for i, a in enumerate(spaces):
        contained = False
        for j, b in enumerate(spaces):
            if i == j:
                continue
            if a.x >= b.x and a.y >= b.y and a.z >= b.z and a.x + a.length <= b.x + b.length and a.y + a.width <= b.y + b.width and a.z + a.height <= b.z + b.height and (a.x, a.y, a.z, a.length, a.width, a.height) != (b.x, b.y, b.z, b.length, b.width, b.height):
                contained = True
                break
        if not contained and a.length > 0 and a.width > 0 and a.height > 0:
            result.append(a)
    return result

def try_merge_two_spaces(a: Space, b: Space) -> Optional[Space]:
    if a.y == b.y and a.z == b.z and a.width == b.width and a.height == b.height:
        if a.x + a.length == b.x:
            return Space(a.x, a.y, a.z, a.length + b.length, a.width, a.height)
        if b.x + b.length == a.x:
            return Space(b.x, b.y, b.z, a.length + b.length, a.width, a.height)
    if a.x == b.x and a.z == b.z and a.length == b.length and a.height == b.height:
        if a.y + a.width == b.y:
            return Space(a.x, a.y, a.z, a.length, a.width + b.width, a.height)
        if b.y + b.width == a.y:
            return Space(b.x, b.y, b.z, a.length, a.width + b.width, a.height)
    if a.x == b.x and a.y == b.y and a.length == b.length and a.width == b.width:
        if a.z + a.height == b.z:
            return Space(a.x, a.y, a.z, a.length, a.width, a.height + b.height)
        if b.z + b.height == a.z:
            return Space(b.x, b.y, b.z, a.length, a.width, a.height + b.height)
    return None

def merge_spaces(spaces: List[Space]) -> List[Space]:
    spaces = remove_contained_spaces(spaces)
    changed = True
    while changed:
        changed = False
        n = len(spaces)
        for i in range(n):
            merged = False
            for j in range(i + 1, n):
                m = try_merge_two_spaces(spaces[i], spaces[j])
                if m is not None:
                    new_spaces = [spaces[k] for k in range(n) if k not in (i, j)]
                    new_spaces.append(m)
                    spaces = remove_contained_spaces(new_spaces)
                    changed = True
                    merged = True
                    break
            if merged:
                break
    return spaces

def build_item_orders(items: List[CargoItem], policy: int) -> List[CargoItem]:
    def ori_height(item: CargoItem) -> int:
        return max(o.size[2] for o in item.allowed_orientations)
    def base_area(item: CargoItem) -> int:
        return max(o.size[0] * o.size[1] for o in item.allowed_orientations)
    if policy == 0:
        return sorted(items, key=lambda it: (-it.volume, it.type_id, it.item_id))
    if policy == 1:
        return sorted(items, key=lambda it: (-base_area(it), -ori_height(it), -it.volume, it.item_id))
    if policy == 2:
        return sorted(items, key=lambda it: (-ori_height(it), -it.volume, it.item_id))
    if policy == 3:
        return sorted(items, key=lambda it: (-it.volume, -base_area(it), it.item_id))
    return sorted(items, key=lambda it: (-max(o.size[0] * o.size[1] for o in it.allowed_orientations), -it.volume, -max(o.size[2] for o in it.allowed_orientations), it.item_id))

def can_place_in_space(item: CargoItem, ori: Orientation, space: Space) -> bool:
    l, w, h = ori.size
    return l <= space.length and w <= space.width and h <= space.height

def placement_gain(truck: Truck, state: LayoutState, item: CargoItem, ori: Orientation, space: Space) -> float:
    l, w, h = ori.size
    fill_ratio = (l * w * h) / max(1, space.length * space.width * space.height)
    low_z_bonus = 1.0 / (1.0 + space.z)
    tight_bonus = 1.0 / (1.0 + (space.length - l) + (space.width - w) + (space.height - h))
    base_bonus = (l * w) / max(1, space.length * space.width)
    used_volume = state.used_volume + item.volume
    space_util, _, fullness = truck_score(truck, used_volume)
    return fullness + 0.12 * fill_ratio + 0.04 * low_z_bonus + 0.03 * tight_bonus + 0.05 * base_bonus + 0.03 * space_util

def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    new_spaces: List[Space] = []
    if space.length > placed.length:
        new_spaces.append(Space(space.x + placed.length, space.y, space.z, space.length - placed.length, space.width, space.height))
    if space.width > placed.width:
        new_spaces.append(Space(space.x, space.y + placed.width, space.z, placed.length, space.width - placed.width, space.height))
    if space.height > placed.height:
        new_spaces.append(Space(space.x, space.y, space.z + placed.height, placed.length, placed.width, space.height - placed.height))
    return new_spaces

def apply_placement(truck: Truck, state: LayoutState, item_idx: int, ori: Orientation, space_idx: int) -> LayoutState:
    item = state.remaining[item_idx]
    space = state.spaces[space_idx]
    l, w, h = ori.size
    placed = PlacedCargo(item.item_id, item.type_id, item.category, space.x, space.y, space.z, l, w, h, 0.0, ori.orient_id, ori.rotation, truck_id=truck.name)
    new_placed = list(state.placed)
    new_placed.append(placed)
    new_spaces = [s for idx, s in enumerate(state.spaces) if idx != space_idx]
    new_spaces.extend(split_space(space, placed))
    new_spaces = merge_spaces(new_spaces)
    new_spaces = sort_spaces_dblf(new_spaces)
    new_remaining = state.remaining[:item_idx] + state.remaining[item_idx + 1:]
    used_volume = state.used_volume + item.volume
    space_util, _, fullness = truck_score(truck, used_volume)
    packed_ratio = len(new_placed) / max(1, len(new_placed) + len(new_remaining))
    return LayoutState(new_spaces, new_placed, new_remaining, 0.0, used_volume, fullness + 0.025 * packed_ratio + 0.015 * space_util, packed_ratio)

def pack_with_beam_search(truck: Truck, items: List[CargoItem], beam_width: int = 5, candidate_items_each_step: int = 6, candidate_moves_each_state: int = 12, policy: int = 0) -> LayoutState:
    ordered = build_item_orders(items, policy)
    init = LayoutState([Space(0, 0, 0, truck.length, truck.width, truck.effective_height)], [], ordered, 0.0, 0, 0.0, 0.0)
    beam: List[LayoutState] = [init]
    best = init
    while beam:
        next_beam: List[LayoutState] = []
        expanded_any = False
        for state in beam:
            if state.score > best.score or state.used_volume > best.used_volume:
                best = state
            if not state.remaining or not state.spaces:
                next_beam.append(state)
                continue
            item_candidates = state.remaining[: min(candidate_items_each_step, len(state.remaining))]
            move_pool: List[Tuple[float, int, Orientation, int]] = []
            for item_idx, item in enumerate(item_candidates):
                for space_idx, space in enumerate(state.spaces[: min(14, len(state.spaces))]):
                    for ori in item.allowed_orientations:
                        if can_place_in_space(item, ori, space):
                            gain = placement_gain(truck, state, item, ori, space)
                            move_pool.append((gain, item_idx, ori, space_idx))
            move_pool.sort(key=lambda x: x[0], reverse=True)
            move_pool = move_pool[:candidate_moves_each_state]
            if not move_pool:
                next_beam.append(state)
                continue
            expanded_any = True
            for _, item_idx, ori, space_idx in move_pool:
                next_beam.append(apply_placement(truck, state, item_idx, ori, space_idx))
        if not expanded_any:
            break
        next_beam.sort(key=lambda st: (st.score, st.used_volume, len(st.placed)), reverse=True)
        beam = next_beam[:beam_width]
        if beam and (beam[0].score > best.score or beam[0].used_volume > best.used_volume):
            best = beam[0]
    return best

def evaluate_candidate(truck: Truck, counts: Dict[str, int], beam_width: int):
    items = expand_items(counts)
    best_state = None
    best_meta = {}
    for policy in range(5):
        state = pack_with_beam_search(truck, items, beam_width=beam_width, candidate_items_each_step=6, candidate_moves_each_state=12, policy=policy)
        if best_state is None or state.used_volume > best_state.used_volume:
            best_state = state
            best_meta = {"policy_index": policy}
    actual_counts = Counter(p.type_id for p in best_state.placed)
    target_counts = {k: v for k, v in counts.items() if v > 0}
    space_util, _, fullness = truck_score(truck, best_state.used_volume)
    packed_ratio = sum(actual_counts.values()) / max(1, sum(target_counts.values()))
    meta = {"truck": truck.name, "space_utilization": round(space_util, 6), "fullness_score": round(fullness, 6), "loaded_volume_mm3": int(best_state.used_volume), "target_counts": target_counts, "actual_counts": dict(actual_counts), "placed_item_count": len(best_state.placed), "packed_ratio": round(packed_ratio, 6), **best_meta}
    return best_state, meta

def solve_problem_11(truck: Truck, topk: int = 8, beam_width: int = 5, trials: int = 180, seed: int = 2026):
    upper_bounds = compute_upper_bounds(truck)
    candidates = generate_count_candidates(truck, upper_bounds, trials=trials, keep=max(topk * 2, 16), seed=seed)
    best_state = None
    best_meta = {}
    for idx, counts in enumerate(candidates[:topk]):
        state, meta = evaluate_candidate(truck, counts, beam_width=beam_width)
        meta["candidate_index"] = idx
        if best_state is None or (state.used_volume, meta.get("packed_ratio", 0.0)) > (best_state.used_volume, best_meta.get("packed_ratio", 0.0)):
            best_state, best_meta = state, meta
    return best_state, best_meta, upper_bounds

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def write_csv(path: str, header: List[str], rows: List[List[object]]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def write_problem11_results(outdir: str, results: List[Dict[str, object]]) -> None:
    rows = []
    for r in results:
        actual_named = {CARGO_TYPES[k].name: v for k, v in r["actual_counts"].items()}
        rows.append([r["truck_name"], r["truck_length_mm"], r["truck_width_mm"], r["truck_height_mm"], r["truck_volume_mm3"], r["used_volume_mm3"], r["space_utilization"], r["placed_item_count"], str(actual_named)])
    write_csv(os.path.join(outdir, "problem11_single_truck_fullness.csv"), ["truck_name", "truck_length_mm", "truck_width_mm", "truck_height_mm", "truck_volume_mm3", "used_volume_mm3", "space_utilization", "placed_item_count", "actual_counts_named"], rows)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(base_dir, "附件2_通用性检验结果_优化版")
    print(f"读取产品种类数: {len(CARGO_TYPES)}")
    print(f"读取典型封闭车型数: {len(TRUCKS)}")
    print(f"产品列表: {[CARGO_TYPES[k].name for k in TYPE_ORDER]}")
    print(f"车型列表: {list(TRUCKS.keys())}")
    results = []
    for truck_name, truck in TRUCKS.items():
        print(f"\n开始求解问题1.1：{truck.name}")
        state, meta, _ = solve_problem_11(truck, topk=8, beam_width=5, trials=180, seed=2026)
        result = {"truck_name": truck.name, "truck_length_mm": truck.length, "truck_width_mm": truck.width, "truck_height_mm": truck.height, "truck_volume_mm3": truck.effective_volume, "used_volume_mm3": state.used_volume, "space_utilization": round(state.used_volume / truck.effective_volume, 6), "placed_item_count": len(state.placed), "actual_counts": dict(Counter(p.type_id for p in state.placed))}
        results.append(result)
        print(result)
    results.sort(key=lambda x: x["space_utilization"], reverse=True)
    write_problem11_results(outdir, results)
    print("\n问题1.1结果（前3名车型）:")
    for r in results[:3]:
        print(r)
    print(f"\n输出目录: {outdir}")

if __name__ == "__main__":
    main()
