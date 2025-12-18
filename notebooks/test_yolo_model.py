import os
import cv2
import json
from ultralytics import YOLO
import numpy as np
import time

def test_yolo_model():
    """Test YOLO model """
    print("🧪 Testing YOLO Model for Manga Detection")
    print("=" * 60)
    
    # Load YOLO model
    model_path = 'best.pt'
    if not os.path.exists(model_path):
        print(f"❌ Không tìm thấy model: {model_path}")
        return False
    
    try:
        yolo_model = YOLO(model_path)
        print("✅ YOLO model loaded successfully")
        print(f"📁 Model path: {model_path}")
        print()
    except Exception as e:
        print(f"❌ Lỗi khi load model: {e}")
        return False
    
    # Danh sách ảnh test
    test_images = [
        # "06.jpg",
        # "07.jpg",
        "atxs52s7fnv21.jpg"
    ]
    
    all_results = {}
    
    for image_path in test_images:
        if not os.path.exists(image_path):
            print(f"⚠️  Không tìm thấy ảnh: {image_path}")
            continue
            
        print(f"🔍 Testing với ảnh: {image_path}")
        print("-" * 40)
        
        try:
            # Chạy YOLO detection
            results = yolo_model(image_path)
            
            # Xử lý kết quả
            image_results = []
            total_detections = 0
            
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
                    confidences = result.boxes.conf.cpu().numpy()
                    classes = result.boxes.cls.cpu().numpy()
                    
                    total_detections = len(boxes)
                    print(f"📊 Tìm thấy {total_detections} detections:")
                    
                    for i, (box, conf, cls) in enumerate(zip(boxes, confidences, classes)):
                        x1, y1, x2, y2 = box.astype(int)
                        width = x2 - x1
                        height = y2 - y1
                        
                        detection_info = {
                            'id': i + 1,
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': float(conf),
                            'class_id': int(cls),
                            'width': int(width),
                            'height': int(height)
                        }
                        
                        image_results.append(detection_info)
                        
                        print(f"  {i+1:2d}. Bbox: [{x1:4d}, {y1:4d}, {x2:4d}, {y2:4d}] "
                              f"| Conf: {conf:.3f} | Class: {int(cls)} | Size: {width}x{height}")
                else:
                    print("  ⚠️  Không tìm thấy detection nào")
            
            all_results[image_path] = {
                'total_detections': total_detections,
                'detections': image_results
            }
            
            # Tạo ảnh kết quả với bounding box
            if total_detections > 0:
                save_detection_image(image_path, image_results)
            
            print()
            
        except Exception as e:
            print(f"❌ Lỗi khi xử lý ảnh {image_path}: {e}")
            continue
    
    # Lưu kết quả JSON
    save_results_json(all_results)
    
    # In tổng kết
    print_summary(all_results)
    
    return True

def save_detection_image(image_path, detections):
    """Lưu ảnh với bounding box được vẽ"""
    try:
        # Đọc ảnh
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Không thể đọc ảnh: {image_path}")
            return
        
        # Vẽ bounding box cho mỗi detection
        for detection in detections:
            bbox = detection['bbox']
            conf = detection['confidence']
            cls_id = detection['class_id']
            
            x1, y1, x2, y2 = bbox
            
            # Màu sắc khác nhau cho các class khác nhau
            colors = [
                (0, 255, 0),    # Xanh lá
                (255, 0, 0),    # Xanh dương
            ]
            color = colors[cls_id % len(colors)]
            
            # Vẽ bounding box
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # Vẽ label
            label = f"Class {cls_id} ({conf:.2f})"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            
            # Vẽ background cho text
            cv2.rectangle(image, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), color, -1)
            
            # Vẽ text
            cv2.putText(image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Lưu ảnh kết quả
        output_path = f"yolo_detection_{os.path.basename(image_path)}"
        cv2.imwrite(output_path, image)
        print(f"🖼️  Đã lưu ảnh kết quả: {output_path}")
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu ảnh: {e}")

def save_results_json(all_results):
    """Lưu kết quả ra file JSON"""
    try:
        output_file = "yolo_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu kết quả JSON: {output_file}")
    except Exception as e:
        print(f"❌ Lỗi khi lưu JSON: {e}")

def print_summary(all_results):
    """In tổng kết kết quả"""
    print("=" * 60)
    print("📊 TỔNG KẾT KẾT QUẢ")
    print("=" * 60)
    
    total_images = len(all_results)
    total_detections = sum(result['total_detections'] for result in all_results.values())
    
    print(f"🖼️  Tổng số ảnh đã test: {total_images}")
    print(f"🎯 Tổng số detections: {total_detections}")
    print()
    
    for image_path, result in all_results.items():
        detections = result['total_detections']
        print(f"📁 {os.path.basename(image_path)}: {detections} detections")
        
        if detections > 0:
            # Thống kê confidence
            confidences = [d['confidence'] for d in result['detections']]
            avg_conf = np.mean(confidences)
            max_conf = np.max(confidences)
            min_conf = np.min(confidences)
            
            print(f"   📈 Confidence - Avg: {avg_conf:.3f}, Max: {max_conf:.3f}, Min: {min_conf:.3f}")
            
            # Thống kê class
            classes = [d['class_id'] for d in result['detections']]
            unique_classes = list(set(classes))
            print(f"   🏷️  Classes detected: {unique_classes}")
    
    print()
    print("✅ Test hoàn thành!")

if __name__ == "__main__":
    start_time = time.time()
    test_yolo_model()
    end_time = time.time()
    print(f"Thời gian chạy: {end_time - start_time} giây")

