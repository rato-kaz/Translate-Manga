from transformers import AutoModel
import numpy as np
from PIL import Image
import torch
import os
import time
import json
from sklearn.metrics.pairwise import cosine_similarity

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

# ============================================================================
# 1. DETECTION VÀ ASSOCIATION (như code cũ)
# ============================================================================
print("=" * 60)
print("1. DETECTION VÀ ASSOCIATION")
print("=" * 60)
start_time = time.time()
with torch.no_grad():
    results = model.predict_detections_and_associations(
        images,
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
print(f"Thời gian detection: {end_time - start_time:.2f} giây")

# ============================================================================
# 2. OCR - ĐỌC TEXT TỪ CÁC BBOX
# ============================================================================
print("\n" + "=" * 60)
print("2. OCR - ĐỌC TEXT")
print("=" * 60)
start_time = time.time()
with torch.no_grad():
    # Lấy text bboxes từ kết quả detection
    text_bboxes = [result["texts"] for result in results]
    
    # Chạy OCR với các tham số tùy chỉnh
    ocr_results = model.predict_ocr(
        images,
        text_bboxes,
        batch_size=32,          # Batch size cho OCR (mặc định: 32)
        max_new_tokens=64,       # Số token tối đa (mặc định: 64)
        use_tqdm=True            # Hiển thị progress bar
    )
    
    # Gán OCR results vào kết quả
    for i, ocr_texts in enumerate(ocr_results):
        results[i]["ocr"] = ocr_texts
        print(f"Image {i}: Tìm thấy {len(ocr_texts)} text boxes")
        for j, text in enumerate(ocr_texts[:3]):  # In 3 text đầu tiên
            print(f"  Text {j+1}: {text}")

end_time = time.time()
print(f"Thời gian OCR: {end_time - start_time:.2f} giây")

# ============================================================================
# 3. CROP EMBEDDINGS - LẤY FEATURES CHO CHARACTERS
# ============================================================================
print("\n" + "=" * 60)
print("3. CROP EMBEDDINGS - CHARACTER FEATURES")
print("=" * 60)
start_time = time.time()
with torch.no_grad():
    # Lấy character bboxes
    character_bboxes = [result["characters"] for result in results]
    
    # Lấy embeddings với các tham số tùy chỉnh
    embeddings = model.predict_crop_embeddings(
        images,
        character_bboxes,
        mask_ratio=0.0,          # 0.0 = không mask (mặc định), 0.75 = mask như training
        batch_size=256           # Batch size cho embeddings (mặc định: 256)
    )
    
    # Embeddings là list của tensors, mỗi tensor có shape [num_characters, hidden_size]
    for i, emb in enumerate(embeddings):
        if emb.shape[0] > 0:
            print(f"Image {i}: {emb.shape[0]} characters, embedding dim: {emb.shape[1]}")
            # Có thể dùng embeddings này để:
            # - So sánh similarity giữa characters
            # - Clustering characters
            # - Tìm characters tương tự

end_time = time.time()
print(f"Thời gian embeddings: {end_time - start_time:.2f} giây")

# ============================================================================
# 4. CHAPTER-WIDE PREDICTION - XỬ LÝ CẢ CHAPTER VỚI CHARACTER BANK
# ============================================================================
print("\n" + "=" * 60)
print("4. CHAPTER-WIDE PREDICTION (với Character Bank)")
print("=" * 60)

# Tạo character bank (danh sách characters đã biết)
# Format: {"images": [list of images], "names": [list of names]}
character_bank = {
    "images": [],  # Thêm các ảnh characters đã biết ở đây
    "names": []    # Thêm tên tương ứng
}

# Ví dụ: nếu có character bank
if len(character_bank["images"]) > 0:
    start_time = time.time()
    with torch.no_grad():
        chapter_results = model.do_chapter_wide_prediction(
            images,
            character_bank,
            eta=0.75,              # Threshold cho "none of the above" (mặc định: 0.75)
            batch_size=8,           # Batch size cho detection (mặc định: 8)
            use_tqdm=True,          # Hiển thị progress bar
            do_ocr=True             # Có chạy OCR hay không
        )
    
    # Kết quả sẽ có thêm "character_names" và "ocr"
    for i, result in enumerate(chapter_results):
        print(f"\nImage {i}:")
        print(f"  Characters: {len(result.get('characters', []))}")
        print(f"  Character names: {result.get('character_names', [])}")
        print(f"  Texts: {len(result.get('texts', []))}")
        print(f"  OCR results: {len(result.get('ocr', []))}")
    
    end_time = time.time()
    print(f"\nThời gian chapter-wide: {end_time - start_time:.2f} giây")
else:
    print("Chưa có character bank. Bỏ qua chapter-wide prediction.")

# ============================================================================
# 5. ĐIỀU CHỈNH THAM SỐ DETECTION - TỐI ƯU CHO TỪNG LOẠI ẢNH
# ============================================================================
print("\n" + "=" * 60)
print("5. THỬ CÁC THAM SỐ KHÁC NHAU")
print("=" * 60)

# Thử với thresholds cao hơn (ít false positives, nhiều false negatives)
print("\n5a. Strict thresholds (cao hơn):")
with torch.no_grad():
    strict_results = model.predict_detections_and_associations(
        images[:2],  # Chỉ test 2 ảnh đầu
        character_detection_threshold=0.5,      # Tăng từ 0.3 -> 0.5
        panel_detection_threshold=0.4,         # Tăng từ 0.2 -> 0.4
        text_detection_threshold=0.5,           # Tăng từ 0.3 -> 0.5
        tail_detection_threshold=0.5,          # Tăng từ 0.34 -> 0.5
        character_character_matching_threshold=0.7,  # Tăng từ 0.5 -> 0.7
        text_character_matching_threshold=0.5,       # Tăng từ 0.35 -> 0.5
        text_tail_matching_threshold=0.5,             # Tăng từ 0.3 -> 0.5
        text_classification_threshold=0.6,           # Tăng từ 0.5 -> 0.6
    )
    for i, result in enumerate(strict_results):
        print(f"  Image {i}: {len(result.get('characters', []))} chars, "
              f"{len(result.get('texts', []))} texts")

# Thử với thresholds thấp hơn (nhiều detections hơn)
print("\n5b. Loose thresholds (thấp hơn):")
with torch.no_grad():
    loose_results = model.predict_detections_and_associations(
        images[:2],
        character_detection_threshold=0.2,      # Giảm từ 0.3 -> 0.2
        panel_detection_threshold=0.1,         # Giảm từ 0.2 -> 0.1
        text_detection_threshold=0.2,          # Giảm từ 0.3 -> 0.2
        tail_detection_threshold=0.25,         # Giảm từ 0.34 -> 0.25
        character_character_matching_threshold=0.4,  # Giảm từ 0.5 -> 0.4
        text_character_matching_threshold=0.25,      # Giảm từ 0.35 -> 0.25
        text_tail_matching_threshold=0.2,            # Giảm từ 0.3 -> 0.2
        text_classification_threshold=0.4,           # Giảm từ 0.5 -> 0.4
    )
    for i, result in enumerate(loose_results):
        print(f"  Image {i}: {len(result.get('characters', []))} chars, "
              f"{len(result.get('texts', []))} texts")

# ============================================================================
# 6. LƯU KẾT QUẢ RA FILE JSON
# ============================================================================
print("\n" + "=" * 60)
print("6. LƯU KẾT QUẢ")
print("=" * 60)

# Chuyển đổi kết quả sang format có thể serialize
def convert_results_to_json(results):
    json_results = []
    for result in results:
        json_result = {
            "panels": result.get("panels", []),
            "texts": result.get("texts", []),
            "characters": result.get("characters", []),
            "tails": result.get("tails", []),
            "text_character_associations": result.get("text_character_associations", []),
            "text_tail_associations": result.get("text_tail_associations", []),
            "character_cluster_labels": result.get("character_cluster_labels", []),
            "is_essential_text": result.get("is_essential_text", []),
            "ocr": result.get("ocr", []),
            "character_names": result.get("character_names", []),
        }
        json_results.append(json_result)
    return json_results

json_results = convert_results_to_json(results)
with open("detection_results.json", "w", encoding="utf-8") as f:
    json.dump(json_results, f, indent=2, ensure_ascii=False)
print("Đã lưu kết quả vào detection_results.json")

# ============================================================================
# 7. TẠM THỜI SET CHARACTER NAMES (sẽ được reassign sau clustering)
# ============================================================================
# Tạm thời set character names để các phần sau không bị lỗi
for i in range(len(images)):
    if isinstance(results[i], dict) and "character_names" not in results[i]:
        num_chars = len(results[i].get("characters", []))
        # Dùng Character_0, Character_1, ... thay vì "Other"
        results[i]["character_names"] = [f"Character_{j}" for j in range(num_chars)]

# ============================================================================
# 8. THỐNG KÊ KẾT QUẢ
# ============================================================================
print("\n" + "=" * 60)
print("8. THỐNG KÊ")
print("=" * 60)

total_chars = sum(len(r.get("characters", [])) for r in results)
total_texts = sum(len(r.get("texts", [])) for r in results)
total_panels = sum(len(r.get("panels", [])) for r in results)
total_tails = sum(len(r.get("tails", [])) for r in results)
total_ocr = sum(len(r.get("ocr", [])) for r in results)

print(f"Tổng số images: {len(images)}")
print(f"Tổng số characters: {total_chars} (trung bình: {total_chars/len(images):.1f}/image)")
print(f"Tổng số texts: {total_texts} (trung bình: {total_texts/len(images):.1f}/image)")
print(f"Tổng số panels: {total_panels} (trung bình: {total_panels/len(images):.1f}/image)")
print(f"Tổng số tails: {total_tails} (trung bình: {total_tails/len(images):.1f}/image)")
print(f"Tổng số OCR texts: {total_ocr}")

# Đếm text-character associations
total_associations = sum(len(r.get("text_character_associations", [])) for r in results)
print(f"Tổng số text-character associations: {total_associations}")

# Đếm essential texts (dialogue)
total_essential = sum(sum(r.get("is_essential_text", [])) for r in results)
print(f"Tổng số essential texts (dialogue): {total_essential}")

# ============================================================================
# 9. CROSS-PAGE CHARACTER CLUSTERING - NHÓM CHARACTERS GIỐNG NHAU QUA CÁC PAGES
# ============================================================================
print("\n" + "=" * 60)
print("9. CROSS-PAGE CHARACTER CLUSTERING")
print("=" * 60)

def cluster_characters_across_pages(results, images, model, similarity_threshold=0.7):
    """
    Nhóm characters giống nhau qua các pages dựa trên embeddings.
    
    Args:
        results: List kết quả detection cho mỗi page
        images: List các images
        model: Magiv2Model
        similarity_threshold: Ngưỡng similarity để coi là cùng 1 character (0.0-1.0)
    
    Returns:
        List character names đã được reassign cho mỗi page
    """
    print(f"Đang lấy embeddings cho tất cả characters...")
    
    # Lấy character bboxes từ tất cả pages
    all_character_bboxes = [result.get("characters", []) for result in results]
    
    # Lấy embeddings cho tất cả characters
    with torch.no_grad():
        all_embeddings = model.predict_crop_embeddings(
            images,
            all_character_bboxes,
            mask_ratio=0.0,
            batch_size=256
        )
    
    # Gộp tất cả embeddings lại với metadata (page_idx, char_idx)
    character_metadata = []  # [(page_idx, char_idx, embedding), ...]
    for page_idx, embeddings in enumerate(all_embeddings):
        for char_idx in range(embeddings.shape[0]):
            embedding = embeddings[char_idx].cpu().numpy()
            character_metadata.append({
                "page_idx": page_idx,
                "char_idx": char_idx,
                "embedding": embedding
            })
    
    if len(character_metadata) == 0:
        print("  Không có characters nào để cluster.")
        return [["Character_0"] * len(result.get("characters", [])) for result in results]
    
    print(f"  Tổng số characters: {len(character_metadata)}")
    
    # Normalize embeddings
    embeddings_matrix = np.array([char["embedding"] for char in character_metadata])
    # Normalize để tính cosine similarity
    embeddings_matrix = embeddings_matrix / (np.linalg.norm(embeddings_matrix, axis=1, keepdims=True) + 1e-8)
    
    # Tính similarity matrix
    print(f"  Đang tính similarity matrix...")
    similarity_matrix = cosine_similarity(embeddings_matrix)
    
    # Clustering: dùng Union-Find hoặc simple greedy clustering
    # Mỗi character ban đầu là 1 cluster
    clusters = {}  # cluster_id -> list of (page_idx, char_idx)
    cluster_id_counter = 0
    
    # Greedy clustering: với mỗi character, tìm cluster có similarity cao nhất
    assigned_clusters = {}  # (page_idx, char_idx) -> cluster_id
    
    for i, char_meta in enumerate(character_metadata):
        page_idx = char_meta["page_idx"]
        char_idx = char_meta["char_idx"]
        key = (page_idx, char_idx)
        
        # Tìm cluster tốt nhất (similarity cao nhất)
        best_cluster_id = None
        best_similarity = -1
        
        for cluster_id, cluster_chars in clusters.items():
            # Tính average similarity với tất cả characters trong cluster
            similarities = []
            for other_page_idx, other_char_idx in cluster_chars:
                other_i = next(j for j, cm in enumerate(character_metadata) 
                              if cm["page_idx"] == other_page_idx and cm["char_idx"] == other_char_idx)
                similarities.append(similarity_matrix[i, other_i])
            
            avg_similarity = np.mean(similarities) if similarities else 0
            
            if avg_similarity >= similarity_threshold and avg_similarity > best_similarity:
                best_similarity = avg_similarity
                best_cluster_id = cluster_id
        
        # Nếu tìm thấy cluster phù hợp, thêm vào
        if best_cluster_id is not None:
            clusters[best_cluster_id].append((page_idx, char_idx))
            assigned_clusters[key] = best_cluster_id
        else:
            # Tạo cluster mới
            new_cluster_id = cluster_id_counter
            cluster_id_counter += 1
            clusters[new_cluster_id] = [(page_idx, char_idx)]
            assigned_clusters[key] = new_cluster_id
    
    print(f"  Tìm thấy {len(clusters)} character clusters")
    
    # Đặt tên cho các clusters: Character_0, Character_1, ...
    cluster_names = {}
    for cluster_id in sorted(clusters.keys()):
        cluster_names[cluster_id] = f"Character_{cluster_id}"
    
    # Tạo character names mới cho mỗi page
    new_character_names = []
    for page_idx, result in enumerate(results):
        num_chars = len(result.get("characters", []))
        page_names = []
        for char_idx in range(num_chars):
            key = (page_idx, char_idx)
            if key in assigned_clusters:
                cluster_id = assigned_clusters[key]
                page_names.append(cluster_names[cluster_id])
            else:
                # Fallback
                page_names.append(f"Character_{char_idx}")
        new_character_names.append(page_names)
    
    # Thống kê
    cluster_sizes = {cluster_id: len(chars) for cluster_id, chars in clusters.items()}
    print(f"\n  Thống kê clusters:")
    for cluster_id in sorted(cluster_sizes.keys()):
        size = cluster_sizes[cluster_id]
        name = cluster_names[cluster_id]
        pages = set(page_idx for page_idx, _ in clusters[cluster_id])
        print(f"    {name}: {size} instances across {len(pages)} pages")
    
    return new_character_names

# Thực hiện clustering
print("Đang cluster characters qua các pages...")
new_character_names = cluster_characters_across_pages(
    results, 
    images, 
    model, 
    similarity_threshold=0.7  # Có thể điều chỉnh: 0.6-0.8
)

# Cập nhật character_names trong results
for page_idx, names in enumerate(new_character_names):
    results[page_idx]["character_names"] = names
    print(f"  Page {page_idx}: {len(names)} characters -> {len(set(names))} unique characters")

# ============================================================================
# 9b. VISUALIZATION VỚI CHARACTER NAMES ĐÃ ĐƯỢC CLUSTER
# ============================================================================
print("\n" + "=" * 60)
print("9b. VISUALIZATION (với character names đã cluster)")
print("=" * 60)

for i in range(len(images)):
    # Visualize với character names đã được reassign qua clustering
    model.visualise_single_image_prediction(
        images[i], 
        results[i], 
        filename=f"image_{i}_with_clustered_names.png"
    )
    print(f"Đã lưu visualization: image_{i}_with_clustered_names.png")

# ============================================================================
# 10. MAP TEXT VỚI CHARACTER - BIẾT CHARACTER NÀO NÓI TEXT NÀO
# ============================================================================
print("\n" + "=" * 60)
print("10. TEXT-CHARACTER MAPPING")
print("=" * 60)

def map_text_to_character(results):
    """
    Map mỗi text với character đã nói text đó.
    Trả về list các dict cho mỗi image.
    """
    text_character_mappings = []
    
    for img_idx, result in enumerate(results):
        # Lấy các dữ liệu cần thiết
        ocr_texts = result.get("ocr", [])
        text_character_associations = result.get("text_character_associations", [])
        character_names = result.get("character_names", [])
        characters = result.get("characters", [])
        is_essential_text = result.get("is_essential_text", [])
        
        # Tạo mapping: character_idx -> list of (text_idx, text)
        character_texts = {}
        for text_idx, char_idx in text_character_associations:
            if char_idx not in character_texts:
                character_texts[char_idx] = []
            
            # Lấy text từ OCR nếu có
            text_content = ""
            if text_idx < len(ocr_texts):
                text_content = ocr_texts[text_idx]
            else:
                text_content = f"[Text {text_idx} - No OCR]"
            
            # Kiểm tra có phải essential text không
            is_dialogue = False
            if text_idx < len(is_essential_text):
                is_dialogue = is_essential_text[text_idx]
            
            character_texts[char_idx].append({
                "text_idx": int(text_idx),
                "text": text_content,
                "is_dialogue": bool(is_dialogue)
            })
        
        # Tạo danh sách dialogues cho image này
        dialogues = []
        for char_idx, texts in character_texts.items():
            # Lấy character name
            # Ưu tiên: character_names -> Character_{idx} nếu là "Other" -> Character_{idx} nếu không có
            char_name = f"Character_{char_idx}"
            if char_idx < len(character_names):
                char_name = character_names[char_idx]
                # Nếu là "Other", dùng Character_{idx} thay vì
                if char_name == "Other":
                    char_name = f"Character_{char_idx}"
            
            # Lấy character bbox
            char_bbox = None
            if char_idx < len(characters):
                char_bbox = characters[char_idx]
            
            # Thêm tất cả texts của character này
            for text_info in texts:
                dialogues.append({
                    "character_idx": int(char_idx),
                    "character_name": char_name,
                    "character_bbox": char_bbox,
                    "text_idx": text_info["text_idx"],
                    "text": text_info["text"],
                    "is_dialogue": text_info["is_dialogue"]
                })
        
        # Sắp xếp theo text_idx để giữ thứ tự
        dialogues.sort(key=lambda x: x["text_idx"])
        
        text_character_mappings.append({
            "image_idx": img_idx,
            "total_characters": len(characters),
            "total_texts": len(ocr_texts),
            "total_associations": len(text_character_associations),
            "dialogues": dialogues
        })
    
    return text_character_mappings

# Tạo mapping
text_character_mappings = map_text_to_character(results)

# Hiển thị kết quả
for mapping in text_character_mappings:
    img_idx = mapping["image_idx"]
    dialogues = mapping["dialogues"]
    
    print(f"\n--- Image {img_idx} ---")
    print(f"Tổng: {mapping['total_characters']} characters, "
          f"{mapping['total_texts']} texts, "
          f"{mapping['total_associations']} associations")
    
    if len(dialogues) == 0:
        print("  Không có text nào được map với character.")
    else:
        print(f"\n  Dialogues ({len(dialogues)}):")
        for i, dialogue in enumerate(dialogues, 1):
            char_name = dialogue["character_name"]
            text = dialogue["text"]
            is_dialogue = "✓" if dialogue["is_dialogue"] else "✗"
            print(f"    {i}. [{char_name}] {is_dialogue} \"{text}\"")

# Lưu mapping vào file JSON
mapping_output = {
    "summary": {
        "total_images": len(text_character_mappings),
        "total_dialogues": sum(len(m["dialogues"]) for m in text_character_mappings)
    },
    "mappings": text_character_mappings
}

with open("text_character_mapping.json", "w", encoding="utf-8") as f:
    json.dump(mapping_output, f, indent=2, ensure_ascii=False)
print(f"\n✓ Đã lưu text-character mapping vào text_character_mapping.json")

# ============================================================================
# 11. TẠO DIALOGUE LIST THEO THỨ TỰ ĐỌC (CHO MỖI IMAGE)
# ============================================================================
print("\n" + "=" * 60)
print("11. DIALOGUE LIST THEO THỨ TỰ")
print("=" * 60)

def create_dialogue_list(mappings):
    """
    Tạo danh sách dialogues theo thứ tự đọc, nhóm theo character.
    """
    all_dialogues = []
    
    for mapping in mappings:
        img_idx = mapping["image_idx"]
        dialogues = mapping["dialogues"]
        
        # Nhóm dialogues theo character
        char_dialogues = {}
        for dialogue in dialogues:
            char_name = dialogue["character_name"]
            if char_name not in char_dialogues:
                char_dialogues[char_name] = []
            char_dialogues[char_name].append(dialogue["text"])
        
        # Tạo format dễ đọc
        image_dialogues = {
            "image_idx": img_idx,
            "dialogues_by_character": char_dialogues,
            "dialogue_list": [
                {
                    "character": d["character_name"],
                    "text": d["text"],
                    "is_dialogue": d["is_dialogue"]
                }
                for d in dialogues
            ]
        }
        all_dialogues.append(image_dialogues)
    
    return all_dialogues

dialogue_lists = create_dialogue_list(text_character_mappings)

# Hiển thị
for img_dialogues in dialogue_lists:
    img_idx = img_dialogues["image_idx"]
    print(f"\n--- Image {img_idx} - Dialogues theo thứ tự ---")
    
    for dialogue_item in img_dialogues["dialogue_list"]:
        char = dialogue_item["character"]
        text = dialogue_item["text"]
        marker = "[DIALOGUE]" if dialogue_item["is_dialogue"] else "[TEXT]"
        print(f"  {marker} {char}: {text}")

# Lưu dialogue list
with open("dialogue_list.json", "w", encoding="utf-8") as f:
    json.dump(dialogue_lists, f, indent=2, ensure_ascii=False)
print(f"\n✓ Đã lưu dialogue list vào dialogue_list.json")

# ============================================================================
# 12. THỐNG KÊ THEO CHARACTER
# ============================================================================
print("\n" + "=" * 60)
print("12. THỐNG KÊ THEO CHARACTER")
print("=" * 60)

# Đếm số lượng text mỗi character nói
character_stats = {}
for mapping in text_character_mappings:
    for dialogue in mapping["dialogues"]:
        char_name = dialogue["character_name"]
        if char_name not in character_stats:
            character_stats[char_name] = {
                "total_texts": 0,
                "dialogue_texts": 0,
                "other_texts": 0
            }
        character_stats[char_name]["total_texts"] += 1
        if dialogue["is_dialogue"]:
            character_stats[char_name]["dialogue_texts"] += 1
        else:
            character_stats[char_name]["other_texts"] += 1

# Sắp xếp theo số lượng text
sorted_chars = sorted(character_stats.items(), 
                     key=lambda x: x[1]["total_texts"], 
                     reverse=True)

print("\nSố lượng text mỗi character:")
for char_name, stats in sorted_chars:
    print(f"  {char_name}:")
    print(f"    - Tổng: {stats['total_texts']} texts")
    print(f"    - Dialogues: {stats['dialogue_texts']}")
    print(f"    - Other: {stats['other_texts']}")

# Lưu stats
with open("character_stats.json", "w", encoding="utf-8") as f:
    json.dump(character_stats, f, indent=2, ensure_ascii=False)
print(f"\n✓ Đã lưu character stats vào character_stats.json")

print("\n" + "=" * 60)
print("HOÀN THÀNH!")
print("=" * 60)

