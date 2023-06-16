# Design

This page describes details specific to HIVE for new developers interacting with the library.

## table of contents

- **[immutability](#immutability)**: the modeling of system state in a HIVE simulation
- **[finite state machine](#finite-state-machine)**: how agent behavior is characterized
- **[error as value](#error-as-value)**: the choice to avoid exception throwing
- **[determinism](#determinism)**: details related to keeping HIVE runs deterministic
  - [iterating over immutables.Map collections](#iterating-over-map-collections)
  - [sorting based on some field is not enough](#sorting-based-on-some-field-is-not-enough)

## immutability

_todo_

## finite state machine

_todo_

## error as value

_todo_

## determinism

It is essential that HIVE produces deterministic runs so that research can explore A/B test cases with stable results. In this section, we describe a few important patterns in the HIVE codebase for tackling non-deterministic behavior.

#### iterating over Map collections

Most of the HIVE state is stored in hash maps. A [3rd party library](https://github.com/MagicStack/immutables) provides an immutable hash map via the Hash Array Mapped Trie (HAMT) data structure. While it is, for the most part, a drop-in replacement for a python Dict, it has one caveat, which is that insertion order is not guaranteed. This has determinism implications for HIVE. For this reason, any iteration of HAMT data structures must first be _sorted_. This is the default behavior for accessing the entity collections on a `SimulationState`, that they are first sorted by `EntityId`, such as `sim.get_vehicles()`.

Deeper within HIVE, whenever the HAMT data structure is interacted with, we must take care. There are two possible situations:
  1. the iteration order is irrelevant (for example, when iterating on a collection in order to write reports, or when updating a collection)
    - here, use of `.items()` iteration is acceptable
  2. the iteration order is sorted (exclusively when retrieving a Map as an _iterator_)
    - here, prefer `DictOps.iterate_vals()` or `DictOps.iterate_items()` which first sort by key
    - if key sorting is not preferred, write a specialized sort 

#### sorting based on some field is not enough

In some instances we want to sort a set of things in HIVE based on a field. For example, when updating vehicle states, we ensure we first update enqueued vehicles and that we update them in a first-in, first-out order. to do this, we sort ChargeQueueing vehicles by their `enqueue_time`. But this value is _not unique_, which means that any vehicles that share a common `enqueue_time` will have matching sort order resulting in a non-deterministic sort assignment. 

To address this, we supply a `Tuple[T, EntityId]` as the sort value. The id serves to "break the tie" in a deterministic way. Example:

```python
vs = sim.get_vehicles(filter_function=lambda v: isinstance(v.vehicle_state, ChargeQueueing))
sorted(vs, key=lambda v: v.vehicle_state.enqueue_time)          # bad
sorted(vs, key=lambda v: (v.vehicle_state.enqueue_time, v.id))  # good
```
