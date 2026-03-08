import asyncio
import importlib.resources
import logging
import time
from dataclasses import dataclass, replace
from typing import Callable, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static, Log, Collapsible

from automixer.core.events import (
    MixingResultEvent,
    TranscriptionStateEvent,
    ProgramChangeEvent,
    SceneType,
    Slide2CamScoreEvent,
    SlideChangeEvent,
    SlideOCREvent,
    TranscriptionStateEvent,
)
from automixer.mixer import Automixer
from automixer.services.base import BaseService, autoregister
from automixer.core.bus import EventBus


@dataclass
class UIState:
    scene_type: Optional[SceneType] = None
    scene_name: Optional[str] = None
    slide_changed_at: Optional[float] = None
    slide_text: str = ""
    transcription: str = ""
    slide2cam_score: Optional[float] = None
    last_decision: Optional[SceneType] = None
    last_decision_at: Optional[float] = None

    def snapshot(self) -> "UIState":
        return replace(self)


class UIStateService(BaseService):
    """Listen to bus events and push compact state snapshots to the UI."""

    def __init__(self, bus: EventBus, state_queue: asyncio.Queue[UIState]):
        super().__init__(bus)
        self.state = UIState()
        self.state_queue = state_queue

    def _push(self):
        try:
            self.state_queue.put_nowait(self.state.snapshot())
        except asyncio.QueueFull:
            # Drop updates if UI lags; the next one will carry fresh state
            pass

    @autoregister
    def on_program_change(self, event: ProgramChangeEvent):
        self.state.scene_type = event.scene_type
        self.state.scene_name = event.scene_name
        self._push()

    @autoregister
    def on_slide_change(self, event: SlideChangeEvent):
        self.state.slide_changed_at = time.time()
        self._push()

    @autoregister
    def on_slide_ocr(self, event: SlideOCREvent):
        text = " ".join([elem[1] for elem in event.ocr_result]) if event.ocr_result else ""
        self.state.slide_text = text
        self._push()

    @autoregister
    def on_transcription_state(self, event: TranscriptionStateEvent):
        self.state.transcription = event.text
        self._push()

    @autoregister
    def on_mixing_result(self, event: MixingResultEvent):
        self.state.last_decision = event.scene_type
        self.state.last_decision_at = time.time()
        self._push()

    @autoregister
    def on_slide2cam_score(self, event: Slide2CamScoreEvent):
        self.state.slide2cam_score = event.score
        self._push()


class LogQueueHandler(logging.Handler):
    """Pipe logging records into an asyncio queue for the UI."""

    def __init__(self, queue: asyncio.Queue[str]):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.queue.put_nowait(msg)
        except Exception:  # pragma: no cover - defensive
            self.handleError(record)


class AutomixerApp(App):
    TITLE = "Automixer"
    CSS_PATH = importlib.resources.files("automixer").joinpath("resources", "tcss", "automixer.tcss")
    BINDINGS = [
        Binding("p", "toggle_pause", "Pause/Resume", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(
        self,
        state_queue: asyncio.Queue[UIState],
        log_queue: asyncio.Queue[str],
        automixer: Automixer,
        on_exit: Optional[Callable[[], None]] = None,
    ):
        super().__init__()
        self.state_queue = state_queue
        self.log_queue = log_queue
        self.automixer = automixer
        self.on_exit = on_exit
        self._state_task: Optional[asyncio.Task] = None
        self._log_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Container(id="main"):
            with Vertical(id="program-scene-group"):
                yield Static("Program Scene", classes="label")
                yield Static("-", id="scene", classes="value")
            with Vertical(id="last-decision-group"):
                yield Static("Last Decision", classes="label")
                yield Static("-", id="decision", classes="value")
            with Vertical(id="slide2cam-score-group"):
                yield Static("Slide→Cam Score", classes="label")
                yield Static("-", id="score", classes="value")
            with Vertical(id="slide-ocr-group"):
                yield Static("Slide OCR", classes="label")
                yield Static("-", id="slide", classes="value")
            with Vertical(id="transcription-group"):
                yield Static("Transcription", classes="label")
                yield Static("-", id="transcription", classes="value")
        with Collapsible(title="Logs"):
            yield Log(id="log", highlight=True)

    async def on_mount(self) -> None:
        # Background tasks consume queues and update widgets
        self._state_task = asyncio.create_task(self._drain_state())
        self._log_task = asyncio.create_task(self._drain_logs())

    async def on_unmount(self) -> None:
        for task in (self._state_task, self._log_task):
            if task is not None:
                task.cancel()
        if self.on_exit:
            self.on_exit()

    async def _drain_state(self) -> None:
        while True:
            state = await self.state_queue.get()
            self._render_state(state)

    async def _drain_logs(self) -> None:
        log_widget = self.query_one("#log", Log)
        while True:
            line = await self.log_queue.get()
            log_widget.write_line(line)

    def _render_state(self, state: UIState):
        scene_label = self.query_one("#scene", Static)
        decision_label = self.query_one("#decision", Static)
        score_label = self.query_one("#score", Static)
        slide_label = self.query_one("#slide", Static)
        transcription_label = self.query_one("#transcription", Static)

        scene_text = "-"
        if state.scene_type:
            scene_text = state.scene_type.value
            if state.scene_name:
                scene_text += f" ({state.scene_name})"
        scene_label.update(scene_text)

        decision_text = "-"
        if state.last_decision:
            decision_text = state.last_decision.value
            if state.last_decision_at:
                decision_text += f" @ {time.strftime('%H:%M:%S', time.localtime(state.last_decision_at))}"
        decision_label.update(decision_text)

        score_text = "-"
        if state.slide2cam_score is not None:
            score_text = f"{state.slide2cam_score:.3f}"
        score_label.update(score_text)

        slide_label.update(state.slide_text or "-")
        transcription_label.update(state.transcription or "-")

    def action_toggle_pause(self) -> None:
        """Toggle the automixer pause state."""
        self.automixer.toggle_pause()


async def create_ui(bus: EventBus, automixer: Automixer) -> tuple[AutomixerApp, LogQueueHandler, UIStateService]:
    state_queue: asyncio.Queue[UIState] = asyncio.Queue(maxsize=100)
    log_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=200)

    # Bridge bus events into state snapshots
    state_service = UIStateService(bus, state_queue)

    # Logging handler to feed bottom bar
    handler = LogQueueHandler(log_queue)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%H:%M:%S")
    handler.setFormatter(formatter)

    app = AutomixerApp(state_queue=state_queue, log_queue=log_queue, automixer=automixer)
    return app, handler, state_service
