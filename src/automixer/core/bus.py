from typing import TYPE_CHECKING
import bubus

if TYPE_CHECKING:
    from automixer.services.base import BaseService


class EventBus(bubus.EventBus):
    def register_service(self, service: "BaseService"):
        """Register all event handlers in the service."""
        service._autoregister_handlers(self)

    def register_services(self, services: list["BaseService"]):
        """Register multiple services."""
        for service in services:
            self.register_service(service)


__all__ = ["EventBus"]
