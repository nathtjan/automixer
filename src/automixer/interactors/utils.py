from typing import Union
from automixer.interactors.base import AbstractInteractor
from automixer.interactors.obs import OBSInteractor
from automixer.interactors.enum import InteractorType


def get_interactor_class(interactor_type: Union[str, InteractorType]) -> AbstractInteractor:
    if isinstance(interactor_type, str):
        interactor_type = InteractorType(interactor_type.lower())

    if interactor_type is InteractorType.OBS:
        return OBSInteractor()
    else:
        raise ValueError(f"Unknown interactor type: {interactor_type}")


__all__ = [
    "InteractorType",
    "get_interactor_class"
]
