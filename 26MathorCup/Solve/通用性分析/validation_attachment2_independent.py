#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
附件2通用性检验（独立版）
- 问题1.1：使用 Count-Layout Beam Heuristic for 3D Packing
- 问题1.2：重复调用问题1.1单车装载器，得到单车型下最少车辆数

简化假设：
1. 每种箱装产品数量统一为 100 件；
2. 不考虑重量约束；
3. 全部按标准件处理；
4. 只选典型封闭车型；
5. 目标是验证模型与算法对新尺寸数据、车型数据的通用性。
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from openpyxl import load_workbook


# ============================================================
# 数据结构
# ============================================================

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
    max_support_pressure: float = 1e18  # 本验证不考虑承压，给很大值

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def density(self) -> float:
        if self.volume <= 0:
            return 0.0
        return self.weight / self.volume


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
    direct_supported_weight: float = 0.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def top_area_m2(self) -> float:
        return (self.length * self.width) / 1_000_000.0


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
    support_item_id: Optional[str] = None
    support_type_id: Optional[str] = None
    support_length: Optional[int] = None
    support_width: Optional[int] = None

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


# ============================================================
# 全局数据容器
# ============================================================

CARGO_TYPES: Dict[str, CargoType] = {}
TRUCKS: Dict[str, Truck] = {}
TYPE_ORDER: List[str] = []


# ============================================================
# Excel读取
# ============================================================

def safe_str(x) -> str:
    return "" if x is None else str(x).strip()


def parse_mm_from_text(text) -> Optional[int]:
    """
    将 '345-347'、'5.8-5.9米'、'2米'、'1900' 这类文本解析成 mm。
    规则：取区间上界；含“米”则转成 mm；否则按 mm 处理。
    """
    s = safe_str(text)
    if not s:
        return None
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if not nums:
        return None
    val = max(float(x) for x in nums)
    if "米" in s:
        return int(round(val * 1000))
    return int(round(val))


def load_attachment2(excel_path: str, quantity_each: int = 100) -> Tuple[Dict[str, CargoType], Dict[str, Truck]]:
    wb = load_workbook(excel_path, data_only=True)

    # ---------------- 产品表 ----------------
    if "箱装产品尺寸" not in wb.sheetnames:
        raise ValueError("Excel中未找到工作表：箱装产品尺寸")
    ws_prod = wb["箱装产品尺寸"]

    products: Dict[str, CargoType] = {}
    pid = 1

    # 约定：
    # A列 产品名
    # 优先读“仓库测量尺寸”，取长宽高三列；若缺失，再尝试其他非空尺寸列
    rows = list(ws_prod.iter_rows(values_only=True))
    for row in rows[1:]:
        if row is None:
            continue
        name = safe_str(row[0])
        if not name:
            continue

        # 从整行提取所有可解析尺寸
        vals = [parse_mm_from_text(v) for v in row[1:]]
        vals = [v for v in vals if v is not None]

        if len(vals) < 3:
            continue

        # 一般表里前半部分是化验尺寸、后半部分是仓库测量尺寸
        # 这里优先取后3个非空值作为仓库测量尺寸
        length, width, height = vals[-3], vals[-2], vals[-1]

        type_id = f"P{pid}"
        pid += 1
        products[type_id] = CargoType(
            type_id=type_id,
            name=name,
            category="standard",
            length=length,
            width=width,
            height=height,
            weight=0.0,
            quantity=quantity_each,
            stackable=True,
            can_rotate=True,
            fragile=False,
            oriented=False,
            max_support_pressure=1e18,
        )

    # ---------------- 车型表 ----------------
    if "车型尺寸" not in wb.sheetnames:
        raise ValueError("Excel中未找到工作表：车型尺寸")
    ws_truck = wb["车型尺寸"]

    trucks: Dict[str, Truck] = {}

    # 典型封闭车型关键词
    closed_keywords = ["柜", "箱货", "集装箱"]
    exclude_keywords = ["高栏", "低栏", "栏板", "平板"]

    rows = list(ws_truck.iter_rows(values_only=True))
    for row in rows[1:]:
        if row is None:
            continue
        name = safe_str(row[0])
        if not name:
            continue

        if not any(k in name for k in closed_keywords):
            continue
        if any(k in name for k in exclude_keywords):
            continue

        dims = [parse_mm_from_text(v) for v in row[1:4]]
        if any(v is None for v in dims):
            # 尝试整行抓取前三个尺寸
            vals = [parse_mm_from_text(v) for v in row[1:]]
            vals = [v for v in vals if v is not None]
            if len(vals) < 3:
                continue
            dims = vals[:3]

        length, width, height = dims[0], dims[1], dims[2]

        # 费用取本行最后一个可解析数值
        cost = 0.0
        cost_candidates = [v for v in row[1:] if parse_mm_from_text(v) is not None]
        # 费用列通常不是尺寸单位，单独抓数值
        nums = []
        for v in row[1:]:
            s = safe_str(v)
            found = re.findall(r"\d+(?:\.\d+)?", s)
            if found:
                nums.extend(float(x) for x in found)
        if nums:
            cost = max(nums)

        trucks[name] = Truck(
            name=name,
            length=int(length),
            width=int(width),
            height=int(height),
            max_weight=1e18,   # 忽略重量约束
            cost=float(cost),
            top_clearance=0,
        )

    return products, trucks


