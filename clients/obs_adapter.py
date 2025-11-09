"""Small OBS adapter implementing MixerClient interface.

This adapter is intentionally lightweight — it accepts either an existing
obs websocket client instance or host/port/password to create one lazily.
"""
from typing import Optional
from clients.mixer_client import MixerClient

try:
    # obs-websocket-py v1/v4 compatibility depends on the package used in the repo.
    # We attempt to import the higher-level convenience module first.
    from obswebsocket import obsws, requests
except Exception:
    # If import fails at runtime, user can install obs-websocket-py or adapt this file.
    obsws = None
    requests = None


class OBSAdapter(MixerClient):
    def __init__(self, ws_client: Optional[object] = None, host: str = "localhost", port: int = 4444, password: str = ""):
        self._ws = ws_client
        self._host = host
        self._port = port
        self._password = password

    def connect(self):
        if self._ws:
            # assume user passed an already-connected client
            return
        if obsws is None:
            raise RuntimeError("obs-websocket-py not installed or failed to import")
        self._ws = obsws(self._host, self._port, self._password)
        self._ws.connect()

    def disconnect(self):
        if not self._ws:
            return
        try:
            self._ws.disconnect()
        finally:
            self._ws = None

    def set_program_scene(self, scene_name: str) -> None:
        if not self._ws:
            self.connect()
        # safe call — adapt depending on the obswebsocket version
        self._ws.call(requests.SetCurrentProgramScene(sceneName=scene_name))

    def get_current_program_scene(self) -> str:
        if not self._ws:
            self.connect()
        return self._ws.call(requests.GetCurrentProgramScene()).getSceneName()
