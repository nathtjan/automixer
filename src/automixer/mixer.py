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

    async def step(self):
        await asyncio.gather(
            self.service_collection.step(),
            self.bus.step()
        )

    async def run(self):
        try:
            logger.info("Starting Automixer...")
            self.bus._start()
            await self.service_collection.up()
            while True:
                logger.debug("Automixer stepping...")
                await self.step()
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Automixer run cancelled, shutting down...")
        finally:
            logger.info("Stopping Automixer...")
            await asyncio.gather(
                self.service_collection.down(),
                self.bus.stop(),
                return_exceptions=True
            )
