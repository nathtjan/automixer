from automixer.interactors.base import AbstractInteractor

try:
    from obswebsocket import obsws, requests
except Exception:  # pragma: no cover
    obsws = None
    requests = None


class OBSInteractor(AbstractInteractor):
    def __init__(self, host: str, port: int, password: str):
        self._host = host
        self._port = port
        self._password = password
        self._ws = None

    def connect(self):
        if obsws is None:
            raise RuntimeError(
                "obs-websocket-py not installed or failed to import")
        self._ws = obsws(self._host, self._port, self._password)
        self._ws.connect()

    def disconnect(self):
        if not self._ws:
            return
        self._ws.disconnect()
        self._ws = None

    def set_program_scene(self, scene_name: str) -> None:
        if not self._ws:
            self.connect()
        self._ws.call(requests.SetCurrentProgramScene(sceneName=scene_name))

    def get_current_program_scene(self) -> str:
        if not self._ws:
            self.connect()
        return self._ws.call(requests.GetCurrentProgramScene()).getSceneName()

    def get_current_preview_scene(self) -> str:
        if not self._ws:
            self.connect()
        return self._ws.call(requests.GetCurrentPreviewScene()).getSceneName()


__all__ = ["OBSInteractor"]