# ============================================================
# 姿态 / 工具函数
# ============================================================

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

    if cargo.fragile:
        dims = [(l, w, h, "LWH"), (w, l, h, "WLH")]
    elif cargo.oriented:
        dims = [(l, w, h, "LWH")]

    out: List[Orientation] = []
    seen = set()
    for a, b, c, name in dims:
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            out.append(Orientation(len(out), key, name))
    return tuple(out)


def truck_score(truck: Truck, used_volume: int, used_weight: float = 0.0) -> Tuple[float, float, float]:
    sv = used_volume / max(1, truck.effective_volume)
    wv = 0.0
    fs = sv
    return sv, wv, fs


def expand_items(counts: Dict[str, int]) -> List[CargoItem]:
    items: List[CargoItem] = []
    for type_id in TYPE_ORDER:
        cargo = CARGO_TYPES[type_id]
        n = counts.get(type_id, 0)
        if n <= 0:
            continue
        oris = generate_orientations(cargo)
        for i in range(1, n + 1):
            items.append(
                CargoItem(
                    item_id=f"{type_id}_{i:03d}",
                    type_id=type_id,
                    category=cargo.category,
                    original_size=(cargo.length, cargo.width, cargo.height),
                    weight=0.0,
                    volume=cargo.volume,
                    stackable=True,
                    fragile=False,
                    oriented=False,
                    allowed_orientations=oris,
                )
            )
    return items


# ============================================================
# 问题1.1：Count-Layout Beam Heuristic
# ============================================================

def count_score(truck: Truck, counts: Dict[str, int]) -> float:
    total_volume = sum(CARGO_TYPES[k].volume * v for k, v in counts.items())
    if total_volume <= 0:
        return -1e18
    space_util = total_volume / truck.effective_volume

    # 轻微鼓励多样化，避免全选一种
    shares = []
    for k in TYPE_ORDER:
        v = counts.get(k, 0) * CARGO_TYPES[k].volume
        if v > 0:
            shares.append(v / total_volume)
    concentration = sum(p * p for p in shares) if shares else 1.0

    return 0.95 * space_util - 0.02 * concentration + 0.03 * min(1.0, total_volume / truck.effective_volume)


def best_grid_count(truck: Truck, cargo: CargoType) -> int:
    best = 0
    for ori in generate_orientations(cargo):
        l, w, h = ori.size
        nx = truck.length // l
        ny = truck.width // w
        nz = truck.effective_height // h
        best = max(best, nx * ny * nz)
    return best


def compute_upper_bounds(truck: Truck, remaining: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    bounds = {}
    for type_id, cargo in CARGO_TYPES.items():
        by_volume = truck.effective_volume // cargo.volume
        by_grid = best_grid_count(truck, cargo)
        qty = cargo.quantity if remaining is None else remaining.get(type_id, 0)
        bounds[type_id] = int(max(0, min(qty, by_volume, by_grid)))
    return bounds


def generate_count_candidates(
    truck: Truck,
    upper_bounds: Dict[str, int],
    trials: int = 600,
    keep: int = 40,
    seed: int = 2026,
) -> List[Dict[str, int]]:
    rng = random.Random(seed)
    seen = set()
    pool: List[Tuple[float, Dict[str, int]]] = []

    for trial in range(trials):
        counts = {t: 0 for t in TYPE_ORDER}
        used_volume = 0

        for _ in range(5000):
            feasible: List[Tuple[float, str]] = []
            for t in TYPE_ORDER:
                if counts[t] >= upper_bounds[t]:
                    continue
                c = CARGO_TYPES[t]
                if used_volume + c.volume > truck.effective_volume:
                    continue
                cand = counts.copy()
                cand[t] += 1
                score = count_score(truck, cand) + rng.uniform(-0.005, 0.005)
                feasible.append((score, t))

            if not feasible:
                break

            feasible.sort(reverse=True)
            rcl_size = min(4, len(feasible))
            chosen = rng.choice(feasible[:rcl_size])[1]
            counts[chosen] += 1
            used_volume += CARGO_TYPES[chosen].volume

        key = tuple(counts[t] for t in TYPE_ORDER)
        if key not in seen and sum(counts.values()) > 0:
            seen.add(key)
            pool.append((count_score(truck, counts), counts))

    pool.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in pool[:keep]]


