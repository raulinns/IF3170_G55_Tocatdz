from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..domain.model import Dimensions, Package, Problem, Truck


class DimensionsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    width: int = Field(gt=0)
    length: int = Field(gt=0)
    height: int = Field(gt=0)


class TruckInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1)
    dimensions: DimensionsInput
    max_capacity: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("id")
    @classmethod
    def nonblank_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be blank")
        return value.strip()


class PackageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1)
    dimensions: DimensionsInput
    value: float = Field(ge=0, allow_inf_nan=False)
    weight: float = Field(ge=0, allow_inf_nan=False)
    is_fragile: bool
    eta: int = Field(ge=0)

    @field_validator("id")
    @classmethod
    def nonblank_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be blank")
        return value.strip()


class ProblemInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1)
    trucks: list[TruckInput] = Field(min_length=1)
    packages: list[PackageInput] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def unique_ids(self) -> ProblemInput:
        for label, items in (("truck", self.trucks), ("package", self.packages)):
            ids = [item.id for item in items]
            if len(set(ids)) != len(ids):
                raise ValueError(f"duplicate {label} id")
        return self


def parse_problem_data(data: Any) -> Problem:
    source = ProblemInput.model_validate(data)
    return Problem(
        source.name,
        tuple(
            Truck(
                truck.id,
                Dimensions(**truck.dimensions.model_dump()),
                truck.max_capacity,
            )
            for truck in source.trucks
        ),
        tuple(
            Package(
                package.id,
                Dimensions(**package.dimensions.model_dump()),
                package.value,
                package.weight,
                package.is_fragile,
                package.eta,
            )
            for package in source.packages
        ),
    )


def parse_problem_json(raw: str | bytes) -> Problem:
    return parse_problem_data(json.loads(raw))


def problem_to_data(problem: Problem) -> dict[str, Any]:
    return {
        "name": problem.name,
        "trucks": [
            {
                "id": truck.id,
                "dimensions": {
                    "width": truck.dimensions.width,
                    "length": truck.dimensions.length,
                    "height": truck.dimensions.height,
                },
                "max_capacity": truck.max_capacity,
            }
            for truck in problem.trucks
        ],
        "packages": [
            {
                "id": package.id,
                "dimensions": {
                    "width": package.dimensions.width,
                    "length": package.dimensions.length,
                    "height": package.dimensions.height,
                },
                "value": package.value,
                "weight": package.weight,
                "is_fragile": package.is_fragile,
                "eta": package.eta,
            }
            for package in problem.packages
        ],
    }


def example_problem_data() -> dict[str, Any]:
    return {
        "name": "Demo pengiriman",
        "trucks": [
            {
                "id": "T1",
                "dimensions": {"width": 8, "length": 6, "height": 5},
                "max_capacity": 35,
            },
            {
                "id": "T2",
                "dimensions": {"width": 6, "length": 5, "height": 4},
                "max_capacity": 22,
            },
        ],
        "packages": [
            {
                "id": "P1",
                "dimensions": {"width": 3, "length": 2, "height": 2},
                "value": 18,
                "weight": 8,
                "is_fragile": False,
                "eta": 2,
            },
            {
                "id": "P2",
                "dimensions": {"width": 2, "length": 2, "height": 2},
                "value": 15,
                "weight": 5,
                "is_fragile": True,
                "eta": 1,
            },
            {
                "id": "P3",
                "dimensions": {"width": 4, "length": 2, "height": 1},
                "value": 12,
                "weight": 6,
                "is_fragile": False,
                "eta": 3,
            },
            {
                "id": "P4",
                "dimensions": {"width": 2, "length": 3, "height": 2},
                "value": 20,
                "weight": 9,
                "is_fragile": False,
                "eta": 0,
            },
        ],
    }
