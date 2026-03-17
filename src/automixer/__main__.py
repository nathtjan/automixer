import argparse
import asyncio
from datetime import datetime
import logging
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

from automixer import EventBus
from automixer.builder import build_from_config
from automixer.config import AutomixerConfig
from automixer.mixer import Automixer
from automixer.utils.file import load_yaml


def build_automixer(config_path: str) -> Tuple[Automixer, EventBus]:
    """Load configuration and build an Automixer instance with its bus."""
    config = load_yaml(config_path)

    bus = EventBus(name="MainBus")
    automixer_config = AutomixerConfig.model_validate(config["mixer"])
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

    app, log_handler, _state_service = await create_ui(bus, automixer)

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


def resolve_log_file_path(log_dir: str | None, log_file: str | None) -> Path | None:
    """Resolve output log path from CLI flags and ensure parent directories exist."""
    if log_file:
        log_path = Path(log_file)
    elif log_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = Path(log_dir) / f"{timestamp}.log"
    else:
        return None

    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path


def configure_logging(level: int, to_console: bool, log_file_path: Path | None = None):
    """Set root logging handlers. For TUI we avoid console to prevent redraw issues."""
    handlers = []
    if to_console:
        handlers.append(logging.StreamHandler())
    if log_file_path is not None:
        handlers.append(logging.FileHandler(log_file_path, mode="a", encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Automixer Command Line Interface")
    parser.add_argument("-c", "--config", type=str, default="./config.yaml", help="Path to the YAML configuration file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--headless", action="store_true", help="Run without Textual terminal UI")
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument("--log-dir", type=str, help="Directory for log files; filename will use startup timestamp")
    log_group.add_argument("--log-file", type=str, help="Path to log file")
    args = parser.parse_args()

    load_dotenv()
    level = logging.DEBUG if args.verbose else logging.INFO
    log_file_path = resolve_log_file_path(args.log_dir, args.log_file)

    if args.headless:
        configure_logging(level, to_console=True, log_file_path=log_file_path)
        asyncio.run(run_headless(args.config))
    else:
        configure_logging(level, to_console=False, log_file_path=log_file_path)
        asyncio.run(run_with_tui(args.config))


if __name__ == "__main__":
    main()
