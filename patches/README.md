# Patch Taxonomy

The `patches/` tree is intentionally split by purpose:

- `curated/`
  - Novel, orthogonal, repo-level examples worth keeping readable and maintained.
- `studies/`
  - Families of related musical investigations. Useful, but not all first-class exemplars.
- `corpus/`
  - Larger generated or pipeline-driven patch sets such as `rings-to-clouds/`.
- `archive/`
  - Debugging scripts, superseded variants, and older ideation that we still want to keep.

Recommended starting points:

- `curated/agentrack_demo.py`
- `curated/tonnetz_demo.py`
- `curated/dub_cm_double.py`
- `curated/plaits_stabs.py`
- `curated/subzero.py`
- `curated/mutation.py`

The goal of this split is to keep the maintained example surface small, so future
API migrations do not have to drag the full historical patch archive with them.
