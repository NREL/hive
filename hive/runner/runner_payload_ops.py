from typing import Type, Union
from returns.result import ResultE, Success, Failure

from hive.runner.runner_payload import RunnerPayload
from hive.dispatcher.instruction_generator.instruction_generator import (
    InstructionGenerator,
)


def update_instruction_generator(
    rp: RunnerPayload, ig: InstructionGenerator
) -> ResultE[RunnerPayload]:
    """
    Inject an updated InstructionGenerator into a runner payload
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


def get_instruction_generator(
    rp: RunnerPayload, ig: Union[str, Type[InstructionGenerator]]
) -> ResultE[InstructionGenerator]:
    """
    Extract an instruction generator from a runner payload
    """
    return rp.u.step_update.get_instruction_generator(ig)
