from abc import ABC, abstractmethod


class AbstractInteractor(ABC):
    """Abstract base for mixer controllers (OBS, vMix, etc.)."""

    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_program_scene(self, scene_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_current_program_scene(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_current_preview_scene(self) -> str:
        raise NotImplementedError


__all__ = ["AbstractInteractor"]
