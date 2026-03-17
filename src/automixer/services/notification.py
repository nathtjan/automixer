import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from automixer.core.events import BaseEvent
from automixer.services.base import BaseService, autoregister


logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    @abstractmethod
    def notify(self, payload: dict[str, Any]):
        """Send a notification payload."""

    def up(self):
        """Start the notifier if needed."""
        pass

    def down(self):
        """Stop the notifier if needed."""
        pass


class MQTTNotifier(BaseNotifier):
    def __init__(
        self,
        host: str,
        topic: str,
        port: int = 1883,
        qos: int = 0,
        retain: bool = False,
        keepalive: int = 60,
        use_tls: bool = False,
        mqtt_version: int = 5,
        client_id: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.host = host
        self.port = port
        self.topic = topic
        self.qos = qos
        self.retain = retain
        self.keepalive = keepalive
        self.client_id = client_id
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.mqtt_version = mqtt_version
        self._client = None

    def up(self):
        # Lazy import so MQTT dependency stays optional unless used.
        from paho.mqtt import client as mqtt_client

        def _is_failure(reason_code: Any) -> bool:
            try:
                return bool(reason_code.is_failure)
            except Exception:
                try:
                    return int(reason_code) != 0
                except Exception:
                    return True

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if not _is_failure(reason_code):
                logger.info(
                    "MQTT notifier connected to %s:%s topic=%s",
                    self.host,
                    self.port,
                    self.topic,
                )
            else:
                logger.warning(
                    "MQTT notifier connection rejected rc=%s host=%s port=%s topic=%s",
                    reason_code,
                    self.host,
                    self.port,
                    self.topic,
                )

        def on_pre_connect(client, userdata):
            logger.debug(
                "MQTT notifier preparing connection host=%s port=%s topic=%s",
                self.host,
                self.port,
                self.topic,
            )

        def on_disconnect(
            client,
            userdata,
            disconnect_flags,
            reason_code,
            properties=None,
        ):
            if _is_failure(reason_code):
                logger.warning(
                    "MQTT notifier disconnected unexpectedly rc=%s host=%s port=%s",
                    reason_code,
                    self.host,
                    self.port,
                )
            else:
                logger.info(
                    "MQTT notifier disconnected rc=%s host=%s port=%s",
                    reason_code,
                    self.host,
                    self.port,
                )

        def on_connect_fail(client, userdata):
            logger.error(
                "MQTT notifier connect failed host=%s port=%s",
                self.host,
                self.port,
            )

        def on_publish(client, userdata, mid, reason_code=None, properties=None):
            logger.debug(
                "MQTT notifier publish acknowledged mid=%s rc=%s topic=%s",
                mid,
                reason_code,
                self.topic,
            )

        def on_subscribe(client, userdata, mid, reason_code_list, properties=None):
            logger.debug(
                "MQTT notifier subscribed mid=%s rc=%s",
                mid,
                reason_code_list,
            )

        def on_unsubscribe(client, userdata, mid, reason_code_list, properties=None):
            logger.debug(
                "MQTT notifier unsubscribed mid=%s rc=%s",
                mid,
                reason_code_list,
            )

        def on_message(client, userdata, message):
            logger.debug(
                "MQTT notifier received message topic=%s qos=%s retained=%s payload_len=%s",
                message.topic,
                message.qos,
                message.retain,
                len(message.payload or b""),
            )

        self._client = mqtt_client.Client(
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
            client_id=self.client_id,
            protocol=self.mqtt_version
        )
        self._client.on_pre_connect = on_pre_connect
        self._client.on_connect = on_connect
        self._client.on_disconnect = on_disconnect
        self._client.on_connect_fail = on_connect_fail
        self._client.on_publish = on_publish
        self._client.on_subscribe = on_subscribe
        self._client.on_unsubscribe = on_unsubscribe
        self._client.on_message = on_message
        if self.username is not None:
            self._client.username_pw_set(self.username, self.password)
        if self.use_tls:
            self._client.tls_set()
        self._client.connect(self.host, self.port, self.keepalive)
        self._client.loop_start()

    def down(self):
        if self._client is None:
            return
        self._client.loop_stop()
        self._client.disconnect()
        self._client = None
        logger.info("MQTT notifier disconnected")

    def notify(self, payload: dict[str, Any]):
        if self._client is None:
            raise RuntimeError("MQTT notifier has not been started")
        body = json.dumps(payload, default=str)
        self._client.publish(self.topic, body, qos=self.qos, retain=self.retain)


class NotificationService(BaseService):
    def __init__(
        self,
        bus,
        notifier: BaseNotifier,
        include_event_types: list[str] | None = None,
        exclude_event_types: list[str] | None = None,
    ):
        super().__init__(bus)
        self.notifier = notifier
        self.include_event_types = set(include_event_types or [])
        self.exclude_event_types = set(exclude_event_types or [])

    async def up(self):
        self.notifier.up()

    async def down(self):
        self.notifier.down()

    def _serialize_event(self, event: BaseEvent) -> dict[str, Any]:
        if hasattr(event, "serialize"):
            data = event.serialize(mode="json")
        elif hasattr(event, "model_dump"):
            data = event.model_dump(mode="json")
        elif hasattr(event, "dict"):
            data = event.dict()
        else:
            data = dict(event.__dict__)

        payload = {
            "event_type": event.__class__.__name__,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return payload


    def _should_notify(self, event_type: str) -> bool:
        if self.include_event_types and event_type not in self.include_event_types:
            return False
        if self.exclude_event_types and event_type in self.exclude_event_types:
            return False
        return True

    @autoregister(event_type="*")
    def on_event(self, event: BaseEvent):
        event_type = event.__class__.__name__
        if not self._should_notify(event_type):
            return
        payload = self._serialize_event(event)
        logger.debug("Sending notification for event type %s: %s", event_type, payload)
        self.notifier.notify(payload)


__all__ = [
    "BaseNotifier",
    "MQTTNotifier",
    "NotificationService",
]
