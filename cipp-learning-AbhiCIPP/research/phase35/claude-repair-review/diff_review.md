# Diff review: repair commit db30ceadbe18cf90e01f6d54dee0203f342b24a8

Parent: `4e712a4b7dea033b9191680a4b4e3577d93ca304` (the commit reviewed
previously). Base: `4764f1758a7399439df2242dfa60819501fc2333`.

## Bundle/checksum/lineage

- `sha256sum` of `phase35-conformance-repair-db30ceadbe18cf90e01f6d54dee0203f342b24a8.bundle`
  matches both the `.sha256` file and the value given in the task exactly:
  `1b330b7402913a5ed92402fba41f1105d687ca1ed080985bef470903f8c3587e`.
- `git bundle verify`: OK, ref `refs/heads/phase35-dendrite-classes-codex1` at
  `db30ceadbe18cf90e01f6d54dee0203f342b24a8`, complete history.
- `git log --pretty=%P -n1 db30cead...` returns exactly one parent,
  `4e712a4b...` -- no merge commit. Cloned fresh into a new disposable
  checkout, independent of the one used for the previous review and of
  Codex 1's own `repo/` directory.

## File-level change summary (`git diff --stat` against the parent)

```
CLAUDE_HANDOFF.md                    | 25 +++++++++
backend/simulation.py                | 65 ++++++++++++++++++----
test_phase35_conformance_repair.py   | 64 +++++++++++++++++++++
3 files changed, 144 insertions(+), 10 deletions(-)
```

`git diff --numstat` confirms no binary rows. `snn/dendrite.py` and
`snn/__init__.py` are untouched by this commit -- the repair is scoped
entirely to `backend/simulation.py`'s presentation-boundary handling, plus a
new committed test file (this time part of the commit, unlike the previous
round's Gate A/B files which lived outside git).

## The fix itself

The entire offending block from `4e712a4` is deleted (confirmed by literal
`-` lines in the diff):

```python
if self.prediction_column_enabled and hasattr(self, 'l2e_to_pcol_queue'):
    self.l2e_to_pcol_queue = deque(...)
    self.s_to_pcol_queue = deque(...)
    for pc in self.pcol:
        pc.clear_compartments()
```

Nothing replaces it at the `_start_presentation` call site -- the physical
delay queues (`l2e_to_pcol_queue`, `s_to_pcol_queue`) and the per-compartment
state are simply left alone across a pattern/probe switch now.

In its place, three additions:

1. **`self.pcol_delivery_metadata_queue`** (new `__init__`/build-time state,
   `backend/simulation.py` ~line 1728): a deque of the same length as the
   physical delay queues (`prediction_feedback_delay` slots), each slot
   holding a list of metadata records. Appended to in lockstep with the
   physical queues at the scheduling site (~line 2791, right where
   `l2e_to_pcol_queue.append`/`s_to_pcol_queue.append` already happen), and
   popped in lockstep at the delivery site (~line 2649, right where
   `l2e_to_pcol_queue.popleft`/`s_to_pcol_queue.popleft` already happen).
   Each scheduled record carries `source`, `target`, `target_compartment`,
   `scheduled_step`, `arrival_step`, `origin_pattern` -- everything the
   review's requirement list asks to survive a switch.
2. **`_prediction_column_origin_class(self, records, pixel_index)`**
   (~line 1740): a pure classifier -- `current-correct` /
   `stale-same-pixel` / `stale-wrong-pixel` / `mixed` -- computed from the
   metadata records and the engine's `current_pattern`/`PATTERNS`/`PROBES`
   lookup. Called once per PC per delivery step (~line 2660) and the result
   is only ever written into `delivered_records`, which feeds
   `self._prediction_column_last_deliveries` and, from there,
   `dynamic_state()['prediction_column']['last_deliveries']`. It is never
   read by `resolve_coincidence`, `_apply_prediction_column_learning`, or
   any other decision path -- confirmed by grep, this identifier does not
   appear anywhere outside its definition and the telemetry-assembly line.
3. **`dynamic_state()` additions** (~line 3540): `pending_deliveries` (a
   flattened dump of everything still sitting in the metadata queue,
   unconsumed) and `last_deliveries` (this step's classified arrivals).
   Both are read-only dict copies (`dict(record)`), not references into
   live state.

## Cleanliness

No cache files, `.venv` artifacts, generated reports, or unrelated files
appear in the diff. Exactly the three claimed files changed, all real
source/doc/test content.
