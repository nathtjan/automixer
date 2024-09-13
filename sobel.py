import numpy as np
import cv2


SOBEL_X = np.array([
	[-1, 0, 1],
	[-2, 0, 2],
	[-1, 0, 1]
])

SOBEL_Y = np.array([
	[-1, -2, -1],
	[0, 0, 0],
	[1, 2, 1]
])


def sobel_edge(img, threshold=None):
	img = img.astype(np.int16)
	edge_x = cv2.filter2D(
		src=img,
		ddepth=-1,
		kernel=SOBEL_X
	).astype(np.int32)
	edge_y = cv2.filter2D(
		src=img,
		ddepth=-1,
		kernel=SOBEL_Y
	).astype(np.int32)
	
	edge = edge_x**2 + edge_y**2
	if threshold is not None:
		edge = np.where(edge > threshold**2, 255, 0)
	else:
		edge = np.sqrt(edge)
	
	return edge.astype(np.uint8)
