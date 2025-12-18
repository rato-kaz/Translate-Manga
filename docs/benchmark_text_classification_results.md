# Language Detection Benchmark Results

## Tổng quan

So sánh hiệu năng của 3 phương pháp nhận diện ngôn ngữ:
- **xlm-r**: XLM-RoBERTa based model (papluca/xlm-roberta-base-language-detection)
- **langdetect**: Thư viện nhận diện ngôn ngữ dựa trên thống kê
- **fast-langdetect**: Thư viện nhận diện ngôn ngữ nhanh với nhiều config

---

## 1. Kết quả tổng hợp

### 1.1. Tốc độ xử lý (trung bình)

| Phương pháp | Thời gian trung bình | Ghi chú |
|------------|---------------------|---------|
| **fast-langdetect** | ~0.0s (sau lần đầu) | ⚡ Nhanh nhất |
| **langdetect** | ~0.0-0.01s | ⚡ Rất nhanh |
| **xlm-r** | ~0.05-0.09s | 🐌 Chậm hơn (cần GPU/CPU mạnh) |

**Lưu ý**: Lần đầu tiên mỗi phương pháp có thể chậm hơn do khởi tạo model.

### 1.2. Độ chính xác

| Ngôn ngữ | xlm-r | langdetect | fast-langdetect |
|---------|-------|------------|-----------------|
| Japanese | ✅ 0.74-0.99 | ✅ | ✅ 0.99-1.00 |
| Vietnamese | ✅ 0.96-0.99 | ✅ | ✅ 0.99-1.00 |
| English | ✅ 0.96-0.99 | ✅ | ✅ 0.84-0.99 |
| Chinese | ✅ 0.97-0.99 | ✅ (zh-cn) | ✅ 0.99-1.00 |
| Korean | ⚠️ 0.67 (nhầm ja) | ✅ | ✅ 1.00 |
| French | ✅ 0.99 | ✅ | ✅ 0.99 |
| Spanish | ✅ 0.99 | ✅ | ✅ 1.00 |
| German | ✅ 0.99 | ✅ | ✅ 1.00 |

---

## 2. Chi tiết kết quả theo từng test case

### 2.1. Japanese (Tiếng Nhật)

#### Test 1: "こんにちは！" (Ngắn)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.355s | ja | 0.7423 |
| langdetect | 0.178s | ja | - |
| fast-langdetect | 0.340s | ja | 0.9868 |

#### Test 2: "今日は良い天気ですね。散歩に行きましょう。" (Trung bình)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.063s | ja | 0.9918 |
| langdetect | 0.0s | ja | - |
| fast-langdetect | 0.0s | ja | 0.9999 |

#### Test 3: "この店はコーヒーが美味いんだ。毎日ここに来て、同じ席に座って、同じコーヒーを飲む。それが僕の日課なんだ。" (Dài - Manga dialogue)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.067s | ja | 0.9943 |
| langdetect | 0.016s | ja | - |
| fast-langdetect | 0.0s | ja | 0.9995 |

**Nhận xét**: Cả 3 phương pháp đều nhận diện chính xác tiếng Nhật. fast-langdetect có confidence cao nhất.

---

### 2.2. Vietnamese (Tiếng Việt)

#### Test 1: "Tôi đang đọc manga." (Ngắn)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.041s | vi | 0.9649 |
| langdetect | 0.0s | vi | - |
| fast-langdetect | 0.0s | vi | 0.9999 |

#### Test 2: "Hôm nay trời đẹp quá. Chúng ta nên đi dạo công viên." (Trung bình)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.052s | vi | 0.9936 |
| langdetect | 0.0s | vi | - |
| fast-langdetect | 0.0s | vi | 0.9991 |

#### Test 3: "Dự án dịch manga này thực sự thú vị..." (Dài)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.083s | vi | 0.9946 |
| langdetect | 0.0s | vi | - |
| fast-langdetect | 0.0s | vi | 1.0000 |

**Nhận xét**: Tất cả đều nhận diện chính xác. fast-langdetect đạt confidence tuyệt đối (1.0000) với text dài.

---

### 2.3. English (Tiếng Anh)

#### Test 1: "This is a test." (Ngắn)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.065s | en | 0.9822 |
| langdetect | 0.004s | en | - |
| fast-langdetect | 0.0s | en | 0.9883 |

#### Test 2: "The weather is beautiful today..." (Trung bình)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.063s | en | 0.9929 |
| langdetect | 0.0s | en | - |
| fast-langdetect | 0.0s | en | 0.9811 |

#### Test 3: "Machine learning and natural language processing..." (Dài)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.093s | en | 0.9626 |
| langdetect | 0.004s | en | - |
| fast-langdetect | 0.0s | en | 0.8397 |

