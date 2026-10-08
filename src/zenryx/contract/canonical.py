"""Canonical serialisation and the contract's hash (spec §6).

The hash is taken over the contract's content, not its text: keys sorted, every quantity in its
canonical unit, conversion noise rounded off (12 significant digits), the hash itself left out.
The same content written another way - keys reordered, 366 N·m written as 366000 N·mm - gives the
same hash; any changed value gives another.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from zenryx.contract.model import HousingDesignSpec
from zenryx.contract.units import Quantity, Vector

_SIGNIFICANT = 12


def _number(x: float) -> float:
    value = float(f"{x:.{_SIGNIFICANT}g}")
    return 0.0 if value == 0 else value


def _canonical(obj: Any) -> Any:
    if isinstance(obj, Quantity):
        value, unit = obj.to_canonical()
        return {"unit": unit, "value": _number(value)}
    if isinstance(obj, Vector):
        values, unit = obj.to_canonical()
        return {"unit": unit, "values": [_number(v) for v in values]}
    if isinstance(obj, BaseModel):
        return {
            name: _canonical(getattr(obj, name))
            for name in type(obj).model_fields
            if name != "frozen_hash"
        }
    if isinstance(obj, (list, tuple)):
        return [_canonical(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): _canonical(v) for k, v in obj.items()}
    if isinstance(obj, bool) or obj is None or isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        return _number(obj)
    raise TypeError(f"cannot serialise {type(obj).__name__} canonically")


def canonical_json(spec: HousingDesignSpec) -> str:
    """The contract's content as one canonical JSON string (the hash leaves itself out)."""
    return json.dumps(
        _canonical(spec),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def spec_hash(spec: HousingDesignSpec) -> str:
    digest = hashlib.sha256(canonical_json(spec).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def freeze(spec: HousingDesignSpec) -> HousingDesignSpec:
    """A copy at stage 'frozen' carrying its own hash. Validate the contract before freezing."""
    staged = spec.model_copy(update={"stage": "frozen", "frozen_hash": None})
    return staged.model_copy(update={"frozen_hash": spec_hash(staged)})
