from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Iterable
from collections import defaultdict
import argparse
import csv
import copy
import math
import random


# ============================================================
# Data structures aligned with the user's modeling files
# ============================================================

@dataclass(frozen=True)
class Orientation:
    orient_id: int
    size: Tuple[int, int, int]
    rotation: str


@dataclass
class CargoType:
    type_id: str
    category: str  # standard / fragile / oriented
    length: int
    width: int
    height: int
    weight: float
    quantity: int
    stackable: bool
    can_rotate: bool
    fragile: bool
    oriented: bool
    max_support_pressure: float = 500.0   # kg / m^2
    top_clearance: int = 3

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def density(self) -> float:
        return self.weight / (self.volume / 1_000_000.0)


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


@dataclass(frozen=True)
class TruckSpec:
    truck_id: str
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
class FreeSpace:
    x: int
    y: int
    z: int
    length: int
    width: int
    height: int
    support_type: Optional[str] = None
    support_id: Optional[str] = None
    support_capacity_kg: float = float("inf")

    def dblf_key(self) -> Tuple[int, int, int]:
        # Deepest-bottom-left ordering adapted from DBLF
        return (-self.z, self.y, self.x)


@dataclass
class DecodeState:
    truck: TruckSpec
    spaces: List[FreeSpace] = field(default_factory=list)
    placed: List[PlacedCargo] = field(default_factory=list)
    loaded_weight: float = 0.0
    loaded_volume: int = 0

    def __post_init__(self) -> None:
        if not self.spaces:
            self.spaces = [
                FreeSpace(
                    0, 0, 0,
                    self.truck.length,
                    self.truck.width,
                    self.truck.effective_height,
                    support_type="floor",
                    support_id="floor",
                    support_capacity_kg=float("inf"),
                )
            ]

    @property
    def space_utilization(self) -> float:
        return self.loaded_volume / self.truck.effective_volume

    @property
    def weight_utilization(self) -> float:
        return self.loaded_weight / self.truck.max_weight

    @property
    def fullness_score(self) -> float:
        return 0.5 * self.space_utilization + 0.5 * self.weight_utilization


# ============================================================
# Basic data
# ============================================================


def build_truck_specs() -> Dict[str, TruckSpec]:
    return {
        "车型1": TruckSpec("车型1", 420, 210, 220, 6000.0, 450.0),
        "车型2": TruckSpec("车型2", 680, 245, 250, 10000.0, 700.0),
    }



def build_cargo_types() -> Dict[str, CargoType]:
    return {
        "G1": CargoType("G1", "standard", 60, 40, 30, 12.0, 800, True, True, False, False),
        "G2": CargoType("G2", "standard", 50, 35, 25, 8.0, 1000, True, True, False, False),
        "G3": CargoType("G3", "fragile", 70, 50, 40, 15.0, 300, False, True, True, False),
        "G4": CargoType("G4", "oriented", 80, 60, 50, 25.0, 400, True, False, False, True),
        "G5": CargoType("G5", "oriented", 40, 40, 60, 18.0, 500, True, False, False, True),
    }


# ============================================================
# Orientation handling
# ============================================================


def generate_orientations(cargo: CargoType) -> List[Orientation]:
    l, w, h = cargo.length, cargo.width, cargo.height
    raw = [
        (l, w, h, "LWH"),
        (l, h, w, "LHW"),
        (w, l, h, "WLH"),
        (w, h, l, "WHL"),
        (h, l, w, "HLW"),
        (h, w, l, "HWL"),
    ]

    if cargo.fragile:
        raw = [(l, w, h, "LWH"), (w, l, h, "WLH")]
    if cargo.oriented:
        raw = [(l, w, h, "LWH")]

    out: List[Orientation] = []
    seen = set()
    for i, (a, b, c, name) in enumerate(raw, start=1):
        if (a, b, c) not in seen:
            seen.add((a, b, c))
            out.append(Orientation(len(out) + 1, (a, b, c), name))
    return out


# ============================================================
# Stage 1: count optimization (type-count search only)
# ============================================================

@dataclass(frozen=True)
class CountState:
    counts: Tuple[int, ...]
    weight: float
    volume: int


@dataclass(frozen=True)
class CountCandidate:
    counts: Tuple[int, ...]
    weight: float
    volume: int
    score: float


