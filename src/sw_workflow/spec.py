"""Strict millimetre inputs and independent analytic acceptance targets."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any


DEFAULTS = {
    "plate": {"width": 100.0, "height": 70.0, "thickness": 8.0,
              "hole_diameter": 6.0, "margin_x": 15.0, "margin_y": 15.0},
    "bracket": {"width": 60.0, "depth": 40.0, "height": 35.0, "thickness": 5.0},
    "bushing": {"outer_diameter": 30.0, "inner_diameter": 16.0, "length": 25.0},
}


class SpecError(ValueError):
    pass


@dataclass(frozen=True)
class PartSpec:
    template: str
    parameters: dict[str, float]
    drawing: bool = False

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "PartSpec":
        if not isinstance(data, dict):
            raise SpecError("The specification must be a JSON object")
        extra = set(data) - {"schema_version", "units", "template", "parameters", "drawing"}
        if extra:
            raise SpecError(f"Unknown fields: {sorted(extra)}")
        if type(data.get("schema_version", 1)) is not int or data.get("schema_version", 1) != 1:
            raise SpecError("Only schema_version 1 is supported")
        if data.get("units", "mm") != "mm":
            raise SpecError("Input units must be mm")
        kind = data.get("template")
        if not isinstance(kind, str) or kind not in DEFAULTS:
            raise SpecError(f"template must be one of {sorted(DEFAULTS)}")
        raw = data.get("parameters", {})
        if not isinstance(raw, dict) or set(raw) - set(DEFAULTS[kind]):
            raise SpecError("Unknown or invalid template parameters")
        values = dict(DEFAULTS[kind])
        for name, value in raw.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SpecError(f"{name} must be a number")
            if not math.isfinite(value) or not 0 < value <= 10000:
                raise SpecError(f"{name} must be finite and in (0, 10000] mm")
            values[name] = float(value)
        drawing = data.get("drawing", False)
        if not isinstance(drawing, bool):
            raise SpecError("drawing must be boolean")
        if kind == "plate":
            p = values
            r = p["hole_diameter"] / 2
            if not r < p["margin_x"] < p["width"] / 2 - r:
                raise SpecError("Four holes must fit inside the plate and remain separated in X")
            if not r < p["margin_y"] < p["height"] / 2 - r:
                raise SpecError("Four holes must fit inside the plate and remain separated in Y")
        elif kind == "bracket":
            if values["thickness"] >= min(values["height"], values["depth"]):
                raise SpecError("Bracket thickness must be smaller than height and depth")
        elif values["inner_diameter"] >= values["outer_diameter"]:
            raise SpecError("Bushing inner diameter must be smaller than outer diameter")
        return cls(kind, values, drawing)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "units": "mm", "template": self.template,
                "parameters": dict(self.parameters), "drawing": self.drawing}

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(payload.encode()).hexdigest()

    @property
    def volume_mm3(self) -> float:
        p = self.parameters
        if self.template == "plate":
            return (p["width"] * p["height"] - math.pi * p["hole_diameter"] ** 2) * p["thickness"]
        if self.template == "bracket":
            return p["width"] * p["thickness"] * (p["depth"] + p["height"] - p["thickness"])
        return math.pi / 4 * (p["outer_diameter"] ** 2 - p["inner_diameter"] ** 2) * p["length"]

    @property
    def extents_mm(self) -> list[float]:
        p = self.parameters
        if self.template == "plate":
            return [p["width"], p["height"], p["thickness"]]
        if self.template == "bracket":
            return [p["width"], p["height"], p["depth"]]
        return [p["outer_diameter"], p["outer_diameter"], p["length"]]

    def changed(self, parameters: dict[str, float]) -> "PartSpec":
        if not isinstance(parameters, dict):
            raise SpecError('Changed parameters must be a JSON object')
        data = self.to_dict()
        data["parameters"].update(parameters)
        return self.parse(data)