def sort_spaces_dblf(spaces: Sequence[Space]) -> List[Space]:
    return sorted(spaces, key=lambda s: (s.z, s.y, s.x, s.volume))


def remove_contained_spaces(spaces: List[Space]) -> List[Space]:
    result = []
    for i, a in enumerate(spaces):
        contained = False
        for j, b in enumerate(spaces):
            if i == j:
                continue
            if (
                a.x >= b.x and a.y >= b.y and a.z >= b.z and
                a.x + a.length <= b.x + b.length and
                a.y + a.width <= b.y + b.width and
                a.z + a.height <= b.z + b.height and
                (a.x, a.y, a.z, a.length, a.width, a.height) !=
                (b.x, b.y, b.z, b.length, b.width, b.height)
            ):
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
    return sorted(items, key=lambda it: (-it.volume, it.item_id))


def can_place_in_space(item: CargoItem, ori: Orientation, space: Space) -> bool:
    l, w, h = ori.size
    return l <= space.length and w <= space.width and h <= space.height


def placement_gain(truck: Truck, state: LayoutState, item: CargoItem, ori: Orientation, space: Space) -> float:
    l, w, h = ori.size
    fill_ratio = (l * w * h) / max(1, space.length * space.width * space.height)
    low_z_bonus = 1.0 / (1.0 + space.z)
    tight_bonus = 1.0 / (1.0 + (space.length - l) + (space.width - w) + (space.height - h))
    used_volume = state.used_volume + item.volume
    sv, _, fs = truck_score(truck, used_volume)
    return fs + 0.10 * fill_ratio + 0.03 * low_z_bonus + 0.02 * tight_bonus + 0.02 * sv


def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    new_spaces: List[Space] = []

    if space.length > placed.length:
        new_spaces.append(
            Space(
                x=space.x + placed.length,
                y=space.y,
                z=space.z,
                length=space.length - placed.length,
                width=space.width,
                height=space.height,
            )
        )

    if space.width > placed.width:
        new_spaces.append(
            Space(
                x=space.x,
                y=space.y + placed.width,
                z=space.z,
                length=placed.length,
                width=space.width - placed.width,
                height=space.height,
            )
        )

    if space.height > placed.height:
        new_spaces.append(
            Space(
                x=space.x,
                y=space.y,
                z=space.z + placed.height,
                length=placed.length,
                width=placed.width,
                height=space.height - placed.height,
            )
        )
    return new_spaces


def apply_placement(truck: Truck, state: LayoutState, item_idx: int, ori: Orientation, space_idx: int) -> LayoutState:
    item = state.remaining[item_idx]
    space = state.spaces[space_idx]
    l, w, h = ori.size

    placed = PlacedCargo(
        item_id=item.item_id,
        type_id=item.type_id,
        category=item.category,
        x=space.x,
        y=space.y,
        z=space.z,
        length=l,
        width=w,
        height=h,
        weight=0.0,
        orientation_id=ori.orient_id,
        rotation=ori.rotation,
        truck_id=truck.name,
    )

    new_placed = list(state.placed)
    new_placed.append(placed)

    new_spaces = [s for idx, s in enumerate(state.spaces) if idx != space_idx]
    new_spaces.extend(split_space(space, placed))
    new_spaces = merge_spaces(new_spaces)
    new_spaces = sort_spaces_dblf(new_spaces)

    new_remaining = state.remaining[:item_idx] + state.remaining[item_idx + 1:]
    used_volume = state.used_volume + item.volume
    sv, _, fs = truck_score(truck, used_volume)
    packed_ratio = len(new_placed) / max(1, len(new_placed) + len(new_remaining))

    return LayoutState(
        spaces=new_spaces,
        placed=new_placed,
        remaining=new_remaining,
        used_weight=0.0,
        used_volume=used_volume,
        score=fs + 0.02 * packed_ratio + 0.01 * sv,
        packed_ratio=packed_ratio,
    )


