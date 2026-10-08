# Helical mesh forces with profile shift: a PROTOTYPE

**What this is.** A sizing script for the load tool's plan ([§4](../../docs/features/gearbox/2026-10-08-load-tool-plan.md)). It works out Ivanov 2018's two meshes at 150 N·m in two ways:
- by the simple formulas at the reference circle (Shigley, Łódź, Ivanov §2.2);
- by the base-circle form, which holds for profile-shifted gears.

**What it is not.** It is not the load tool; GBX-1 builds that, with its checks. Nothing in `src/` imports it, and it writes nothing.

## Run it

```
uv run python prototypes/helical_forces/forces.py
```

## What it gave (8 October, 21:00)

The base-circle form against the simple one:

| Mesh | Ft | Fr | Fa |
|---|---|---|---|
| Stage 1 (150 N·m on the pinion) | −2.1 % | +13.8 % | 0 |
| Stage 2 (306 N·m on the pinion) | −1.6 % | +10.4 % | 0 |

The torque check holds exactly: Ft times the working pitch radius gives back the torque.
