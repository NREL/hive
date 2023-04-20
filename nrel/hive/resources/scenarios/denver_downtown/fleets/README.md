Fleets are specified with a yaml file.

Each key represents the identifies of a fleet and then each sub key represents which entities are part of that fleet.

For example, let's say we have this fleet file:

```yaml
tnc_1:
  vehicles:
    - v1   
    - v2   
  stations:
    - s1
  bases:
    - b1

tnc_2:
  vehicles:
    - v1   
    - v3   
  stations:
    - s2
  bases:
    - b2
```

In this case, vehicle `v1` belongs to both fleets and so would have access to all entities listed here.
Vehicle `v2` is only in the fleet `tnc_1` and so would only have access to the stations `s1`.

```{note}
if an entity is not specified in this file _or_ if this file is not specified in the scenario config,
the simulation will tag it with a 'public' membership and there will be no restrictions entity interactions. 
```
