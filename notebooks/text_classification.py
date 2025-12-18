from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
import time
from langdetect import detect as langdetect_detect
from langdetect.lang_detect_exception import LangDetectException
from fast_langdetect import detect as fast_detect

# Load model
model_name = "papluca/xlm-roberta-base-language-detection"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

texts = [
    # Japanese - Short
    "こんにちは！",
    # Japanese - Medium
    "今日は良い天気ですね。散歩に行きましょう。",
    # Japanese - Long (manga dialogue)
    "この店はコーヒーが美味いんだ。毎日ここに来て、同じ席に座って、同じコーヒーを飲む。それが僕の日課なんだ。",
    # Vietnamese - Short
    "Tôi đang đọc manga.",
    # Vietnamese - Medium
    "Hôm nay trời đẹp quá. Chúng ta nên đi dạo công viên.",
    # Vietnamese - Long
    "Dự án dịch manga này thực sự thú vị. Tôi đang học cách sử dụng các công cụ nhận diện ngôn ngữ và dịch thuật tự động để xử lý các bộ truyện tranh Nhật Bản.",
    # English - Short
    "This is a test.",
    # English - Medium
    "The weather is beautiful today. We should go for a walk in the park.",
    # English - Long
    "Machine learning and natural language processing have revolutionized the way we work with text data. These technologies enable us to build sophisticated applications that can understand, translate, and generate human language with remarkable accuracy.",
    # Chinese - Short
    "这是一个测试。",
    # Chinese - Medium
    "今天天气真好。我们应该去公园散步。",
    # Chinese - Long
    "人工智能和机器学习技术正在改变我们的世界。这些技术使我们能够构建复杂的应用程序，可以理解、翻译和生成人类语言，准确度令人印象深刻。",
    # Korean
    "안녕하세요. 오늘 날씨가 정말 좋네요.",
    # French
    "Bonjour! Comment allez-vous aujourd'hui? Le temps est magnifique.",
    # Spanish
    "Hola! ¿Cómo estás? El clima está hermoso hoy.",
    # German
    "Guten Tag! Wie geht es Ihnen? Das Wetter ist heute wunderbar.",
    # Mixed language (Japanese + English)
    "Hello! こんにちは！This is a mixed text.",
    # More mixed language examples
    "I love 日本語 and learning new languages.",
    "Bonjour! こんにちは！Hello from multiple languages.",
    # Very short text
    "Hi",
    # Numbers and symbols
    "1234567890 !@#$%^&*()",
    # Code snippet
    "def hello_world(): print('Hello, World!')",
]

# Map ID → label
labels = model.config.id2label

def detect_language(text):
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)
        idx = torch.argmax(probs, dim=1).item()
    return labels[idx], probs[0][idx].item()

print("=" * 60)
print("Test with xlm-r")
print("=" * 60)

# Test
for t in texts:
    start_time = time.time()
    try:
        lang, prob = detect_language(t)
        end_time = time.time()
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print(f"Detected language: {lang}, probability={prob:.4f}")
    except Exception as e:
        end_time = time.time()
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print(f"Detected language: ERROR - {str(e)}")
    print("--------------")
    
print("=" * 60)
print("Test with langdetect")
print("=" * 60)

# Test with langdetect
for t in texts:
    start_time = time.time()
    try:
        lang = langdetect_detect(t)
        end_time = time.time()
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print(f"Detected language: {lang}")
    except LangDetectException as e:
        end_time = time.time()
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print(f"Detected language: ERROR - {str(e)}")
    except Exception as e:
        end_time = time.time()
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print(f"Detected language: ERROR - {str(e)}")
    print("--------------")
    
print("=" * 60)
print("Test with fast-langdetect")
print("=" * 60)
# Test with fast-langdetect
for t in texts:
    start_time = time.time()
    try:
        results = fast_detect(t, model='full', k=1)
        end_time = time.time()
        result = results[0] if results else {}
        lang = result.get('lang', 'unknown')
        prob = result.get('score', 0.0)
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print(f"Detected language: {lang}, probability={prob:.4f}")
    except Exception as e:
        end_time = time.time()
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print(f"Detected language: ERROR - {str(e)}")
    print("--------------")

# Test mixed language with special config
print("=" * 60)
print("Test with fast-langdetect (Mixed Language - Special Config)")
print("=" * 60)
print("Config: model='auto', k=3 (top 3 candidates)")
print("=" * 60)

# Mixed language texts
mixed_texts = [
    "Hello! こんにちは！This is a mixed text.",
    "I love 日本語 and learning new languages.",
    "Bonjour! こんにちは！Hello from multiple languages.",
]

for t in mixed_texts:
    start_time = time.time()
    try:
        results = fast_detect(t, model='auto', k=3)
        end_time = time.time()
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print("Top candidates:")
        for i, result in enumerate(results[:3], 1):
            lang = result.get('lang', 'unknown')
            prob = result.get('score', 0.0)
            print(f"  {i}. {lang}: {prob:.4f}")
    except Exception as e:
        end_time = time.time()
        print(f"Thời gian chạy: {end_time - start_time} giây")
        print(f"Text: {t}")
        print(f"Detected language: ERROR - {str(e)}")
    print("--------------")