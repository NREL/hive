from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instructions import (
    IdleInstruction,
    DispatchTripInstruction
)


def serialize(instruction: Instruction) -> str:
    """
    converts the instruction name and parameters into a string representation for serialization
    :param instruction: some instruction
    :return: a string representation of the instruction
    """
    if isinstance(instruction, IdleInstruction):
        return f'{{"instruction": "IdleInstruction", "vehicle_id": "{instruction.vehicle_id}"}}'
    elif isinstance(instruction, DispatchTripInstruction):
        return f'{{"instruction": "DispatchTripInstruction", "vehicle_id": "{instruction.vehicle_id}", "request_id": "{instruction.request_id}"}}'
    else:
        # incomplete here
        raise NotImplementedError
