import logging
import asyncio
from automixer import services, EventBus


logger = logging.getLogger(__name__)


class Automixer:
    def __init__(
        self,
        bus: EventBus,
        service_collection: services.ServiceCollection
    ):
        self.bus = bus
        self.service_collection = service_collection
        self._should_pause = False

    def pause(self):
        logger.info("Pausing Automixer...")
        self._should_pause = True
        self.service_collection.pause()

    def resume(self):
        logger.info("Resuming Automixer...")
        self._should_pause = False
        self.service_collection.resume()

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
        await self.service_collection.up()

    async def step(self):
        await asyncio.gather(
            self.service_collection.step(),
            self.bus.step()
        )

    async def stop(self):
        logger.info("Stopping Automixer...")
        await asyncio.gather(
            self.service_collection.down(),
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
