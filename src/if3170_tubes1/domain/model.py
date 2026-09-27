from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from types import MappingProxyType
from typing import Mapping


class Orientation(IntEnum):
    WLH = 0
    WHL = 1
    LWH = 2
    LHW = 3
    HWL = 4
    HLW = 5


class ObjectiveKind(StrEnum):
    TOTAL_VALUE = "total_value"
    VALUE_PER_URGENCY = "value_per_urgency"


@dataclass(frozen=True, slots=True)
class Dimensions:
    width: int
    length: int
    height: int

    def oriented(self, orientation: Orientation) -> Dimensions:
        w, l, h = self.width, self.length, self.height
        values = (
            (w, l, h),
            (w, h, l),
            (l, w, h),
            (l, h, w),
            (h, w, l),
            (h, l, w),
        )
        return Dimensions(*values[orientation])


@dataclass(frozen=True, slots=True)
class Position:
    x: int
    y: int
    z: int


@dataclass(frozen=True, slots=True)
class Package:
    id: str
    dimensions: Dimensions
    value: float
    weight: float
    is_fragile: bool
    eta: int


@dataclass(frozen=True, slots=True)
class Truck:
    id: str
    dimensions: Dimensions
    max_capacity: float


@dataclass(frozen=True, slots=True)
class Problem:
    name: str
    trucks: tuple[Truck, ...]
    packages: tuple[Package, ...]
    _trucks_by_id: Mapping[str, Truck] = field(init=False, repr=False, compare=False)
    _packages_by_id: Mapping[str, Package] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        trucks = tuple(sorted(self.trucks, key=lambda truck: truck.id))
        packages = tuple(sorted(self.packages, key=lambda package: package.id))
        trucks_by_id = {truck.id: truck for truck in trucks}
        packages_by_id = {package.id: package for package in packages}
        if len(trucks_by_id) != len(trucks):
            raise ValueError("truck ids must be unique")
        if len(packages_by_id) != len(packages):
            raise ValueError("package ids must be unique")
        object.__setattr__(self, "trucks", trucks)
        object.__setattr__(self, "packages", packages)
        object.__setattr__(self, "_trucks_by_id", MappingProxyType(trucks_by_id))
        object.__setattr__(self, "_packages_by_id", MappingProxyType(packages_by_id))

    def truck(self, truck_id: str) -> Truck:
        return self._trucks_by_id[truck_id]

    def package(self, package_id: str) -> Package:
        return self._packages_by_id[package_id]


@dataclass(frozen=True, slots=True)
class Placement:
    package_id: str
    truck_id: str | None = None
    position: Position | None = None
    orientation: Orientation = Orientation.WLH

    @property
    def is_outside(self) -> bool:
        return self.truck_id is None


@dataclass(frozen=True, slots=True)
class State:
    placements: tuple[Placement, ...]
    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "placements",
            tuple(sorted(self.placements, key=lambda placement: placement.package_id)),
        )


    @classmethod
    def all_outside(cls, problem: Problem) -> State:
        return cls(tuple(Placement(package.id) for package in problem.packages))

    def placement(self, package_id: str) -> Placement:
        try:
            return next(item for item in self.placements if item.package_id == package_id)
        except StopIteration as error:
            raise KeyError(package_id) from error

    def replace(self, replacement: Placement) -> State:
        if not any(item.package_id == replacement.package_id for item in self.placements):
            raise KeyError(replacement.package_id)
        return State(
            tuple(
                replacement if item.package_id == replacement.package_id else item
                for item in self.placements
            )
        )