def pack_with_beam_search(
    truck: Truck,
    items: List[CargoItem],
    beam_width: int = 6,
    candidate_items_each_step: int = 5,
    candidate_moves_each_state: int = 10,
    policy: int = 0,
) -> LayoutState:
    ordered = build_item_orders(items, policy)
    init = LayoutState(
        spaces=[Space(0, 0, 0, truck.length, truck.width, truck.effective_height)],
        placed=[],
        remaining=ordered,
        used_weight=0.0,
        used_volume=0,
        score=0.0,
        packed_ratio=0.0,
    )

    beam = [init]
    best = init

    while beam:
        next_beam = []
        expanded_any = False

        for state in beam:
            if state.score > best.score or state.used_volume > best.used_volume:
                best = state
            if not state.remaining or not state.spaces:
                next_beam.append(state)
                continue

            item_candidates = state.remaining[:min(candidate_items_each_step, len(state.remaining))]
            move_pool: List[Tuple[float, int, Orientation, int]] = []

            for item_idx, item in enumerate(item_candidates):
                for space_idx, space in enumerate(state.spaces[:min(15, len(state.spaces))]):
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
                child = apply_placement(truck, state, item_idx, ori, space_idx)
                next_beam.append(child)

        if not expanded_any:
            break

        next_beam.sort(key=lambda st: (st.score, st.used_volume, len(st.placed)), reverse=True)
        beam = next_beam[:beam_width]
        if beam and (beam[0].score > best.score or beam[0].used_volume > best.used_volume):
            best = beam[0]

    return best


def evaluate_candidate(truck: Truck, counts: Dict[str, int], beam_width: int) -> Tuple[LayoutState, Dict[str, object]]:
    items = expand_items(counts)
    best_state = None
    best_meta = {}

    for policy in range(4):
        state = pack_with_beam_search(
            truck=truck,
            items=items,
            beam_width=beam_width,
            candidate_items_each_step=5,
            candidate_moves_each_state=10,
            policy=policy,
        )
        if best_state is None or state.used_volume > best_state.used_volume:
            best_state = state
            best_meta = {"policy_index": policy}

    assert best_state is not None
    actual_counts = Counter(p.type_id for p in best_state.placed)
    sv, _, fs = truck_score(truck, best_state.used_volume)

    meta = {
        "truck": truck.name,
        "space_utilization": round(sv, 6),
        "fullness_score": round(fs, 6),
        "loaded_volume_mm3": int(best_state.used_volume),
        "target_counts": {k: v for k, v in counts.items() if v > 0},
        "actual_counts": dict(actual_counts),
        "placed_item_count": len(best_state.placed),
        **best_meta,
    }
    return best_state, meta


def solve_problem_11_single_truck(
    truck: Truck,
    remaining: Optional[Dict[str, int]] = None,
    topk: int = 16,
    beam_width: int = 6,
    trials: int = 600,
    seed: int = 2026,
) -> Tuple[LayoutState, Dict[str, object], Dict[str, int]]:
    upper_bounds = compute_upper_bounds(truck, remaining=remaining)
    candidates = generate_count_candidates(
        truck, upper_bounds, trials=trials, keep=max(topk * 3, 30), seed=seed
    )

    best_state = None
    best_meta = {}
    best_counts = {}

    for idx, counts in enumerate(candidates[:topk]):
        state, meta = evaluate_candidate(truck, counts, beam_width=beam_width)
        meta["candidate_index"] = idx

        if best_state is None:
            best_state, best_meta, best_counts = state, meta, counts
            continue

        old = best_state.used_volume
        new = state.used_volume
        if new > old:
            best_state, best_meta, best_counts = state, meta, counts

    assert best_state is not None
    return best_state, best_meta, upper_bounds


# ============================================================
# 问题1.2：重复调用问题1.1单车装载器
# ============================================================