TYPE_ORDER = ("G1", "G2", "G3", "G4", "G5")



def single_truck_upper_bounds(truck: TruckSpec, cargo_types: Dict[str, CargoType]) -> Dict[str, int]:
    ub: Dict[str, int] = {}
    for t in TYPE_ORDER:
        cargo = cargo_types[t]
        ub[t] = min(
            cargo.quantity,
            truck.effective_volume // cargo.volume,
            int(truck.max_weight // cargo.weight),
        )
    return ub



def candidate_score(volume: int, weight: float, truck: TruckSpec, alpha: float, balance_penalty: float) -> float:
    vr = volume / truck.effective_volume
    wr = weight / truck.max_weight
    return alpha * vr + (1.0 - alpha) * wr - balance_penalty * abs(vr - wr)



def prune_states(states: Iterable[CountState], truck: TruckSpec, alpha: float, balance_penalty: float, beam_width: int) -> List[CountState]:
    best_by_counts: Dict[Tuple[int, ...], CountState] = {}
    for s in states:
        prev = best_by_counts.get(s.counts)
        if prev is None:
            best_by_counts[s.counts] = s
    unique = list(best_by_counts.values())
    unique.sort(
        key=lambda s: (
            candidate_score(s.volume, s.weight, truck, alpha, balance_penalty),
            s.volume,
            s.weight,
        ),
        reverse=True,
    )

    filtered: List[CountState] = []
    frontier: List[CountState] = []
    for s in unique:
        dominated = False
        for p in frontier:
            if p.weight <= s.weight and p.volume >= s.volume and (p.weight < s.weight or p.volume > s.volume):
                dominated = True
                break
        if not dominated:
            frontier.append(s)
            filtered.append(s)
        if len(filtered) >= beam_width:
            break
    return filtered



def count_grid(max_c: int) -> List[int]:
    if max_c <= 20:
        return list(range(max_c + 1))
    pts = {0, max_c}
    for c in range(1, min(12, max_c) + 1):
        pts.add(c)
    step = max(1, max_c // 10)
    for c in range(0, max_c + 1, step):
        pts.add(c)
    for r in [0.25, 0.40, 0.55, 0.70, 0.85, 0.95]:
        pts.add(min(max_c, max(0, int(round(max_c * r)))))
    return sorted(pts)


def build_count_candidates(
    truck: TruckSpec,
    cargo_types: Dict[str, CargoType],
    beam_width: int = 320,
    top_k: int = 80,
) -> List[CountCandidate]:
    ub = single_truck_upper_bounds(truck, cargo_types)
    type_list = list(TYPE_ORDER)

    all_candidates: Dict[Tuple[int, ...], CountCandidate] = {}
    alpha_grid = [0.35, 0.50, 0.65]
    penalty_grid = [0.00, 0.10]

    coarse_grid = {t: count_grid(ub[t]) for t in type_list}

    for alpha in alpha_grid:
        for penalty in penalty_grid:
            frontier = [CountState(tuple(), 0.0, 0)]
            for t in type_list:
                cargo = cargo_types[t]
                new_states: List[CountState] = []
                for s in frontier:
                    max_c = min(
                        ub[t],
                        int((truck.max_weight - s.weight) // cargo.weight),
                        (truck.effective_volume - s.volume) // cargo.volume,
                    )
                    for c in coarse_grid[t]:
                        if c > max_c:
                            break
                        new_states.append(
                            CountState(
                                s.counts + (c,),
                                s.weight + c * cargo.weight,
                                s.volume + c * cargo.volume,
                            )
                        )
                frontier = prune_states(new_states, truck, alpha, penalty, beam_width)

            for s in frontier:
                sc = candidate_score(s.volume, s.weight, truck, alpha, penalty)
                key = s.counts
                old = all_candidates.get(key)
                if old is None or sc > old.score:
                    all_candidates[key] = CountCandidate(key, s.weight, s.volume, sc)

    # Local refinement around strong coarse solutions.
    seeds = sorted(all_candidates.values(), key=lambda x: (x.score, x.volume, x.weight), reverse=True)[:40]
    for cand in seeds:
        base = list(cand.counts)
        for i, t in enumerate(type_list):
            local_points = {base[i]}
            for delta in (-12, -8, -4, -2, -1, 1, 2, 4, 8, 12):
                local_points.add(max(0, min(ub[t], base[i] + delta)))
            for c in local_points:
                counts = base[:]
                counts[i] = c
                wt = sum(counts[j] * cargo_types[type_list[j]].weight for j in range(len(type_list)))
                vol = sum(counts[j] * cargo_types[type_list[j]].volume for j in range(len(type_list)))
                if wt <= truck.max_weight and vol <= truck.effective_volume:
                    sc = candidate_score(vol, wt, truck, 0.5, 0.1)
                    key = tuple(counts)
                    old = all_candidates.get(key)
                    if old is None or sc > old.score:
                        all_candidates[key] = CountCandidate(key, wt, vol, sc)

    ranked = sorted(all_candidates.values(), key=lambda x: (x.score, x.volume, x.weight), reverse=True)
    return ranked[:top_k]


# ============================================================
# Stage 2: detailed layout verification and refinement
# ============================================================


def remove_contained_spaces(spaces: List[FreeSpace]) -> List[FreeSpace]:
    kept: List[FreeSpace] = []
    for i, a in enumerate(spaces):
        ax2, ay2, az2 = a.x + a.length, a.y + a.width, a.z + a.height
        contained = False
        for j, b in enumerate(spaces):
            if i == j:
                continue
            bx2, by2, bz2 = b.x + b.length, b.y + b.width, b.z + b.height
            if a.support_id != b.support_id:
                continue
            if a.x >= b.x and a.y >= b.y and a.z >= b.z and ax2 <= bx2 and ay2 <= by2 and az2 <= bz2:
                contained = True
                break
        if not contained:
            kept.append(a)
    return kept



def merge_spaces(spaces: List[FreeSpace]) -> List[FreeSpace]:
    out = spaces[:]
    changed = True
    while changed:
        changed = False
        used = [False] * len(out)
        new_spaces: List[FreeSpace] = []
        for i in range(len(out)):
            if used[i]:
                continue
            a = out[i]
            merged = False
            for j in range(i + 1, len(out)):
                if used[j]:
                    continue
                b = out[j]
                if (a.support_id, a.support_type) != (b.support_id, b.support_type):
                    continue
                if abs(a.support_capacity_kg - b.support_capacity_kg) > 1e-9:
                    continue
                # merge x
                if a.y == b.y and a.z == b.z and a.width == b.width and a.height == b.height:
                    if a.x + a.length == b.x:
                        new_spaces.append(FreeSpace(a.x, a.y, a.z, a.length + b.length, a.width, a.height, a.support_type, a.support_id, a.support_capacity_kg))
                        used[i] = used[j] = True
                        changed = True
                        merged = True
                        break
                    if b.x + b.length == a.x:
                        new_spaces.append(FreeSpace(b.x, a.y, a.z, a.length + b.length, a.width, a.height, a.support_type, a.support_id, a.support_capacity_kg))
                        used[i] = used[j] = True
                        changed = True
                        merged = True
                        break
                # merge y
                if a.x == b.x and a.z == b.z and a.length == b.length and a.height == b.height:
                    if a.y + a.width == b.y:
                        new_spaces.append(FreeSpace(a.x, a.y, a.z, a.length, a.width + b.width, a.height, a.support_type, a.support_id, a.support_capacity_kg))
                        used[i] = used[j] = True
                        changed = True
                        merged = True
                        break
                    if b.y + b.width == a.y:
                        new_spaces.append(FreeSpace(a.x, b.y, a.z, a.length, a.width + b.width, a.height, a.support_type, a.support_id, a.support_capacity_kg))
                        used[i] = used[j] = True
                        changed = True
                        merged = True
                        break
            if not merged and not used[i]:
                used[i] = True
                new_spaces.append(a)
        out = remove_contained_spaces(new_spaces)
    return out



def feasible_in_space(cargo: CargoType, orient: Orientation, space: FreeSpace, state: DecodeState) -> bool:
    l, w, h = orient.size
    if l > space.length or w > space.width or h > space.height:
        return False
    if state.loaded_weight + cargo.weight > state.truck.max_weight + 1e-9:
        return False
    if space.z + h > state.truck.effective_height:
        return False
    if cargo.fragile and space.z > 0 and space.support_type != "standard":
        return False
    if space.z > 0 and cargo.weight > space.support_capacity_kg + 1e-9:
        return False
    return True



def placement_score(
    cargo: CargoType,
    orient: Orientation,
    space: FreeSpace,
    state: DecodeState,
    policy: Dict[str, float],
    type_priority_rank: Dict[str, int],
) -> float:
    l, w, h = orient.size
    fill = (l * w * h) / (space.length * space.width * space.height)
    vr = cargo.volume / state.truck.effective_volume
    wr = cargo.weight / state.truck.max_weight
    footprint_fit = (l * w) / max(1, space.length * space.width)
    base_bonus = 1.0 if space.z == 0 else 0.0
    rank_bonus = (len(type_priority_rank) - type_priority_rank.get(cargo.type_id, len(type_priority_rank))) / max(1, len(type_priority_rank))
    fragile_floor_bonus = 1.0 if (cargo.fragile and space.z == 0) else 0.0
    top_penalty = 1.0 if (cargo.fragile and space.z > 0) else 0.0
    tall_penalty = h / max(1, state.truck.effective_height)
    return (
        policy["fill"] * fill
        + policy["vol"] * vr
        + policy["wt"] * wr
        + policy["footprint"] * footprint_fit
        + policy["base"] * base_bonus
        + policy["priority"] * rank_bonus
        + policy["fragile_floor"] * fragile_floor_bonus
        - policy["fragile_top_penalty"] * top_penalty
        - policy["tall_penalty"] * tall_penalty
    )



def split_space(space: FreeSpace, cargo: CargoType, orient: Orientation, item_id: str) -> List[FreeSpace]:
    l, w, h = orient.size
    x, y, z = space.x, space.y, space.z
    out: List[FreeSpace] = []
    if space.length > l:
        out.append(FreeSpace(x + l, y, z, space.length - l, space.width, space.height, space.support_type, space.support_id, space.support_capacity_kg))
    if space.width > w:
        out.append(FreeSpace(x, y + w, z, l, space.width - w, space.height, space.support_type, space.support_id, space.support_capacity_kg))
    if space.height > h and cargo.stackable:
        cap = cargo.max_support_pressure * ((l * w) / 10000.0)
        out.append(FreeSpace(x, y, z + h, l, w, space.height - h, cargo.category, item_id, cap))
    return [s for s in out if s.length > 0 and s.width > 0 and s.height > 0]



def make_item_pool(counts: Dict[str, int]) -> Dict[str, List[str]]:
    pool: Dict[str, List[str]] = {}
    for t, c in counts.items():
        pool[t] = [f"{t}_{i:04d}" for i in range(1, c + 1)]
    return pool



def decode_counts_with_policy(
    truck: TruckSpec,
    cargo_types: Dict[str, CargoType],
    target_counts: Dict[str, int],
    type_priority: List[str],
    policy: Dict[str, float],
) -> Tuple[DecodeState, bool]:
    remain = target_counts.copy()
    item_pool = make_item_pool(target_counts)
    state = DecodeState(truck)
    rank = {t: i for i, t in enumerate(type_priority)}

    max_spaces_considered = 28
    while sum(remain.values()) > 0:
        state.spaces.sort(key=lambda s: s.dblf_key())
        if len(state.spaces) > 80:
            state.spaces = state.spaces[:80]
        best: Optional[Tuple[int, str, Orientation, float]] = None
        for s_idx, space in enumerate(state.spaces[:max_spaces_considered]):
            for t in type_priority:
                if remain.get(t, 0) <= 0:
                    continue
                cargo = cargo_types[t]
                for orient in generate_orientations(cargo):
                    if not feasible_in_space(cargo, orient, space, state):
                        continue
                    sc = placement_score(cargo, orient, space, state, policy, rank)
                    if best is None or sc > best[3]:
                        best = (s_idx, t, orient, sc)
        if best is None:
            break

        s_idx, t, orient, _ = best
        cargo = cargo_types[t]
        space = state.spaces[s_idx]
        item_id = item_pool[t].pop(0)
        l, w, h = orient.size
        state.placed.append(
            PlacedCargo(
                item_id=item_id,
                type_id=t,
                category=cargo.category,
                x=space.x,
                y=space.y,
                z=space.z,
                length=l,
                width=w,
                height=h,
                weight=cargo.weight,
                orientation_id=orient.orient_id,
                rotation=orient.rotation,
                support_by=space.support_id,
                truck_id=truck.truck_id,
            )
        )
        state.loaded_weight += cargo.weight
        state.loaded_volume += cargo.volume
        remain[t] -= 1

        new_spaces = split_space(space, cargo, orient, item_id)
        del state.spaces[s_idx]
        state.spaces.extend(new_spaces)
        state.spaces = merge_spaces(remove_contained_spaces(state.spaces))

    success = all(v == 0 for v in remain.values())
    return state, success



def build_decode_policies(cargo_types: Dict[str, CargoType]) -> List[Tuple[List[str], Dict[str, float]]]:
    by_density = sorted(TYPE_ORDER, key=lambda t: cargo_types[t].density, reverse=True)
    by_volume = sorted(TYPE_ORDER, key=lambda t: cargo_types[t].volume, reverse=True)
    by_base = sorted(TYPE_ORDER, key=lambda t: max((o.size[0] * o.size[1] for o in generate_orientations(cargo_types[t]))), reverse=True)
    fragile_last = sorted(TYPE_ORDER, key=lambda t: (cargo_types[t].fragile, cargo_types[t].volume), reverse=True)
    standard_first = sorted(TYPE_ORDER, key=lambda t: (cargo_types[t].category != "standard", -cargo_types[t].volume))

    policies = [
        (by_density, {"fill": 0.35, "vol": 0.22, "wt": 0.18, "footprint": 0.10, "base": 0.06, "priority": 0.04, "fragile_floor": 0.09, "fragile_top_penalty": 0.20, "tall_penalty": 0.04}),
        (by_volume,  {"fill": 0.38, "vol": 0.25, "wt": 0.12, "footprint": 0.12, "base": 0.05, "priority": 0.03, "fragile_floor": 0.07, "fragile_top_penalty": 0.20, "tall_penalty": 0.03}),
        (by_base,    {"fill": 0.30, "vol": 0.18, "wt": 0.18, "footprint": 0.18, "base": 0.08, "priority": 0.04, "fragile_floor": 0.08, "fragile_top_penalty": 0.22, "tall_penalty": 0.04}),
        (fragile_last,{"fill": 0.34, "vol": 0.20, "wt": 0.18, "footprint": 0.10, "base": 0.08, "priority": 0.04, "fragile_floor": 0.10, "fragile_top_penalty": 0.25, "tall_penalty": 0.03}),
        (standard_first,{"fill": 0.33, "vol": 0.19, "wt": 0.19, "footprint": 0.11, "base": 0.08, "priority": 0.05, "fragile_floor": 0.10, "fragile_top_penalty": 0.20, "tall_penalty": 0.03}),
    ]
    return policies



def local_count_neighbors(counts: Dict[str, int]) -> List[Dict[str, int]]:
    out: List[Dict[str, int]] = []
    keys = list(TYPE_ORDER)
    for a in keys:
        for b in keys:
            if a == b:
                continue
            for da, db in [(1, -1), (-1, 1), (2, -2), (-2, 2)]:
                nxt = counts.copy()
                nxt[a] = max(0, nxt[a] + da)
                nxt[b] = max(0, nxt[b] + db)
                out.append(nxt)
    return out



def counts_to_metrics(counts: Dict[str, int], cargo_types: Dict[str, CargoType]) -> Tuple[float, int]:
    wt = sum(counts[t] * cargo_types[t].weight for t in TYPE_ORDER)
    vol = sum(counts[t] * cargo_types[t].volume for t in TYPE_ORDER)
    return wt, vol



def solve_problem_1_1(
    truck: TruckSpec,
    cargo_types: Dict[str, CargoType],
    candidate_top_k: int = 80,
) -> Tuple[DecodeState, Dict[str, int], Dict[str, object]]:
    count_candidates = build_count_candidates(truck, cargo_types, top_k=candidate_top_k)
    policies = build_decode_policies(cargo_types)

    best_state: Optional[DecodeState] = None
    best_counts: Optional[Dict[str, int]] = None
    best_info: Dict[str, object] = {}

    tried_count_vectors = set()
    trial_queue: List[Dict[str, int]] = []

    for cand in count_candidates[:min(len(count_candidates), 18)]:
        cnt = {TYPE_ORDER[i]: cand.counts[i] for i in range(len(TYPE_ORDER))}
        trial_queue.append(cnt)
        # add small local neighbors for precise verification
        for nei in local_count_neighbors(cnt)[:6]:
            wt, vol = counts_to_metrics(nei, cargo_types)
            if wt <= truck.max_weight and vol <= truck.effective_volume:
                trial_queue.append(nei)

    # deduplicate while preserving order
    deduped: List[Dict[str, int]] = []
    for cnt in trial_queue:
        key = tuple(cnt[t] for t in TYPE_ORDER)
        if key not in tried_count_vectors:
            tried_count_vectors.add(key)
            deduped.append(cnt)

    for idx, cnt in enumerate(deduped, start=1):
        wt, vol = counts_to_metrics(cnt, cargo_types)
        if wt > truck.max_weight or vol > truck.effective_volume:
            continue
        for p_idx, (type_priority, policy) in enumerate(policies, start=1):
            state, ok = decode_counts_with_policy(truck, cargo_types, cnt, type_priority, policy)
            packed_ratio = len(state.placed) / max(1, sum(cnt.values()))
            score = state.fullness_score + (0.15 if ok else 0.0) + 0.08 * packed_ratio
            if best_state is None or score > (best_info["score"]):
                best_state = state
                best_counts = cnt.copy()
                best_info = {
                    "score": score,
                    "feasible_full_pack": ok,
                    "candidate_index": idx,
                    "policy_index": p_idx,
                    "packed_ratio": packed_ratio,
                    "target_counts": cnt.copy(),
                    "placed_count": len(state.placed),
                }
            if ok and state.space_utilization >= 0.97 and state.weight_utilization >= 0.90:
                return best_state, best_counts, best_info

    if best_state is None or best_counts is None:
        raise RuntimeError("未能构造出任何可行的单车装载方案。")
    return best_state, best_counts, best_info


# ============================================================
# Output helpers
# ============================================================


def write_items_csv(path: str, items: List[PlacedCargo]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_id", "type_id", "category", "truck_id", "x", "y", "z",
            "length", "width", "height", "weight", "orientation_id", "rotation", "support_by"
        ])
        for p in items:
            writer.writerow([
                p.item_id, p.type_id, p.category, p.truck_id, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight, p.orientation_id, p.rotation, p.support_by or ""
            ])



def summarize_solution(state: DecodeState, counts: Dict[str, int], info: Dict[str, object]) -> Dict[str, object]:
    type_counts = defaultdict(int)
    for p in state.placed:
        type_counts[p.type_id] += 1
    return {
        "truck": state.truck.truck_id,
        "space_utilization": round(state.space_utilization, 6),
        "weight_utilization": round(state.weight_utilization, 6),
        "fullness_score": round(state.fullness_score, 6),
        "loaded_weight_kg": round(state.loaded_weight, 3),
        "loaded_volume_cm3": state.loaded_volume,
        "target_counts": counts,
        "actual_counts": dict(type_counts),
        "placed_item_count": len(state.placed),
        "feasible_full_pack": info.get("feasible_full_pack"),
        "packed_ratio": round(float(info.get("packed_ratio", 0.0)), 6),
        "candidate_index": info.get("candidate_index"),
        "policy_index": info.get("policy_index"),
    }


# ============================================================
# CLI
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="MathorCup D题 问题1.1 专用：计数优化 + 精细布局验证")
    parser.add_argument("--topk", type=int, default=80, help="第一阶段保留的计数组合数量")
    args = parser.parse_args()

    trucks = build_truck_specs()
    cargo_types = build_cargo_types()

    for truck_name in ["车型1", "车型2"]:
        truck = trucks[truck_name]

        print("\n" + "=" * 50)
        print(f"开始求解：{truck.truck_id}")
        print("=" * 50)

        ub = single_truck_upper_bounds(truck, cargo_types)
        print(f"[{truck.truck_id}] 单车上界: {ub}")

        state, counts, info = solve_problem_1_1(
            truck,
            cargo_types,
            candidate_top_k=args.topk
        )

        summary = summarize_solution(state, counts, info)
        print(summary)

        out_csv = f"{truck.truck_id}_问题1_1_计数优化版装箱明细.csv"
        write_items_csv(out_csv, state.placed)
        print(f"装箱明细已写入: {out_csv}")


if __name__ == "__main__":
    main()
