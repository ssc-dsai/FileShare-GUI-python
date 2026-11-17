# Classification/vision_helper.py
"""
Multi-image vision descriptions using local Qwen2-VL.
Reads [IMAGE_PATH: ...] markers from ingestion and/or scans _images/{stem}/.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_PATH_RE = re.compile(r"\[IMAGE_PATH:\s*(.+?)\]")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".bmp", ".webp"}

# Lazy-loaded model (one load per process)
_model = None
_processor = None


def collect_image_paths(
    raw_text: str,
    original_path: Path | None = None,
    extracted_texts_dir: Path | None = None,
) -> list[Path]:
    """Gather 0..N image files for vision description."""
    paths: list[Path] = []
    seen: set[str] = set()

    def _add(p: Path) -> None:
        try:
            rp = str(p.resolve())
        except Exception:
            rp = str(p)
        if rp in seen:
            return
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            seen.add(rp)
            paths.append(p)

    for m in IMAGE_PATH_RE.finditer(raw_text or ""):
        _add(Path(m.group(1).strip().strip('"')))

    if original_path and original_path.suffix.lower() in IMAGE_EXTS:
        _add(original_path)

    if original_path and extracted_texts_dir:
        folder = Path(extracted_texts_dir) / "_images" / original_path.stem
        if folder.is_dir():
            for p in sorted(folder.iterdir()):
                _add(p)
    elif extracted_texts_dir and original_path is None:
        # stem from text markers only — already handled via IMAGE_PATH
        pass

    return paths


def _load_qwen(model_path: Path):
    global _model, _processor
    if _model is not None:
        return _model, _processor

    import torch
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

    logger.info(f"Loading vision model from {model_path}")
    _processor = AutoProcessor.from_pretrained(str(model_path), trust_remote_code=True)
    _model = Qwen2VLForConditionalGeneration.from_pretrained(
        str(model_path),
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    if not torch.cuda.is_available():
        _model = _model.to("cpu")
    _model.eval()
    logger.info("Vision model ready")
    return _model, _processor


def describe_image(image_path: Path, model_path: Path) -> str:
    """Describe a single image with local Qwen2-VL."""
    from PIL import Image
    import torch

    if not image_path.is_file():
        return ""

    model, processor = _load_qwen(model_path)
    image = Image.open(image_path).convert("RGB")

    prompt = (
        "Describe this document image in detail for records classification. "
        "Include chart titles, axis labels, key numbers, logos, form fields, "
        "and any visible text. Be concise but complete."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    try:
        text_prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = processor(
            text=[text_prompt],
            images=[image],
            return_tensors="pt",
            padding=True,
        )
        device = next(model.parameters()).device
        inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in inputs.items()}

        with torch.no_grad():
            generated = model.generate(**inputs, max_new_tokens=256)

        # Strip prompt tokens when possible
        trim = inputs["input_ids"].shape[1]
        out_ids = generated[:, trim:]
        desc = processor.batch_decode(out_ids, skip_special_tokens=True)[0].strip()
        return desc
    except Exception as e:
        logger.error(f"describe_image failed for {image_path.name}: {e}")
        return ""


def build_vision_augmented_text(
    raw_text: str,
    model_path: Path,
    original_path: Path | None = None,
    extracted_texts_dir: Path | None = None,
) -> tuple[str, str]:
    """
    Returns (text_for_matching, vision_description_for_excel).
    vision_description is 'N/A' when not flagged or no images.
    """
    if "[VISION_FLAG: Yes]" not in (raw_text or ""):
        return raw_text, "N/A"

    if not model_path.exists():
        logger.error(f"Vision model path not found: {model_path}")
        return raw_text, "N/A"

    paths = collect_image_paths(raw_text, original_path, extracted_texts_dir)
    if not paths:
        logger.warning("VISION_FLAG Yes but no image files found")
        return raw_text, "N/A"

    blocks: list[str] = []
    for i, img in enumerate(paths, 1):
        try:
            desc = describe_image(img, model_path)
            if desc:
                blocks.append(f"[Image {i}: {img.name}]\n{desc}")
                logger.info(f"Vision description ({len(desc)} chars) for {img.name}")
        except Exception as e:
            logger.error(f"Vision failed for {img}: {type(e).__name__}: {e}")

    if not blocks:
        return raw_text, "N/A"

    vision_block = "\n\n".join(blocks)
    augmented = f"[Vision Description]\n{vision_block}\n\n{raw_text}"
    return augmented, vision_block