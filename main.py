from datetime import datetime
import logging
import os
import time
import numpy as np
import cv2
from obswebsocket import requests
from obsclient import ws
from sobel import sobel_edge
import easyocr
from recorder import Recorder
from transcriber import OpenAITranscriber
import queue
from metric import lcs, lcs_1gram


def setup_logger(base_dir="./logs"):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    filename = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    filename += ".txt"

    save_path = os.path.join(base_dir, filename)

    file_handler = logging.FileHandler(save_path)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
    	"%(asctime)s %(levelname)-8s %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logging.basicConfig(
    	level=logging.INFO,
    	format="%(asctime)s %(levelname)-8s %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
    )

    return logger


logger = setup_logger()


ws.connect()


PPT_scenenames = ["FULL PPT", "KHOTBAH MODE 1", "KHOTBAH MODE 2"]
cam_scenename = "UTAMA DECKLINK"
default_PPT_scenename = PPT_scenenames[0]


def switch_to_PPT():
	curr_preview = ws.call(requests.GetCurrentPreviewScene()).getSceneName()
	curr_program = ws.call(requests.GetCurrentProgramScene()).getSceneName()
	if curr_program in PPT_scenenames:
		logger.info("Program scene unchanged since current is " + curr_program)
		return
	if curr_preview in PPT_scenenames:
		sceneName = curr_preview
	else:
		sceneName = default_PPT_scenename

	ws.call(requests.SetCurrentProgramScene(sceneName=sceneName))
	logger.info("Switched program scene to " + sceneName)


def switch_to_cam():
	curr_preview = ws.call(requests.GetCurrentPreviewScene()).getSceneName()
	curr_program = ws.call(requests.GetCurrentProgramScene()).getSceneName()
	if curr_program == cam_scenename:
		logger.info("Program scene unchanged since current is " + curr_program)
		return

	ws.call(requests.SetCurrentProgramScene(sceneName=cam_scenename))
	logger.info("Switched program scene to " + cam_scenename)


onchange_delay_dur = 2
delay_dur = 0.1
edge_threshold = 20
diff_threshold = 5
full_black_threshold_mean = 36
full_black_threshold_std = 5
cam = cv2.VideoCapture(3)
img_before = None
obs_vcam_default = cv2.imread("obs_vcam_default.png")

rouge_1gram_weight = 0.9
rouge_l_weight = 0.1
rouge_threshold = 0.8
transition_back_delay = 1

reader = easyocr.Reader(["id", "en"])
recording_queue = queue.Queue()
transcription_queue = queue.Queue()
recorder = Recorder(23, recording_queue)
transcriber = OpenAITranscriber(recording_queue, transcription_queue)
slide_text = ""
transcription = ""


def is_full_black(img):
	mean = np.mean(img)
	std = np.std(img)
	return (mean < full_black_threshold_mean
                and std < full_black_threshold_std)


def is_obs_vcam_default(img):
    diff = img - obs_vcam_default
    return (diff.mean() <= 1.0 and diff.std() <= 0.5)


def onchange():
	logger.info("Change detected!")
	switch_to_PPT()
	slide_text = ""
	transcription = ""
	recorder.start()
	time.sleep(onchange_delay_dur)


def clear_queue(queue):
    while not queue.empty():
        queue.get()


logger.info("AUTOMIXER v2")
logger.info("Running...")
while True:
	retval, img = cam.read()
	if not retval:
		continue

	if (
		img_before is not None
		and not is_full_black(img_before)
		and not is_full_black(img)
        and not is_obs_vcam_default(img_before)
        and not is_obs_vcam_default(img)
	):
		img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		edge_gray = sobel_edge(img_gray)
		edge = cv2.cvtColor(edge_gray, cv2.COLOR_GRAY2BGR)
		diff = np.abs(
			img.astype(np.int16)
			- img_before.astype(np.int16)
		).astype(np.uint8)
		diff *= edge < edge_threshold
		mean_diff = np.mean(diff)
		if mean_diff > diff_threshold:
			onchange()

	img_before = img

	curr_program = ws.call(requests.GetCurrentProgramScene()).getSceneName()
	if curr_program not in PPT_scenenames:
		recorder.stop()
		transcriber.stop()
		slide_text = ""
		transcription = ""
		clear_queue(recording_queue)
		clear_queue(transcription_queue)
	else:
		recorder.start()
		transcriber.start()
		while not transcription_queue.empty():
			if transcription.endswith("..."):
				transcription = transcription[:-3]
			transcription += " " + transcription_queue.get().lower()
			logger.debug(f"Transcription: {transcription}")
		if not slide_text:
		    ocr_result = reader.readtext(img)
		    slide_text = " ".join([elem[1] for elem in ocr_result]).lower()
		    logger.debug(f"Slide text: {slide_text}")
		if slide_text and transcription:
			lcs_length, lcs_result = lcs_1gram(slide_text.split(), transcription.split(), 3)
			rouge_1gram = len(" ".join(lcs_result)) / len(slide_text)
			lcs_length, lcs_result = lcs(slide_text, transcription)
			rouge_l = lcs_length / len(slide_text)
			rouge_score = rouge_1gram_weight * rouge_1gram + rouge_l_weight * rouge_l
		else:
			rouge_score = 0
		logger.debug(f"rouge_score: {rouge_score}")
		if rouge_score >= rouge_threshold:
			logger.info("Rouge score crosses threshold.")
			time.sleep(transition_back_delay)
			switch_to_cam()
			time.sleep(onchange_delay_dur)


	time.sleep(delay_dur)


ws.disconnect()
cam.release()
cv2.destroyAllWindows()
