"""
ocr_extraction.py

Handles PDF-to-Image conversion and then uses the 
Gemini API's multimodal capabilities for OCR.
"""

import os
import base64
import io
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import streamlit as st
from typing import Optional

# --- PDF Conversion (requires pdf2image) ---
try:
    from pdf2image.pdf2image import convert_from_path
except ImportError:
    st.error("pdf2image not found. Please run: pip install pdf2image")
    convert_from_path = None

def convert_pdf_to_images(pdf_path: str, poppler_path: Optional[str] = None) -> list[str]:
    """
    Converts a PDF file into a list of base64-encoded JPEG images.
    """
    if not convert_from_path:
        raise ImportError("pdf2image library is required but not found.")
        
    print(f"Converting PDF: {pdf_path}")

    # Call 'convert_from_path' differently based on whether poppler_path is provided.
    if poppler_path:
        images = convert_from_path(pdf_path, poppler_path=poppler_path, dpi=150)
    else:
        images = convert_from_path(pdf_path, dpi=150)
    
    base64_images = []
    for i, image in enumerate(images):
        print(f"  - Processing page {i+1}/{len(images)}")
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        b64_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
        base64_images.append(b64_string)
        
    print(f"Conversion complete. {len(base64_images)} images generated.")
    return base64_images

# --- Gemini API Configuration ---
def initialize_gemini(api_key):
    """Initializes and configures the Gemini client."""
    try:
        if not api_key:
            st.error("API Key is missing. Please add it on the 'Settings' page.")
            return False
        
        genai.configure(api_key=api_key)  # pyright: ignore[reportPrivateImportUsage]
        return True
    except Exception as e:
        st.error(f"Error configuring Gemini API: {e}")
        return False

# Safety settings
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- Gemini OCR Function ---
def extract_text_from_images(images_base64: list[str], api_key: str, mime_type: str = "image/jpeg") -> str:
    """
    Performs OCR on an array of base64-encoded images using Gemini.
    """
    if not initialize_gemini(api_key):
        return "API Key configuration failed."

    # --- THIS WILL CAUSE A 404 ERROR WITH YOUR OLD LIBRARY ---
    OCR_MODEL = genai.GenerativeModel("models/gemini-2.5-flash-preview-09-2025")  # pyright: ignore[reportPrivateImportUsage]

    if not images_base64:
        return ""
        
    print(f"Starting Gemini OCR for {len(images_base64)} images (one by one)...")

    # This prompt will be used for each individual page
    prompt_for_single_image = "Extract all text from this image. Maintain line breaks."
    
    all_extracted_text = []
    
    for i, b64_string in enumerate(images_base64):
        print(f"  - Processing image {i+1}/{len(images_base64)}...")
        
        parts = [
            {"text": prompt_for_single_image},
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_string
                }
            }
        ]
        
        try:
            response = OCR_MODEL.generate_content(parts, safety_settings=SAFETY_SETTINGS)
            
            if response.parts:
                all_extracted_text.append(response.text)
            else:
                reason = response.candidates[0].finish_reason if response.candidates else "Unknown"
                print(f"    - OCR failed for image {i+1}. Reason: {reason}")
                all_extracted_text.append(f"[Page {i+1} OCR Failed: {reason}]")

        except Exception as e:
            print(f"    - An error occurred during OCR for image {i+1}: {e}")
            all_extracted_text.append(f"[Page {i+1} OCR Error: {e}]")

    print("OCR extraction complete for all images.")
    # Join the text from all pages, separated by a new line
    return "\n".join(all_extracted_text)