**Nhận xét**: Tất cả nhận diện chính xác. fast-langdetect có confidence thấp hơn một chút với text dài về technical.

---

### 2.4. Chinese (Tiếng Trung)

#### Test 1: "这是一个测试。" (Ngắn)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.048s | zh | 0.9742 |
| langdetect | 0.001s | zh-cn | - |
| fast-langdetect | 0.0s | zh | 1.0000 |

#### Test 2: "今天天气真好。我们应该去公园散步。" (Trung bình)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.059s | zh | 0.9916 |
| langdetect | 0.001s | zh-cn | - |
| fast-langdetect | 0.0s | zh | 0.9935 |

#### Test 3: "人工智能和机器学习技术..." (Dài)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.106s | zh | 0.9932 |
| langdetect | 0.002s | zh-cn | - |
| fast-langdetect | 0.001s | zh | 0.9979 |

**Nhận xét**: 
- langdetect trả về `zh-cn` (cụ thể hơn)
- fast-langdetect đạt confidence tuyệt đối với text ngắn

---

### 2.5. Các ngôn ngữ khác

#### Korean: "안녕하세요. 오늘 날씨가 정말 좋네요."
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.072s | ⚠️ ja (0.6705) | ❌ Nhầm |
| langdetect | 0.0s | ko | ✅ |
| fast-langdetect | 0.0s | ko | 1.0000 ✅ |

**Nhận xét**: xlm-r nhầm Korean thành Japanese. fast-langdetect và langdetect nhận diện chính xác.

#### French: "Bonjour! Comment allez-vous aujourd'hui? Le temps est magnifique."
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.058s | fr | 0.9924 |
| langdetect | 0.0003s | fr | - |
| fast-langdetect | 0.0s | fr | 0.9940 |

#### Spanish: "Hola! ¿Cómo estás? El clima está hermoso hoy."
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.054s | es | 0.9928 |
| langdetect | 0.003s | es | - |
| fast-langdetect | 0.0s | es | 0.9966 |

#### German: "Guten Tag! Wie geht es Ihnen? Das Wetter ist heute wunderbar."
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.053s | de | 0.9920 |
| langdetect | 0.002s | de | - |
| fast-langdetect | 0.0s | de | 0.9989 |

---

### 2.6. Mixed Language (Ngôn ngữ hỗn hợp)

#### Test 1: "Hello! こんにちは！This is a mixed text."
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.051s | en | 0.6076 ⚠️ |
| langdetect | 0.002s | en | - |
| fast-langdetect | 0.0s | en | 0.2676 ⚠️ |

**Với config đặc biệt (model='auto', k=3):**
```
Top candidates:
  1. en: 0.2676
  2. ja: 0.1962
  3. te: 0.0425
```
✅ **Phát hiện được cả English và Japanese!**

#### Test 2: "I love 日本語 and learning new languages."
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.049s | en | 0.9932 |
| langdetect | 0.004s | en | - |
| fast-langdetect | 0.0s | en | 0.6412 ⚠️ |

**Với config đặc biệt (model='auto', k=3):**
```
Top candidates:
  1. en: 0.6412
  2. ja: 0.1444
  3. es: 0.0440
```
✅ **Phát hiện được cả English và Japanese!**

#### Test 3: "Bonjour! こんにちは！Hello from multiple languages."
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.043s | en | 0.6790 ⚠️ |
| langdetect | 0.010s | fr | - |
| fast-langdetect | 0.0s | en | 0.4640 ⚠️ |

**Với config đặc biệt (model='auto', k=3):**
```
Top candidates:
  1. en: 0.4640
  2. ja: 0.0491
  3. zh: 0.0408
```
⚠️ **Không phát hiện được French, nhưng có Japanese**

**Nhận xét**: 
- Với text mixed language, confidence thường thấp hơn
- Sử dụng `model='auto'` và `k=3` giúp phát hiện nhiều ngôn ngữ trong cùng text
- fast-langdetect với config đặc biệt là tốt nhất cho mixed language

---

### 2.7. Edge Cases (Trường hợp đặc biệt)

#### Test 1: "Hi" (Rất ngắn)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.025s | sw (0.3741) | ⚠️ Không chắc chắn |
| langdetect | 0.001s | nl | - |
| fast-langdetect | 0.0s | de (0.5161) | ⚠️ Không chắc chắn |

**Nhận xét**: Text quá ngắn khiến tất cả đều không chắc chắn.

#### Test 2: "1234567890 !@#$%^&*()" (Số và ký tự đặc biệt)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.055s | ur (0.5342) | ⚠️ Không chắc chắn |
| langdetect | 0.0s | ❌ ERROR | No features in text |
| fast-langdetect | 0.0s | ja (0.1835) | ⚠️ Không chắc chắn |

