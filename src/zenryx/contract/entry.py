"""Entries: every value in a contract with where it came from, who may change it, and its kind.

Provenance kinds (spec §3):
    published   from a paper or a maker's data: needs a citation (document, table or page)
    standard    from a standard or guideline: needs a citation (standard and clause)
    measured    measured on an existing part: needs a citation (the part and the face)
    derived     computed by a versioned tool: needs the tool, its version and the input hash
    assumption  no source: points to its entry in the contract's assumptions list
    engineer    set by a person: needs who and when

A derived value is written only by its tool. A person or an agent may ask for it to be derived
again from a changed input it has authority over, but never writes the value itself.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from zenryx.contract.units import Quantity, Vector

ProvenanceKind = Literal["published", "standard", "measured", "derived", "assumption", "engineer"]
Authority = Literal["engineer_locked", "agent_bounded", "agent_free"]
Kind = Literal["hard", "soft", "derived"]

_NEEDS: dict[str, tuple[str, ...]] = {
    "published": ("citation",),
    "standard": ("citation",),
    "measured": ("citation",),
    "derived": ("tool", "tool_version", "input_hash"),
    "assumption": ("assumption_id",),
    "engineer": ("who", "when"),
}


class Provenance(BaseModel):
    """Where a value came from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ProvenanceKind
    citation: str | None = None
    tool: str | None = None
    tool_version: str | None = None
    input_hash: str | None = None
    assumption_id: str | None = None
    who: str | None = None
    when: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _complete(self) -> Provenance:
        missing = [name for name in _NEEDS[self.kind] if not getattr(self, name)]
        if missing:
            raise ValueError(f"provenance.{self.kind} needs {', '.join(missing)}")
        return self


Value = Quantity | Vector | str | int | bool | None


class Entry(BaseModel):
    """One value of the contract, with its provenance, authority and kind."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: Value
    provenance: Provenance
    authority: Authority
    kind: Kind
    bounds: tuple[Quantity, Quantity] | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Entry:
        derived_kind = self.kind == "derived"
        derived_source = self.provenance.kind == "derived"
        if derived_kind != derived_source:
            raise ValueError(
                "kind 'derived' and provenance 'derived' go together: a derived value is "
                "written only by its tool"
            )
        if self.authority == "agent_bounded":
            if self.bounds is None:
                raise ValueError("authority 'agent_bounded' needs bounds")
            if isinstance(self.value, Quantity):
                low, high = (b.to_canonical() for b in self.bounds)
                value = self.value.to_canonical()
                if not (low[1] == value[1] == high[1]):
                    raise ValueError("bounds must be in the same dimension as the value")
                if not low[0] <= value[0] <= high[0]:
                    raise ValueError("the value lies outside its bounds")
        return self

    def stamped(self) -> bool:
        """A derived value carrying its tool, version and input hash."""
        p = self.provenance
        return p.kind == "derived" and bool(p.tool and p.tool_version and p.input_hash)
