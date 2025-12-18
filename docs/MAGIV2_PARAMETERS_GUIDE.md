# Hướng dẫn Tham số Magiv2 Model

## 📋 Tổng quan các hàm chính

### 1. `predict_detections_and_associations()`
Hàm chính để detect và liên kết các objects trong ảnh manga.

**Tham số có thể điều chỉnh:**

| Tham số | Mặc định | Mô tả | Gợi ý điều chỉnh |
|---------|----------|-------|-----------------|
| `character_detection_threshold` | 0.3 | Ngưỡng để giữ lại character detections | **Tăng** (0.4-0.6): ít false positives<br>**Giảm** (0.2-0.25): nhiều detections hơn |
| `panel_detection_threshold` | 0.2 | Ngưỡng để giữ lại panel detections | **Tăng** (0.3-0.4): chỉ giữ panels chắc chắn<br>**Giảm** (0.1-0.15): giữ nhiều panels hơn |
| `text_detection_threshold` | 0.3 | Ngưỡng để giữ lại text detections | **Tăng** (0.4-0.5): chỉ text rõ ràng<br>**Giảm** (0.2-0.25): giữ nhiều text hơn |
| `tail_detection_threshold` | 0.34 | Ngưỡng để giữ lại tail (speech bubble tail) detections | **Tăng** (0.4-0.5): chỉ tails rõ ràng<br>**Giảm** (0.25-0.3): giữ nhiều tails hơn |
| `character_character_matching_threshold` | 0.65 | Ngưỡng để match 2 characters là cùng 1 người | **Tăng** (0.7-0.8): strict matching<br>**Giảm** (0.5-0.6): loose matching |
| `text_character_matching_threshold` | 0.35 | Ngưỡng để match text với character | **Tăng** (0.4-0.5): strict association<br>**Giảm** (0.25-0.3): loose association |
| `text_tail_matching_threshold` | 0.3 | Ngưỡng để match text với tail | **Tăng** (0.4-0.5): strict matching<br>**Giảm** (0.2-0.25): loose matching |
| `text_classification_threshold` | 0.5 | Ngưỡng để phân loại text là dialogue | **Tăng** (0.6-0.7): chỉ dialogue chắc chắn<br>**Giảm** (0.4-0.45): giữ nhiều dialogue hơn |

**Kết quả trả về:**
- `panels`: List các bounding boxes của panels
- `texts`: List các bounding boxes của text boxes
- `characters`: List các bounding boxes của characters
- `tails`: List các bounding boxes của tails
- `text_character_associations`: Các cặp (text_idx, character_idx)
- `text_tail_associations`: Các cặp (text_idx, tail_idx)
- `character_cluster_labels`: Labels cho character clustering
- `is_essential_text`: Boolean list cho text có phải dialogue không

---

### 2. `predict_ocr()`
Đọc text từ các bounding boxes đã detect.

**Tham số có thể điều chỉnh:**

| Tham số | Mặc định | Mô tả | Gợi ý điều chỉnh |
|---------|----------|-------|-----------------|
| `batch_size` | 32 | Số lượng crops xử lý cùng lúc | **Tăng** (64-128): nhanh hơn nhưng tốn RAM<br>**Giảm** (16-24): tiết kiệm RAM |
| `max_new_tokens` | 64 | Số token tối đa cho mỗi text | **Tăng** (128-256): đọc text dài hơn<br>**Giảm** (32-48): nhanh hơn, chỉ text ngắn |
| `use_tqdm` | False | Hiển thị progress bar | `True` để theo dõi tiến độ |

**Input:**
- `images`: List các ảnh (numpy arrays)
- `crop_bboxes`: List các list bboxes cho mỗi ảnh

**Output:**
- List các list text strings cho mỗi ảnh

---

### 3. `predict_crop_embeddings()`
Lấy feature embeddings cho các crops (thường dùng cho characters).

**Tham số có thể điều chỉnh:**

| Tham số | Mặc định | Mô tả | Gợi ý điều chỉnh |
|---------|----------|-------|-----------------|
| `mask_ratio` | 0.0 | Tỷ lệ mask (như training) | **0.0**: Không mask (inference)<br>**0.75**: Mask như training |
| `batch_size` | 256 | Số lượng crops xử lý cùng lúc | **Tăng** (512): nhanh hơn<br>**Giảm** (128): tiết kiệm RAM |

**Input:**
- `images`: List các ảnh
- `crop_bboxes`: List các list bboxes

**Output:**
- List các tensors embeddings [num_crops, hidden_size=768]

**Ứng dụng:**
- So sánh similarity giữa characters
- Clustering characters
- Tìm characters tương tự

---

### 4. `do_chapter_wide_prediction()`
Xử lý cả chapter với character name assignment.

**Tham số có thể điều chỉnh:**

