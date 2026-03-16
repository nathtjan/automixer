import logging
import asyncio
from typing import List

from automixer import EventBus
from automixer.services.base import BaseService


logger = logging.getLogger(__name__)


class Automixer:
    def __init__(
        self,
        bus: EventBus,
        services: List[BaseService]
    ):
        for service in services:
            if not isinstance(service, BaseService):
                raise ValueError(f"All services must be instances of BaseService, got {type(service)}")

        self.bus = bus
        self.services = services
        self._should_pause = False

    def pause(self):
        logger.info("Pausing Automixer...")
        self._should_pause = True
        for service in self.services:
            service.pause()

    def resume(self):
        logger.info("Resuming Automixer...")
        self._should_pause = False
        for service in self.services:
            service.resume()

    def toggle_pause(self):
        if self.should_pause():
            self.resume()
        else:
            self.pause()

    def should_pause(self):
        return self._should_pause

    async def start(self):
        logger.info("Starting Automixer...")
        self.bus._start()
        await asyncio.gather(*[service.up() for service in self.services])

    async def step(self):
        await asyncio.gather(
            asyncio.gather(*[service.step() for service in self.services]),
            self.bus.step()
        )

    async def stop(self):
        logger.info("Stopping Automixer...")
        await asyncio.gather(
            asyncio.gather(*[service.down() for service in self.services]),
            self.bus.stop(),
        )

    async def run(self):
        try:
            await self.start()
            while True:
                if not self.should_pause():
                    await self.step()
                else:
                    # Yield to the event loop while paused so the TUI stays responsive
                    await asyncio.sleep(0.05)
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Automixer run cancelled, shutting down...")
        finally:
            await self.stop()
