import cv2
import easyocr


cam = cv2.VideoCapture(3)
reader = easyocr.Reader(['id','en'])

while True:
    retval, img = cam.read()
    if not retval:
        result = reader.readtext(img)
        for (bbox, text, prob) in result:
            print(f'Text: {text}, Probability: {prob}')
    else:
        print(f"retval={retval}")