def solve_problem_12_by_repeated_p11(
    truck: Truck,
    topk: int = 16,
    beam_width: int = 6,
    trials: int = 600,
    seed: int = 2026,
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    remaining = {k: CARGO_TYPES[k].quantity for k in TYPE_ORDER}
    vehicle_results: List[Dict[str, object]] = []
    vehicle_index = 1

    while sum(remaining.values()) > 0:
        state, meta, _ = solve_problem_11_single_truck(
            truck=truck,
            remaining=remaining,
            topk=topk,
            beam_width=beam_width,
            trials=trials,
            seed=seed + vehicle_index,
        )

        actual_counts = Counter(p.type_id for p in state.placed)
        loaded = sum(actual_counts.values())

        if loaded == 0:
            raise RuntimeError(f"{truck.name} 在第 {vehicle_index} 辆车未能装入任何货物。")

        for t in TYPE_ORDER:
            remaining[t] = max(0, remaining[t] - actual_counts.get(t, 0))

        vehicle_results.append({
            "vehicle_id": f"{truck.name}_{vehicle_index:03d}",
            "space_utilization": meta["space_utilization"],
            "used_volume_mm3": meta["loaded_volume_mm3"],
            "placed_item_count": meta["placed_item_count"],
            "actual_counts": dict(actual_counts),
            "placed": state.placed,
        })
        vehicle_index += 1

    avg_space = sum(v["space_utilization"] for v in vehicle_results) / max(1, len(vehicle_results))
    summary = {
        "truck_name": truck.name,
        "vehicle_count": len(vehicle_results),
        "avg_space_utilization": round(avg_space, 6),
        "total_cost_per_1000km": round(len(vehicle_results) * truck.cost, 2),
    }
    return vehicle_results, summary


# ============================================================
# 输出
# ============================================================

def write_csv(path: str, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_items_csv(path: str, placed: Sequence[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_id", "type_id", "category",
            "x", "y", "z",
            "length", "width", "height",
            "orientation_id", "rotation", "truck_id"
        ])
        for p in placed:
            writer.writerow([
                p.item_id, p.type_id, p.category,
                p.x, p.y, p.z,
                p.length, p.width, p.height,
                p.orientation_id, p.rotation, p.truck_id
            ])


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="附件2通用性检验：Count-Layout Beam Heuristic")
    parser.add_argument("--excel", type=str, default="附件2：验证数据集.xlsx", help="Excel路径")
    parser.add_argument("--outdir", type=str, default="附件2_通用性检验结果_beam", help="输出目录")
    parser.add_argument("--quantity-each", type=int, default=100, help="每类产品统一数量")
    parser.add_argument("--topk", type=int, default=16)
    parser.add_argument("--beam-width", type=int, default=6)
    parser.add_argument("--trials", type=int, default=600)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    global CARGO_TYPES, TRUCKS, TYPE_ORDER
    CARGO_TYPES, TRUCKS = load_attachment2(args.excel, quantity_each=args.quantity_each)
    TYPE_ORDER = list(CARGO_TYPES.keys())

    print(f"读取产品种类数: {len(CARGO_TYPES)}")
    print(f"读取典型封闭车型数: {len(TRUCKS)}")
    print("产品列表:", [c.name for c in CARGO_TYPES.values()])
    print("车型列表:", list(TRUCKS.keys()))

    # ---------------- 问题1.1 ----------------
    p11_rows = []
    for truck in TRUCKS.values():
        state, meta, _ = solve_problem_11_single_truck(
            truck=truck,
            remaining=None,
            topk=args.topk,
            beam_width=args.beam_width,
            trials=args.trials,
            seed=args.seed,
        )
        p11_rows.append({
            "truck_name": truck.name,
            "truck_length_mm": truck.length,
            "truck_width_mm": truck.width,
            "truck_height_mm": truck.height,
            "truck_volume_mm3": truck.effective_volume,
            "used_volume_mm3": meta["loaded_volume_mm3"],
            "space_utilization": meta["space_utilization"],
            "placed_item_count": meta["placed_item_count"],
            "actual_counts": meta["actual_counts"],
        })

    p11_rows.sort(key=lambda x: x["space_utilization"], reverse=True)
    write_csv(os.path.join(args.outdir, "problem11_single_truck_fullness_beam.csv"), p11_rows)

    print("\n问题1.1结果（前3名车型）:")
    for r in p11_rows[:3]:
        print(r)

    # ---------------- 问题1.2 ----------------
    p12_rows = []
    details_dir = os.path.join(args.outdir, "problem12_vehicle_details_beam")
    for truck in TRUCKS.values():
        vehicle_results, summary = solve_problem_12_by_repeated_p11(
            truck=truck,
            topk=args.topk,
            beam_width=args.beam_width,
            trials=args.trials,
            seed=args.seed,
        )
        p12_rows.append(summary)

        truck_dir = os.path.join(details_dir, truck.name)
        for vr in vehicle_results:
            write_items_csv(os.path.join(truck_dir, f"{vr['vehicle_id']}_装箱明细.csv"), vr["placed"])

    p12_rows.sort(key=lambda x: (x["vehicle_count"], x["total_cost_per_1000km"]))
    write_csv(os.path.join(args.outdir, "problem12_min_vehicle_count_beam.csv"), p12_rows)

    print("\n问题1.2结果（前3名车型）:")
    for r in p12_rows[:3]:
        print(r)

    print("\n输出目录:", os.path.abspath(args.outdir))


if __name__ == "__main__":
    main()