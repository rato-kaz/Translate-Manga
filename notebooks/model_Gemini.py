import os
import time
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY không được tìm thấy trong biến môi trường hoặc file .env")

genai.configure(api_key=api_key)

# Khởi tạo model Gemini
model = genai.GenerativeModel('gemini-2.5-flash')

# Đọc ảnh
image_path = "panel_example_1.jpg"
image = Image.open(image_path)

# Prompt mô tả manga panel
prompt = "You are a visual storytelling assistant that describes manga panels. Describe the given manga panel in one or two sentences. Focus on the characters, their actions, emotions, and any visible dialogue. Avoid generic phrases like 'in a manga style'. Use natural prose suitable for a novel or screenplay. Do not explain anything else. Only output the description. The following text appears in the panel: 'この店はコーヒーが美味いんだ'."

# Gửi request với ảnh và prompt
print("\n" + "="*50)
print("ĐANG XỬ LÝ VỚI GEMINI...")
print("="*50)
start_time = time.time()

response = model.generate_content([prompt, image])

end_time = time.time()

# In kết quả
print("\n" + "="*50)
print("KẾT QUẢ MÔ TẢ MANGA PANEL")
print("="*50)
print("\nMô tả:")
print(response.text)
print(f"\nThời gian chạy: {end_time - start_time:.2f} giây")
print("="*50 + "\n")