**Nhận xét**: 
- langdetect không thể xử lý (đúng như mong đợi)
- xlm-r và fast-langdetect cố gắng nhưng không chắc chắn

#### Test 3: "def hello_world(): print('Hello, World!')" (Code snippet)
| Phương pháp | Thời gian | Kết quả | Confidence |
|------------|-----------|---------|------------|
| xlm-r | 0.050s | en (0.4878) | ⚠️ Không chắc chắn |
| langdetect | 0.008s | en | - |
| fast-langdetect | 0.0s | en (0.1996) | ⚠️ Không chắc chắn |

**Nhận xét**: Code snippet khó nhận diện do có nhiều ký tự đặc biệt.

---

## 3. So sánh tổng thể

### 3.1. Ưu điểm của từng phương pháp

#### xlm-r (XLM-RoBERTa)
✅ **Ưu điểm:**
- Có confidence score chi tiết
- Phương pháp deep learning hiện đại
- Hỗ trợ nhiều ngôn ngữ

❌ **Nhược điểm:**
- Chậm nhất (0.025-0.355s)
- Cần GPU/CPU mạnh
- Model lớn, tốn tài nguyên
- Nhầm Korean thành Japanese
- Confidence thấp với mixed language

#### langdetect
✅ **Ưu điểm:**
- Rất nhanh (~0.0s sau lần đầu)
- Nhẹ, không cần GPU
- Dễ sử dụng
- Nhận diện chính xác Korean
- Trả về zh-cn (cụ thể hơn)

❌ **Nhược điểm:**
- Không có confidence score
- Phương pháp thống kê cũ hơn
- Không xử lý được text chỉ có số/ký tự đặc biệt
- Lần đầu chậm (~0.178s)

#### fast-langdetect
✅ **Ưu điểm:**
- Nhanh nhất (~0.0s sau lần đầu)
- Có confidence score
- Hỗ trợ nhiều config (model='auto', 'full', 'lite')
- Có thể lấy top k candidates (hữu ích cho mixed language)
- Confidence cao nhất (thường >0.99)
- Nhận diện chính xác Korean

❌ **Nhược điểm:**
- Confidence thấp với mixed language (nhưng có thể dùng k>1 để phát hiện nhiều ngôn ngữ)
- Lần đầu chậm (~0.340s)

---

## 4. Kết luận và Khuyến nghị

### 4.1. Kết luận

1. **Tốc độ**: fast-langdetect > langdetect > xlm-r
2. **Độ chính xác**: fast-langdetect ≈ langdetect > xlm-r (xlm-r nhầm Korean)
3. **Confidence score**: fast-langdetect và xlm-r có, langdetect không có
4. **Mixed language**: fast-langdetect với `model='auto'` và `k=3` là tốt nhất

### 4.2. Khuyến nghị sử dụng

#### Cho dự án Translate Manga:

**Phương án 1: fast-langdetect (Khuyến nghị)**
- ✅ Nhanh nhất
- ✅ Có confidence score
- ✅ Hỗ trợ mixed language với config đặc biệt
- ✅ Độ chính xác cao
- ✅ Nhận diện chính xác Korean (quan trọng cho manga)

**Phương án 2: langdetect**
- ✅ Rất nhanh
- ✅ Nhẹ, đơn giản
- ✅ Độ chính xác tốt
- ❌ Không có confidence score
- ❌ Không hỗ trợ mixed language tốt

**Phương án 3: xlm-r**
- ✅ Có confidence score
- ❌ Chậm nhất
- ❌ Nhầm Korean
- ❌ Tốn tài nguyên

### 4.3. Cấu hình đề xuất

```python
# Cho text thông thường (single language)
from fast_langdetect import detect
result = detect(text, model='full', k=1)

# Cho text mixed language (Japanese + English trong manga)
result = detect(text, model='auto', k=3)  # Lấy top 3 candidates
```

---

## 5. Bảng tổng hợp nhanh

| Tiêu chí | xlm-r | langdetect | fast-langdetect |
|----------|-------|------------|-----------------|
| **Tốc độ** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Độ chính xác** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Confidence score** | ✅ | ❌ | ✅ |
| **Mixed language** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Tài nguyên** | 🔴 Cao | 🟢 Thấp | 🟢 Thấp |
| **Khuyến nghị** | ❌ | ⚠️ | ✅ |

---

## 6. Ghi chú

- Tất cả thời gian đo được tính bằng giây
- Confidence score được làm tròn 4 chữ số thập phân
- Test được thực hiện trên Windows với Python 3.x
- Lần đầu tiên mỗi phương pháp có thể chậm hơn do khởi tạo model
- Kết quả có thể khác nhau tùy vào phần cứng và môi trường

---

*Generated from benchmark test results - Date: 2025*

