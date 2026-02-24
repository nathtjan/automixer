import logging
import os
from automixer.interactors.base import AbstractInteractor

try:
    from obswebsocket import obsws, requests
except Exception:  # pragma: no cover
    obsws = None
    requests = None


logger = logging.getLogger(__name__)


class OBSInteractor(AbstractInteractor):
    def __init__(self, host: str, port: int, password: str = ""):
        self._host = host
        self._port = port
        
        # If password is None, try to read from environment variable
        if not password:
            password = os.getenv("OBS_PASSWORD", "")

        self._password = password

        self._ws = None

    def connect(self):
        if obsws is None:
            raise RuntimeError(
                "obs-websocket-py not installed or failed to import")

        try:
            ws = obsws(self._host, self._port, self._password)
            ws.connect()
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket at {self._host}:{self._port}: {e}")
            raise RuntimeError(f"Failed to connect to OBS WebSocket at {self._host}:{self._port}: {e}") from e

        self._ws = ws

        logger.info(f"Connected to OBS WebSocket at {self._host}:{self._port}")

        # Remove password from memory after connecting
        self._password = None

    def disconnect(self):
        if not self._ws:
            return
        self._ws.disconnect()
        self._ws = None

        logger.info(f"Disconnected from OBS WebSocket at {self._host}:{self._port}")

    def set_program_scene(self, scene_name: str) -> None:
        if not self._ws:
            self.connect()
        self._ws.call(requests.SetCurrentProgramScene(sceneName=scene_name))
        logger.info(f"Set program scene to '{scene_name}'")

    def get_current_program_scene(self) -> str:
        if not self._ws:
            self.connect()
        return self._ws.call(requests.GetCurrentProgramScene()).getSceneName()
    

    def get_current_preview_scene(self) -> str:
        if not self._ws:
            self.connect()
        return self._ws.call(requests.GetCurrentPreviewScene()).getSceneName()


__all__ = ["OBSInteractor"]
