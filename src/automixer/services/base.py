import logging
import inspect
import threading
from typing import overload, Type
from automixer.core.bus import EventBus
from automixer.core.events import BaseEvent


logger = logging.getLogger(__name__)


def _default_autoregister(func: callable) -> callable:
    func._autoregister = True
    return func


def _custom_autoregister(
    func: callable,
    event_type: Type[BaseEvent] = None,
    self_name: str = 'self'
) -> callable:
    func._autoregister = True
    func._autoregister_config = {
        'event_type': event_type,
        'self_name': self_name,
    }
    return func


@overload
def autoregister(
    event_type: Type[BaseEvent] = None,
    self_name: str = 'self'
) -> callable:
    ...


@overload
def autoregister(func: callable) -> callable:
    ...


def autoregister(*args, **kwargs):
    """Add autoregister attribute(s) to a method or function."""

    # Default case: used as @autoregister
    if len(args) == 1 and callable(args[0]) and not kwargs:
        func: callable = args[0]
        return _default_autoregister(func)

    # Custom case: used as @autoregister(...)
    def wrapper(func):
        return _custom_autoregister(func, *args, **kwargs)
    return wrapper


class BaseService():
    def __init__(self, bus: EventBus):
        self.bus = bus
        self._autoregister_handlers(bus)

    def _autoregister_handlers(self, bus: EventBus):
        """Register all event handlers in the service."""
        for name, method in inspect.getmembers(self, predicate=inspect.isroutine):
            if hasattr(method, '_autoregister') and method._autoregister:
                config = getattr(method, '_autoregister_config', {})
                self_name = config.get('self_name', 'self')
                event_type = config.get('event_type', None)
                # Get the event type from the method's first parameter annotation
                sig = inspect.signature(method)
                # Remove 'self' and 'return' from parameters if exists
                sig = {
                    k: v for k, v in sig.parameters.items()
                    if k != self_name and k != 'return'
                }
                if len(sig) != 1:
                    raise ValueError(
                        f"Autoregistered handler '{name}' must have exactly one parameter: "
                        "the event object. Ensure it is properly annotated and you are"
                        f"using '{self_name}' for the instance parameter."
                    )
                if event_type is None:
                    event_type = next(iter(sig.values()))
                bus.on(event_type, method)

    def step(self):
        """Perform a single step of the service. Override in subclasses if needed."""
        pass


class ThreadService(BaseService):
    SERVICE_NAME = None

    def __init__(self, bus: EventBus):
        super().__init__(bus)
        self._should_stop = False
        self._thread = None
        if self.SERVICE_NAME is None:
            self.service_name = self.__class__.__name__
        else:
            self.service_name = self.SERVICE_NAME

    def should_stop(self) -> bool:
        return self._should_stop

    def run(self):
        raise NotImplementedError(
            "ThreadedService subclasses must implement run()")

    def is_alive(self):
        return (self._thread is not None) and self._thread.is_alive()

    def start(self):
        if self.is_alive():
            return
        self._should_stop = False
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logger.info(f"{self.service_name} started")

    def stop(self):
        if not self.is_alive():
            return
        self._should_stop = True
        self._thread.join()
        self._thread = None
        logger.info(f"{self.service_name} stopped")


__all__ = [
    "autoregister",
    "BaseService",
    "ThreadService"
]
