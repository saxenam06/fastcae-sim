# The load tool for helical gears (GBX-1 to GBX-4): equations, sources and checks

**Date.** 8 October 2026, 21:01. Asked for by the engineer at 20:59. Each step takes its equations from the source that gives them best and still holds for helical gears. It starts from what every source agrees on, and each step states its confidence.

**Status.** A plan, for the engineer's review. Nothing is built.

**The sources** (read in [the round-2 research note](../../research/2026-10-08-housing-sources-round-2.md)):
- Shigley Ch. 18;
- the Łódź handbook (Maciejczyk and Zdziennicki 2011);
- Ivanov 2018 §2.2;
- JTEKT eq. 5-29, via the textbook example in fastcae's [gearbox-housing engineering report](../../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md) §6.2;
- the involute geometry already in `zenryx.contract.involute`.

---

## 1. The finding that shapes the plan: Ivanov's gears are profile-shifted

The textbook formulas (Shigley, Łódź, Ivanov §2.2) assume standard gears: Ft = 2T/d, Fr = Ft·tan αn / cos β, Fa = Ft·tan β. Ivanov's gears carry a profile shift of about +1.0 per stage. That moves the operating pressure angle from 20.6° to 23.6° (stage 1) and 22.8° (stage 2).

Worked with our own involute code at 150 N·m (the prototype `prototypes/helical_forces/forces.py`):

| Mesh | Simple formulas (N) | Shift taken into account (N) | Change |
|---|---|---|---|
| Stage 1 | Ft 5,617.5 · Fr 2,107.6 · Fa 3,243.2 | Ft 5,499.4 · **Fr 2,398.7** · Fa 3,243.2 | Ft −2.1 %, **Fr +13.8 %**, Fa 0 |
| Stage 2 (306 N·m on its pinion) | Ft 11,240.9 · Fr 4,217.4 · Fa 6,489.9 | Ft 11,066.0 · **Fr 4,657.1** · Fa 6,489.9 | Ft −1.6 %, **Fr +10.4 %**, Fa 0 |

So the tool uses the form that holds for shifted gears, and the simple form becomes its check at zero shift.

**Confirmed by an independent source** (searched, 21:05). [drivetrainhub, *notebooks-gears*, "Chapter 1 - Force Analysis"](https://nbviewer.org/format/script/github/drivetrainhub/notebooks-gears/blob/master/strength/Chapter%201%20-%20Force%20Analysis.ipynb), whose figures are credited to Maitra, *Handbook of Gear Design*, takes the forces at the operating pitch circle:
- "Ft = 2T/dp", with the working pitch diameter dw;
- "Fr = Ft tan αtw", with the working transverse pressure angle.

These are exactly this plan's Ft and Fr, so the +10-14 % radial stands.

For the axial force it uses "Fa = Ft tan β" with the reference helix angle. That is about 2 % below the exact value. Taken at the working circle, the helix angle is βw (tan βw = tan β · dw/d), and Ft·tan βw = Fbt·tan βb, this plan's form. The plan keeps the exact form, and the check records the 2 % as a known difference between the two conventions.

## 2. The chain, step by step

| Step | Equations | Best source, and why | Also in | Confidence |
|---|---|---|---|---|
| **1. Gear geometry** | αt = atan(tan αn / cos β); inv αwt = inv αt + 2(x₁+x₂)·tan αn/(z₁+z₂); βb = atan(tan β·cos αt); d = z·mn/cos β; db = d·cos αt; rw = rb/cos αwt | The involute definitions (DIN 3960, ISO 21771), as `zenryx.contract.involute` already uses them. They are verified against two published gear sets: 56.94 against 57 and 96.99 against 97 mm (Kim 2024); 82.92 against 83 and 125.04 against 125 mm (Ivanov) | every gear text | **High**: exact geometry |
| **2. Mesh forces** | Fbt = 2T/db; **Ft = Fbt·cos αwt; Fr = Fbt·sin αwt; Fa = Fbt·tan βb**. At zero shift this is exactly the textbook form | The base-circle form: the torque is carried along the line of action at the base radius, and every source agrees on that. Shigley gives the textbook form it reduces to | Shigley Ch. 13; Ivanov §2.2; Łódź Ch. 3 (spur) | **High**. The one judgement is to take the working rather than the reference circle (§4) |
| **3. Directions** | The driver's and the driven gear's forces are equal and opposite; Ft along the motion of the driven gear; Fa from the hand and the sense of the torque; per case, drive, regeneration (torque reversed) and reverse (rotation and torque reversed) | Shigley Ch. 13 (the components on driver and driven); the hands from Ivanov (pinions left, gears right) | Ivanov §2.2 | **High**, once fixed by the checks in §3 |
| **4. Spacing along each shaft** | Gear and bearing positions from the face widths, the bearing widths and the gaps between them | Shigley §18-4, the case study's layout practice, with dimensions; Łódź Ch. 3. The face widths are Ivanov's and the bearing widths ISO 15's | - | **Medium**: the gaps are assumptions, listed |
| **5. Bearing reactions** | Each shaft is a beam on two supports, with the gear forces at their pitch points and the axial force's moment Fa·rw. Then statics in two planes | **JTEKT eq. 5-29**: it carries the helical axial moment, and our textbook example already uses it. Shigley's statics hold for the spur parts | Shigley Ch. 3 and 7; Łódź Ch. 3 | **High** for statics |
| **6. Who takes the axial force** | The locating bearing of each shaft: the input's ball bearing (its cylindrical roller floats); the output's ball pair by its arrangement. The intermediate tapered pair: each bearing's **induced axial force is 0.5·Fr/Y** (Y from the bearing's table). The bearing with the smaller induced force takes the external thrust plus the other's induced force | [Machine Design, Eitel 2005, "Adjusting tapered bearings"](https://www.machinedesign.com/bearings/adjusting-tapered-bearings) for the induced force (searched 21:05; NSK's catalogue says the same); the bearing makers' pair method for the sharing. The arrangement is A8 (Hofstetter's pattern) | Shigley Ch. 11 | **High** for the formula; **medium** for the arrangement assumed |
| **7. Bearing sizes** | L10 = (C/P)^p·10⁶ revolutions, P = X·Fr + Y·Fa; p = 3 for ball and 10/3 for roller bearings. The life is 944 h (A4) | The catalogue method. ISO 281 is the standard, but it is paid, so it never enters the repo. Its formula is public through Shigley Ch. 11 and Łódź Ch. 4-5, which works an example | Shigley Ch. 18 (its bearing selection) | **High** for the method; **medium** for the duty (§4) |
| **8. Mesh orders** | teeth × shaft speed / 60 | exact; built (`zenryx.contract.train`) | all | **High** |
| **9. Into the contract** | Interfaces: the seats' centre, axis, diameter (the bearing's OD), width and stock. Physics: the load cases with their seat forces, and the mesh orders. Each stamped with the tool, its version and the input hash | the contract's rules: derived physics is computed, never typed | - | the validator accepts it as derived, then it freezes |

