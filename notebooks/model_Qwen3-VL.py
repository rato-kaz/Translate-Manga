import os
import base64
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Load biến môi trường từ file .env
load_dotenv()

client = InferenceClient(
    provider="novita",
    api_key=os.environ.get("HF_TOKEN"),
)

# Đọc và encode ảnh thành base64
image_path = "panel_example_1.jpg"
with open(image_path, "rb") as f:
    image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

# Xác định loại ảnh từ extension
image_ext = os.path.splitext(image_path)[1].lower()
mime_type = "image/jpeg" if image_ext in [".jpg", ".jpeg"] else "image/png" if image_ext == ".png" else "image/jpeg"

completion = client.chat.completions.create(
    model="Qwen/Qwen3-VL-30B-A3B-Instruct",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "You are a visual storytelling assistant that describes manga panels. Describe the given manga panel in one or two sentences. Focus on the characters, their actions, emotions, and any visible dialogue. Avoid generic phrases like 'in a manga style'. Use natural prose suitable for a novel or screenplay. The following text appears in the panel: '高橋さん最近また強くなりましたよね', '隙がないっていうか周到ってもうか'."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_base64}"
                    }
                }
            ]
        }
    ],
)

# In kết quả
print("\n" + "="*50)
print("KẾT QUẢ MÔ TẢ MANGA PANEL")
print("="*50)
print("\nMô tả:")
print(completion.choices[0].message.content)
print("="*50 + "\n")
