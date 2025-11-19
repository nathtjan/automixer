import time
from logging import getLogger
from queue import Queue
from automixer.core.events import (
    MixingResultEvent,
    ProgramChangeEvent,
    SceneType
)
from automixer.services.base import ThreadService, autoregister


logger = getLogger(__name__)


class InteractionService(ThreadService):
    SERVICE_NAME = "interaction"

    def __init__(
        self,
        bus,
        interactor,
        slide_scenenames: list[str],
        default_slide_scenename: str,
        cam_scenename: str,
        program_check_delay: float = 0.1
    ):
        super().__init__(bus)
        self._interactor = interactor
        self._slide_scenenames = slide_scenenames
        self._default_slide_scenename = default_slide_scenename
        self._cam_scenename = cam_scenename
        self._program_change_queue = Queue()
        self._program_check_delay = program_check_delay

    def switch_to_slide(self):
        preview = self._interactor.get_current_preview_scene()
        program = self._interactor.get_current_program_scene()
        if program in self._slide_scenenames:
            logger.info("Program scene unchanged since current is " + program)
            return
        if preview in self._slide_scenenames:
            sceneName = preview
        else:
            sceneName = self._default_slide_scenename
        logger.info("Switching program scene to " + sceneName)
        self._interactor.set_program_scene(sceneName)

    def switch_to_camera(self):
        program = self._interactor.get_current_program_scene()
        if program == self._cam_scenename:
            logger.info("Program scene unchanged since current is " + program)
            return
        logger.info("Switching program scene to " + self._cam_scenename)
        self._interactor.set_program_scene(self._cam_scenename)

    @autoregister
    def on_mixing_result(self, event: MixingResultEvent):
        if (event.scene_type is SceneType.SLIDE):
            self.switch_to_slide()
        elif (event.scene_type is SceneType.CAMERA):
            self.switch_to_camera()
        else:
            raise ValueError("Unknown scene type: " + str(event.scene_type))

    def run(self):
        prev_program = self._interactor.get_current_program_scene()
        while not self.should_stop():
            program = self._interactor.get_current_program_scene()
            if program != prev_program:
                logger.info("Detected program scene change to " + program)
                self._program_change_queue.put(program)
                prev_program = program
            time.sleep(self._program_check_delay)

    def step(self):
        while not self._program_change_queue.empty():
            program = self._program_change_queue.get()
            if (program in self._slide_scenenames
                or program == self._default_slide_scenename):
                scene_type = SceneType.SLIDE
            elif program == self._cam_scenename:
                scene_type = SceneType.CAMERA
            else:
                scene_type = SceneType.OTHER
            self.bus.dispatch(ProgramChangeEvent(
                scene_type=scene_type,
                scene_name=program
            ))


__all__ = ["InteractionService"]
