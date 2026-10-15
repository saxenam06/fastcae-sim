"""The final workflow, end to end, from the contract to a judged design (LOP-31, LOP-33).

- `recipe`: the one versioned recipe of agreed settings (`recipes/final.json`) and its fingerprint.
- `flow`: one design's stages in order (the layout, the optimisation, the drawing, the oil-tight
  gate, FE beside castability, the grade, the Designs tab's records), its gates and its record.
- `grade`: every graded line of the contract against a design's FE result.
- `run`: the workflow run when the contract or the recipe changed, its state kept.

The heavy stages (the optimiser, the drawing, FE, castability, the pictures) are reached through
`flow.Engines`. Until each is ported here with a check that it gives the prototype's result, its
engine is the prototype's (`prototypes/first_loop/engines.py`): nothing here imports a prototype.
"""
