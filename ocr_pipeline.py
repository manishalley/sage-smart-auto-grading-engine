"""
ocr_pipeline.py
Phase 1: PDF → Images → Preprocess → Gemini OCR → Extracted Text JSON
"""

import os
import cv2
import base64
import json
from pdf2image import convert_from_path
from tqdm import tqdm
import google.generativeai as genai


class OCRPipeline:
    def __init__(self, api_key: str, output_base: str = "output"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")
        self.output_base = output_base

    def pdf_to_images(self, pdf_path: str, session_id: str) -> str:
        image_folder = os.path.join(self.output_base, session_id, "raw_images")
        os.makedirs(image_folder, exist_ok=True)

        pages = convert_from_path(pdf_path, dpi=300)
        for i, page in enumerate(pages):
            page.save(os.path.join(image_folder, f"page_{i+1}.jpg"), "JPEG")

        print(f"✅ Converted {len(pages)} pages to images.")
        return image_folder

    def preprocess_images(self, image_folder: str, session_id: str) -> str:
        preprocessed_folder = os.path.join(self.output_base, session_id, "preprocessed_images")
        os.makedirs(preprocessed_folder, exist_ok=True)

        for image_file in sorted(os.listdir(image_folder)):
            if not image_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            img = cv2.imread(os.path.join(image_folder, image_file))
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
            processed = cv2.adaptiveThreshold(
                denoised, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            cv2.imwrite(os.path.join(preprocessed_folder, image_file), processed)

        print("✅ Preprocessing completed.")
        return preprocessed_folder

    def image_to_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def extract_text_from_image(self, image_path: str) -> str:
        prompt = """You are an advanced OCR system for handwritten exam answer sheets.

Your job:
- Extract ALL handwritten text exactly as written
- Preserve question numbers exactly (e.g., Q1, Q2, 1., 1), Part A, Part B)
- Preserve paragraph structure and line breaks
- Do NOT correct spelling or grammar
- Ignore crossed-out or scribbled text
- Output only plain text, no markdown

Start directly with the extracted text."""

        try:
            response = self.model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": self.image_to_base64(image_path)}
            ])
            return response.text.strip()
        except Exception as e:
            return f"[OCR_ERROR: {str(e)}]"

    def run(self, pdf_path: str, session_id: str) -> dict:
        print(f"🔄 Starting OCR pipeline for session: {session_id}")

        image_folder = self.pdf_to_images(pdf_path, session_id)
        preprocessed_folder = self.preprocess_images(image_folder, session_id)

        results = []
        image_files = sorted([
            f for f in os.listdir(preprocessed_folder)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])

        print(f"🔄 Extracting text from {len(image_files)} pages using Gemini...")
        for image_file in tqdm(image_files):
            image_path = os.path.join(preprocessed_folder, image_file)
            text = self.extract_text_from_image(image_path)
            results.append({"page": image_file, "text": text})

        full_text = "\n\n".join([r["text"] for r in results])

        output = {
            "session_id": session_id,
            "pages": results,
            "full_text": full_text,
            "total_pages": len(results)
        }

        output_dir = os.path.join(self.output_base, session_id)
        with open(os.path.join(output_dir, "ocr_result.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4, ensure_ascii=False)

        with open(os.path.join(output_dir, "extracted_text.txt"), "w", encoding="utf-8") as f:
            for page in results:
                f.write(f"\n\n--- {page['page']} ---\n\n{page['text']}")

        print("✅ OCR pipeline completed!")
        return output