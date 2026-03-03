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
                await self.step()
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Automixer run cancelled, shutting down...")
        finally:
            await self.stop()
