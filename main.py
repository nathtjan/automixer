import time
import numpy as np
import cv2
from obswebsocket import requests
from obsclient import ws
from sobel import sobel_edge


ws.connect()


PPT_scenenames = ["FULL PPT", "KHOTBAH MODE 1", "KHOTBAH MODE 2"]
default_PPT_scenename = PPT_scenenames[0]


def switch_to_PPT():
	curr_preview = ws.call(requests.GetCurrentPreviewScene()).getSceneName()
	curr_program = ws.call(requests.GetCurrentProgramScene()).getSceneName()
	if curr_program in PPT_scenenames:
		print("Program scene unchanged since current is", curr_program)
		return
	if curr_preview in PPT_scenenames:
		sceneName = curr_preview
	else:
		sceneName = default_PPT_scenename

	ws.call(requests.SetCurrentProgramScene(sceneName=sceneName))
	print("Switched program scene to " + sceneName)


delay_dur = 0.2
edge_threshold = 20
diff_threshold = 5
cam = cv2.VideoCapture(3)
img_before = None


def onchange():
	print("Change detected!")
	switch_to_PPT()


print("AUTOMIXER v1")
print("Running...")
while True:
	retval, img = cam.read()
	if not retval:
		continue

	if img_before is not None:
		img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		edge_gray = sobel_edge(img_gray)
		edge = cv2.cvtColor(edge_gray, cv2.COLOR_GRAY2BGR)
		diff = np.abs(
			img.astype(np.int16)
			- img_before.astype(np.int16)
		).astype(np.uint8)
		diff *= edge < edge_threshold
		if np.mean(diff) > diff_threshold:
			onchange()
	img_before = img
	time.sleep(delay_dur)


ws.disconnect()
cam.release()
cv2.destroyAllWindows()