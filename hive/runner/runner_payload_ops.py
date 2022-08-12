from typing import Type, Union
from returns.result import ResultE, Success, Failure

from hive.runner.runner_payload import RunnerPayload
from hive.dispatcher.instruction_generator.instruction_generator import (
    InstructionGenerator,
)


def update_instruction_generator_safe(
    rp: RunnerPayload, ig: InstructionGenerator
) -> ResultE[RunnerPayload]:
    """
    Inject an updated InstructionGenerator into a runner payload

    Safe method
    """
    new_step_fn_or_error = rp.u.step_update.update_instruction_generator(ig)
    if isinstance(new_step_fn_or_error, Success):
        new_update = rp.u._replace(step_update=new_step_fn_or_error.unwrap())
        new_rp = rp._replace(u=new_update)
        return Success(new_rp)
    elif isinstance(new_step_fn_or_error, Failure):
        return new_step_fn_or_error
    else:
        return Failure(
            Exception(
                "StepUpdate.update_instruction_generator failed to return a Result"
            )
        )


def update_instruction_generator(
    rp: RunnerPayload, ig: InstructionGenerator
) -> RunnerPayload:
    """
    Inject an updated InstructionGenerator into a runner payload

    Unsafe method
    """
    rp_or_error = update_instruction_generator_safe(rp, ig)
    if isinstance(rp_or_error, Success):
        rp = rp_or_error.unwrap()
        return rp
    elif isinstance(rp_or_error, Failure):
        err = rp_or_error.failure()
        raise err
    else:
        raise Exception("update_instruction_generator_safe failed to produce a result")


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

    if isinstance(new_ig_or_error, Success):
        ig = new_ig_or_error.unwrap()
        return ig
    elif isinstance(new_ig_or_error, Failure):
        err = new_ig_or_error.failure()
        raise err
    else:
        raise Exception("get_instruction_generator_safe failed to produce a result")
