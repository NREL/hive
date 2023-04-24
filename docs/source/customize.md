# Customize

In addition to using hive as a command line application to run a simulation, you can also use hive as a library for co-simulation or you can extend the existing control logic.

## Co-Simulation

Co-simulation can be done using the `nrel.hive.app.hive_cosim` module.

That module exposes a `crank` function that takes in a RunnerPayload and an integer that defines how many time steps should be run and returns a `CrankResult` object that includes the updated RunnerPayload and its sim time. At this point, you can examine the simulation state and decide what to do next, continuing in this fashion.

## Custom Control Logic

Adding custom control logic can be done by creating a sub class for the `InstructionGenerator` class and overriding the `generate_instructions` method. You can then inject the control module into the simulation at load time using the `load_scenario` function and then, at crank step, you can optionally update your custom control object by getting it with the `get_instruction_generator` function, modifying it and putting it back into the simulation with `update_instruction_generator`.

## Example

See the [cosim_custom_dispatcher.py](https://github.com/NREL/hive/blob/main/examples/cosim_custom_dispatcher.py) file for an example of using custom control logic with the co-simulation API.
