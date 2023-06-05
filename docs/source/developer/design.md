# Design

This page describes details specific to HIVE for new developers interacting with the library.

## table of contents

- **[determinism](#determinism)**: details related to keeping HIVE runs deterministic

### determinism

#### immutables.Map does not iterate based on insertion order

Most of the HIVE state is stored in hash maps. A [3rd party library](https://github.com/MagicStack/immutables) provides an immutable hash map via the Hash Array Mapped Trie (HAMT) data structure. While it is, for the most part, a drop-in replacement for a python Dict, it has one caveat, which is that insertion order is not guaranteed. This has determinism implications for HIVE. For this reason, any iteration of HAMT data structures must first be _sorted_. This is the default behavior for accessing the entity collections on a `SimulationState`, that they are first sorted by `EntityId`, such as `sim.get_vehicles()`.

Deeper within HIVE, whenever the HAMT data structure is interacted with, we must take care. There are two possible situations:
  1. the iteration order is irrelevant (for example, when iterating on a collection in order to write reports, or when updating a collection)
    - here, use of `.items()` iteration is acceptable
  2. the iteration order is sorted (exclusively when retrieving a Map as an _iterator_)
    - here, prefer `DictOps.iterate_vals()` or `DictOps.iterate_items()` which first sort by key
    - if key sorting is not preferred, write a specialized sort 

When making a specialized sort function over a set of entities, consider bundling the cost value with the entity id. If two entities have the same value, the id can be used to "break the tie" in a deterministic way. Example:

```python
vs: List[Vehicle] = ... #
sorted(vs, key=lambda v: v.distance_traveled_km)          # bad
sorted(vs, key=lambda v: (v.distance_traveled_km, v.id))  # good
```