| Tham số | Mặc định | Mô tả | Gợi ý điều chỉnh |
|---------|----------|-------|-----------------|
| `eta` | 0.75 | Threshold cho "none of the above" trong character assignment | **Tăng** (0.8-0.9): strict assignment<br>**Giảm** (0.6-0.7): loose assignment |
| `batch_size` | 8 | Batch size cho detection | **Tăng** (16-32): nhanh hơn<br>**Giảm** (4): tiết kiệm RAM |
| `use_tqdm` | False | Hiển thị progress bar | `True` để theo dõi tiến độ |
| `do_ocr` | True | Có chạy OCR hay không | `False` nếu chỉ cần detection |

**Input:**
- `pages_in_order`: List các ảnh theo thứ tự
- `character_bank`: Dict với format:
  ```python
  {
      "images": [list of character images],
      "names": [list of character names]
  }
  ```

**Output:**
- List các results với thêm:
  - `character_names`: Tên đã assign cho mỗi character
  - `ocr`: OCR results cho mỗi text box

---

### 5. `assign_names_to_characters()`
Gán tên cho characters dựa trên character bank và embeddings.

**Tham số có thể điều chỉnh:**

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `eta` | 0.75 | Threshold cho "none of the above" |

**Input:**
- `images`: List các ảnh
- `character_bboxes`: List các list character bboxes
- `character_bank`: Dict với images và names
- `character_clusters`: Cluster labels từ detection

**Output:**
- List các character names đã assign

---

## 🎯 Các kịch bản sử dụng

### Kịch bản 1: Detection nhanh (không OCR)
```python
results = model.predict_detections_and_associations(
    images,
    character_detection_threshold=0.3,
    panel_detection_threshold=0.2,
    text_detection_threshold=0.3,
    # ... các tham số khác
)
# Không chạy OCR để tiết kiệm thời gian
```

### Kịch bản 2: Detection + OCR đầy đủ
```python
# Bước 1: Detection
results = model.predict_detections_and_associations(images)

# Bước 2: OCR
text_bboxes = [r["texts"] for r in results]
ocr_results = model.predict_ocr(
    images, 
    text_bboxes,
    batch_size=32,
    max_new_tokens=128,  # Cho text dài hơn
    use_tqdm=True
)

# Gán OCR vào results
for i, ocr_texts in enumerate(ocr_results):
    results[i]["ocr"] = ocr_texts
```

### Kịch bản 3: Chapter-wide với Character Bank
```python
character_bank = {
    "images": [char_img1, char_img2, ...],
    "names": ["Character A", "Character B", ...]
}

results = model.do_chapter_wide_prediction(
    images,
    character_bank,
    eta=0.75,
    batch_size=8,
    do_ocr=True,
    use_tqdm=True
)
```

### Kịch bản 4: Tối ưu cho ảnh có nhiều text nhỏ
```python
results = model.predict_detections_and_associations(
    images,
    text_detection_threshold=0.2,  # Giảm để detect text nhỏ
    text_character_matching_threshold=0.25,  # Loose matching
    text_classification_threshold=0.4,  # Giữ nhiều dialogue hơn
)
```

### Kịch bản 5: Tối ưu cho ảnh có nhiều characters
```python
results = model.predict_detections_and_associations(
    images,
    character_detection_threshold=0.25,  # Giảm để detect nhiều hơn
    character_character_matching_threshold=0.6,  # Moderate matching
)

# Lấy embeddings để phân tích
character_bboxes = [r["characters"] for r in results]
embeddings = model.predict_crop_embeddings(
    images,
    character_bboxes,
    batch_size=256
)
```

---

## ⚙️ Tuning Tips

### Khi nào tăng thresholds?
- ✅ Khi có quá nhiều false positives
- ✅ Khi muốn chỉ giữ detections chắc chắn
- ✅ Khi ảnh có chất lượng tốt, rõ ràng

### Khi nào giảm thresholds?
- ✅ Khi thiếu detections (false negatives)
- ✅ Khi ảnh có text/characters nhỏ
- ✅ Khi ảnh có chất lượng thấp

### Tối ưu performance:
- **RAM hạn chế**: Giảm `batch_size` cho OCR và embeddings
- **Cần tốc độ**: Tăng `batch_size`, giảm `max_new_tokens`
- **Cần độ chính xác**: Điều chỉnh thresholds cẩn thận, tăng `max_new_tokens`

---

## 📊 Output Format

Mỗi result trong list results có format:
```python
{
    "panels": [[x1, y1, x2, y2], ...],  # Bounding boxes
    "texts": [[x1, y1, x2, y2], ...],
    "characters": [[x1, y1, x2, y2], ...],
    "tails": [[x1, y1, x2, y2], ...],
    "text_character_associations": [[text_idx, char_idx], ...],
    "text_tail_associations": [[text_idx, tail_idx], ...],
    "character_cluster_labels": [0, 1, 0, ...],  # Cluster IDs
    "is_essential_text": [True, False, ...],  # Dialogue flags
    "ocr": ["text1", "text2", ...],  # Nếu có OCR
    "character_names": ["Name1", "Name2", ...]  # Nếu có character bank
}
```

