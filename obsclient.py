import os
import sys
import time
from dotenv import load_dotenv
from obswebsocket import obsws


load_dotenv()

ws = obsws(
	os.environ["HOST"],
	os.environ["PORT"],
	os.environ["PASSWORD"]
)