## 3. How it is checked: a ladder, cheapest first

1. **Invariants, on every run:**
   - at each mesh, Ft·rw equals the torque. It holds exactly for Ivanov: 150.000 and 306.000 N·m;
   - each mesh's two forces are equal and opposite;
   - each shaft is in equilibrium;
   - the housing's seat forces sum to zero, and their moment balances the input and output torques, (i − 1)·T, as the prototype's statics did on 8 October.
2. **Reduction:** at zero shift the general form equals the textbook form (Shigley, Ivanov §2.2) to rounding.
3. **Answer keys, worked examples with their numbers:**
   - **Shigley Ch. 18:** torques of 60, 270 and 1,215 lbf·ft; transmitted loads of 540 and 2,431 lbf; the intermediate shaft's reactions (spur).
   - **Łódź Ch. 3:** Wt 9.556 kN and Wr 3.478 kN, the belt's 3.42 kN, the bearing loads (spur, with a belt).
   - **The textbook example** (helical 25°, JTEKT eq. 5-29): seat loads of (5000, 842.2, 0) and (5000, 3173.8, 4663.1) N. It is already a contract in `checks/data/contracts/`.
   - **Bearing life:** Łódź Ch. 5's worked selection, and Shigley Ch. 18's.
4. **An independent method:** an FE beam model of one shaft on its two supports gives the same reactions.
5. **Fault injection:** a flipped hand, a wrong sign of torque, a missing axial moment or two swapped seats must each change a result the checks catch.
6. **Optional:** KISSsoft on Ivanov's two stages, if the engineer has a licence. It would settle the convention of §4 independently.

## 3a. Where the plan searched (the engineer, 21:02: "where you are not confident, search the web, but in a controlled way, only for that information")

| Point of low confidence | Searched for | Found | Now |
|---|---|---|---|
| The force convention for profile-shifted gears | The forces at the working pitch circle and pressure angle | drivetrainhub's force analysis: Ft = 2T/dw, Fr = Ft·tan αtw | **High** (§1) |
| How a tapered pair shares the axial force | The induced axial force of a tapered bearing | 0.5·Fr/Y (Machine Design 2005; NSK) | **High** for the formula |
| Still to search, when its PBI starts | the gaps along a shaft (GBX-2); an EV reducer's load spectrum for bearing life (GBX-3) | - | medium, listed as assumptions |

## 4. Choices for the engineer

1. **The convention for shifted gears:** the base-circle form, proposed. It is the physics, it equals the textbooks at zero shift, and an independent source takes the forces the same way (§1). For Ivanov it puts the radial forces 10-14 % above the simple formulas.
2. **The duty for bearing life:** the drive case (150 N·m at 6,000 rpm) held for all 944 h, as the conservative default, unless a load spectrum is given.
3. **The spacing along the shafts:** the gaps, and which bearing locates axially, follow the A8 pattern and are listed as assumptions.

## 5. The PBIs

| PBI | What | Done when |
|---|---|---|
| GBX-1 | Mesh geometry and forces for helical, shifted gears, with their directions in each load case | The invariants hold, the forms agree at zero shift, and Shigley's and Łódź's force numbers are reproduced |
| GBX-2 | Spacing along the shafts and the bearing reactions, axial moments included | The textbook example's seat loads and Shigley's and Łódź's reactions are reproduced; the FE beam agrees; the faults are caught |
| GBX-3 | Bearing sizes by L10 life | Łódź Ch. 5's and Shigley's worked selections are reproduced |
| GBX-4 | Derive the Ivanov contract: seats and load cases stamped, the validator accepting it as derived, then frozen | The contract freezes, and the UI's planned calculations show their results |
