import logging
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
        self.bus.register_services(service_collection.services)

    def run(self):
        try:
            logger.info("Starting Automixer...")
            self.service_collection.start()
            while True:
                logger.debug("Automixer stepping...")
                self.service_collection.step()
        except KeyboardInterrupt:
            logger.info("Stopping Automixer...")
            self.service_collection.stop()
