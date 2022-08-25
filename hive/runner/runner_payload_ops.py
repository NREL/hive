from typing import Iterable, Tuple, Type, Union
from returns.result import ResultE, Success, Failure


from hive.runner.runner_payload import RunnerPayload
from hive.state.simulation_state.simulation_state_ops import (
    modify_entities_safe as _modify_entities_safe,
)

from hive.dispatcher.instruction_generator.instruction_generator import (
    InstructionGenerator,
)
from hive.util.fp import throw_or_return
from hive.util.typealiases import Entity


def update_instruction_generator_safe(
    rp: RunnerPayload, ig: InstructionGenerator
) -> ResultE[RunnerPayload]:
    """
    Inject an updated InstructionGenerator into a runner payload

    Safe method
    """
    new_step_fn_or_error = rp.u.step_update.update_instruction_generator(ig)
    if isinstance(new_step_fn_or_error, Failure):
        return new_step_fn_or_error
    else:
        new_update = rp.u._replace(step_update=new_step_fn_or_error.unwrap())
        new_rp = rp._replace(u=new_update)
        return Success(new_rp)


def update_instruction_generator(
    rp: RunnerPayload, ig: InstructionGenerator
) -> RunnerPayload:
    """
    Inject an updated InstructionGenerator into a runner payload

    Unsafe method
    """
    rp_or_error = update_instruction_generator_safe(rp, ig)
    return throw_or_return(rp_or_error)


def get_instruction_generator_safe(
    rp: RunnerPayload, ig: Union[str, Type[InstructionGenerator]]
) -> ResultE[InstructionGenerator]:
    """
    Extract an instruction generator from a runner payload
    """
    return rp.u.step_update.get_instruction_generator(ig)


def get_instruction_generator(
    rp: RunnerPayload, ig: Union[str, Type[InstructionGenerator]]
) -> InstructionGenerator:
    """
    Extract an instruction generator from a runner payload
    """
    new_ig_or_error = rp.u.step_update.get_instruction_generator(ig)
    return throw_or_return(new_ig_or_error)


def set_instruction_generators(
    rp: RunnerPayload, instruction_generators: Tuple[InstructionGenerator]
) -> RunnerPayload:
    """
    Set the instruction generators on a runner payload.
    Overwrites any existing instruction generators.

    :param rp: The runner payload to update
    :param instruction_generators: The instruction generators to set

    :return: The updated runner payload
    """
    new_step_simulation = rp.u.step_update.update_instruction_generators(
        instruction_generators
    )
    new_update = rp.u._replace(step_update=new_step_simulation)
    new_rp = rp._replace(u=new_update)
    return new_rp


def modify_entities_safe(
    rp: RunnerPayload, entities: Iterable[Entity]
) -> ResultE[RunnerPayload]:
    """
    Modify entities in a runner payload
    """
    new_s_or_error = _modify_entities_safe(rp.s, entities)

    if isinstance(new_s_or_error, Failure):
        return new_s_or_error
    else:
        new_rp = rp._replace(s=new_s_or_error.unwrap())
        return Success(new_rp)


def modify_entities(rp: RunnerPayload, entities: Iterable[Entity]) -> RunnerPayload:
    """
    Modify entities in a runner payload
    """
    return throw_or_return(modify_entities_safe(rp, entities))
