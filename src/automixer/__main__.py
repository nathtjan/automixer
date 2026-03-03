import argparse
import asyncio
import json
import logging
from typing import Tuple

from dotenv import load_dotenv

from automixer import EventBus
from automixer.builder import build_from_config
from automixer.config import AutomixerConfig
from automixer.mixer import Automixer


def build_automixer(config_path: str) -> Tuple[Automixer, EventBus]:
    """Load configuration and build an Automixer instance with its bus."""
    with open(config_path, "r") as f:
        config = json.load(f)

    bus = EventBus(name="MainBus")
    automixer_config = AutomixerConfig.model_validate(config)
    automixer = build_from_config(automixer_config, bus=bus)
    if not isinstance(automixer, Automixer):
        raise TypeError("The built object is not an instance of Automixer")
    return automixer, bus


async def run_headless(config_path: str):
    automixer, _ = build_automixer(config_path)
    await automixer.run()


async def run_with_tui(config_path: str):
    from automixer.tui import create_ui

    automixer, bus = build_automixer(config_path)

    app, log_handler, _state_service = await create_ui(bus)

    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)

    try:
        async with asyncio.TaskGroup() as tg:
            task_tui = tg.create_task(app.run_async())
            task_automixer = tg.create_task(automixer.run())
            tasks = [task_tui, task_automixer]
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            # Cancel all others
            for task in pending:
                task.cancel()
    except ExceptionGroup as eg:
        import traceback
        print(f"Caught an exception group during TUI run with {len(eg.exceptions)} sub-exceptions:")
        for i, exc in enumerate(eg.exceptions):
            print(f"  Sub-exception {i+1}: {exc}")
            # print traceback
            print("  Traceback:")
            traceback.print_exception(type(exc), exc, exc.__traceback__)
    except Exception as e:
        print(f"Error occurred during TUI run: {e}")
    finally:
        print("Shutting down...")
        root_logger.removeHandler(log_handler)


def configure_logging(level: int, to_console: bool):
    """Set root logging handlers. For TUI we avoid console to prevent redraw issues."""
    handlers = []
    if to_console:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Automixer Command Line Interface")
    parser.add_argument("-c", "--config", type=str, default="./config.json", help="Path to the configuration file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--headless", action="store_true", help="Run without Textual terminal UI")
    args = parser.parse_args()

    load_dotenv()
    level = logging.DEBUG if args.verbose else logging.INFO

    if args.headless:
        configure_logging(level, to_console=True)
        asyncio.run(run_headless(args.config))
    else:
        configure_logging(level, to_console=False)
        asyncio.run(run_with_tui(args.config))


if __name__ == "__main__":
    main()
