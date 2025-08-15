import logging
import time
import queue
import cv2
import easyocr
import pylcs
from recorder import Recorder
from transcriber import Transcriber


logging.basicConfig(
	format='%(asctime)s %(levelname)-8s %(message)s',
	level=logging.DEBUG,
	datefmt='%Y-%m-%d %H:%M:%S'
)

def is_ppt():
    return True


def clear_queue(queue):
    while not queue.empty():
        queue.get()


def main():
    cam = cv2.VideoCapture(3)
    reader = easyocr.Reader(["id", "en"])
    recording_queue = queue.Queue()
    transcription_queue = queue.Queue()
    recorder = Recorder(1, recording_queue)
    transcriber = Transcriber(recording_queue, transcription_queue)
    slide_text = ""
    transcription = ""

    while True:
        if not is_ppt():
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
                transcription += " " + transcription_queue.get()
            if not slide_text:
                retval, img = cam.read()
                if retval:
                    ocr_result = reader.readtext(img)
                    slide_text = " ".join([elem[1] for elem in ocr_result])

            lcs_length = pylcs.lcs_sequence_length(transcription, slide_text)
            if not slide_text:
                continue
            lcs_ratio = lcs_length / len(slide_text)
            logging.info(f"lcs_ratio: {lcs_ratio}")
            logging.info(f"slide_text: {slide_text}")
            logging.info(f"transcription: {transcription}")

        time.sleep(1)


if __name__ == "__main__":
    main()
