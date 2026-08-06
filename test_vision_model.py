"""
Quick test: load local Qwen2-VL-2B-Instruct and describe an image.
Fully offline once the model is downloaded.
"""

import os
from pathlib import Path

# Force offline (optional but recommended)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from PIL import Image
import torch

MODEL_PATH = Path(r"C:\JAY_DOCS\models\Qwen2-VL-2B-Instruct")

# --- Put a real image path here (one of your vision-flagged charts) ---
TEST_IMAGE = Path(r"C:\Users\jason\OneDrive\Pictures\Screenshots 1\Picture.png")  # change to a real .png / .jpg file

def find_first_image(folder: Path) -> Path | None:
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.tif", "*.tiff"):
        hits = list(folder.rglob(ext))
        if hits:
            return hits[0]
    return None

image_path = TEST_IMAGE if TEST_IMAGE.is_file() else find_first_image(TEST_IMAGE)
if image_path is None:
    raise FileNotFoundError("No test image found. Set TEST_IMAGE to a real image file.")

print("Using image:", image_path)
print("Loading model from:", MODEL_PATH)

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

model = Qwen2VLForConditionalGeneration.from_pretrained(
    str(MODEL_PATH),
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    device_map="auto" if device == "cuda" else None,
)
processor = AutoProcessor.from_pretrained(str(MODEL_PATH))

messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": str(image_path)},
            {"type": "text", "text": "Describe this image in 2-3 sentences. Focus on any chart, table, or key information."},
        ],
    }
]

text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
image_inputs, video_inputs = process_vision_info(messages)

inputs = processor(
    text=[text],
    images=image_inputs,
    videos=video_inputs,
    padding=True,
    return_tensors="pt",
)
inputs = inputs.to(device)

print("Generating description...")
with torch.no_grad():
    output_ids = model.generate(**inputs, max_new_tokens=128)

generated = processor.batch_decode(
    [out[len(inp):] for inp, out in zip(inputs.input_ids, output_ids)],
    skip_special_tokens=True,
)[0]

print("\n===== MODEL OUTPUT =====")
print(generated)
print("========================")