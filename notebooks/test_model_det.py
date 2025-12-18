from transformers import AutoModel
import numpy as np
from PIL import Image
import torch
import os
import time

images = [
        "06.jpg",
        "07.jpg",
        "08.jpg",
        "09.jpg",
        "10.jpg",
        "11.jpg",
    ]

def read_image_as_np_array(image_path):
    with open(image_path, "rb") as file:
        image = Image.open(file).convert("L").convert("RGB")
        image = np.array(image)
    return image

images = [read_image_as_np_array(image) for image in images]

model = AutoModel.from_pretrained("ragavsachdeva/magiv2", trust_remote_code=True).cuda().eval()
start_time = time.time()
with torch.no_grad():
    results = model.predict_detections_and_associations(images,
                                                        character_detection_threshold=0.3,
                                                        panel_detection_threshold=0.2,
                                                        text_detection_threshold=0.3,
                                                        tail_detection_threshold=0.34,
                                                        character_character_matching_threshold=0.5,
                                                        text_character_matching_threshold=0.35,
                                                        text_tail_matching_threshold=0.3,
                                                        text_classification_threshold=0.5,
                                                    )
end_time = time.time()
print(f"Thời gian chạy: {end_time - start_time} giây")
for i in range(len(images)):
    if isinstance(results[i], dict) and "character_names" not in results[i]:
        num_chars = len(results[i].get("characters", []))
        results[i]["character_names"] = ["Other"] * num_chars
    model.visualise_single_image_prediction(images[i], results[i], filename=f"image_{i}.png")