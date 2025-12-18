from manga_ocr import MangaOcr
import time
mocr = MangaOcr()
start_time = time.time()
text = mocr('yolo_detection_atxs52s7fnv21_1.jpg')
end_time = time.time()
print(f"Thời gian chạy: {end_time - start_time} giây")
print(text)