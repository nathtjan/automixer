import logging
import time
import numpy as np
import cv2
from obswebsocket import requests
from obsclient import ws
from sobel import sobel_edge


logging.basicConfig(
	format='%(asctime)s %(levelname)-8s %(message)s',
	level=logging.INFO,
	datefmt='%Y-%m-%d %H:%M:%S'
)

ws.connect()


PPT_scenenames = ["FULL PPT", "KHOTBAH MODE 1", "KHOTBAH MODE 2"]
default_PPT_scenename = PPT_scenenames[0]


def switch_to_PPT():
	curr_preview = ws.call(requests.GetCurrentPreviewScene()).getSceneName()
	curr_program = ws.call(requests.GetCurrentProgramScene()).getSceneName()
	if curr_program in PPT_scenenames:
		logging.info("Program scene unchanged since current is " + curr_program)
		return
	if curr_preview in PPT_scenenames:
		sceneName = curr_preview
	else:
		sceneName = default_PPT_scenename

	ws.call(requests.SetCurrentProgramScene(sceneName=sceneName))
	logging.info("Switched program scene to " + sceneName)


onchange_delay_dur = 2
delay_dur = 0.1
edge_threshold = 20
diff_threshold = 5
full_black_threshold_mean = 36
full_black_threshold_std = 5
cam = cv2.VideoCapture(3)
img_before = None
obs_vcam_default = cv2.imread("obs_vcam_default.png")


def is_full_black(img):
	mean = np.mean(img)
	std = np.std(img)
	return (mean < full_black_threshold_mean
                and std < full_black_threshold_std)


def is_obs_vcam_default(img):
        diff = img - obs_vcam_default
        return (diff.mean() <= 1.0 and diff.std() <= 0.5)


def onchange():
	logging.info("Change detected!")
	switch_to_PPT()
	time.sleep(onchange_delay_dur)


logging.info("AUTOMIXER v1")
logging.info("Running...")
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
	time.sleep(delay_dur)


ws.disconnect()
cam.release()
cv2.destroyAllWindows()
