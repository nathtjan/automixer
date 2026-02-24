import argparse
import asyncio
import json
import logging
from dotenv import load_dotenv
from automixer.builder import build_from_config
from automixer.config import AutomixerConfig
from automixer.mixer import Automixer
from automixer import EventBus


def run(config_path: str):
    with open(config_path, "r") as f:
        config = json.load(f)

    bus = EventBus()
    automixer_config = AutomixerConfig.model_validate(config)
    automixer = build_from_config(automixer_config, bus=bus)
    if not isinstance(automixer, Automixer):
        raise TypeError("The built object is not an instance of Automixer")

    asyncio.run(automixer.run())


def main():
    parser = argparse.ArgumentParser(description="Automixer Command Line Interface")
    parser.add_argument("-c", "--config", type=str, default="./config.json", help="Path to the configuration file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    load_dotenv()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    run(args.config)


if __name__ == "__main__":
    main()
