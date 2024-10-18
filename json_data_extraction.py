import streamlit as st
from PyPDF2 import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai
from docx import Document
from pptx import Presentation
import pandas as pd
import os
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

if not api_key:
    st.error("API key not found. Please check your .env file or environment variables.")

class PolicyExtractor:
    def __init__(self):
        self.model = genai.GenerativeModel(model_name='gemini-1.5-pro')

    def get_text_from_document(self, uploaded_files):
        text = ""
        for file in uploaded_files:
            if file.name.lower().endswith((".pdf", ".docx", ".txt", ".pptx", ".csv")):
                try:
                    if file.name.lower().endswith(".pdf"):
                        pdf_reader = PdfReader(file)
                        for page in pdf_reader.pages:
                            text += page.extract_text() or ""
                    elif file.name.lower().endswith(".docx"):
                        doc_content = Document(file)
                        text += "\n".join([paragraph.text for paragraph in doc_content.paragraphs])
                    elif file.name.lower().endswith(".txt"):
                        text += file.read().decode('utf-8', errors='ignore')
                    elif file.name.lower().endswith(".pptx"):
                        presentation = Presentation(file)
                        for slide in presentation.slides:
                            for shape in slide.shapes:
                                if hasattr(shape, "text"):
                                    text += shape.text + "\n"
                    elif file.name.lower().endswith('.csv'):
                        df = pd.read_csv(file)
                        text += df.to_csv(index=False)
                except Exception as e:
                    st.error(f"Error processing {file.name}: {e}")
        return text
    
    def get_text_chunks(self, text):
        """Split text into chunks."""
        if not text:
            print("No text provided.")
            return []
        try:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
            chunks = text_splitter.split_text(text)
            return chunks
        except Exception as e:
            print(f"Error splitting text: {e}")
            return []

    def extract_policy_information(self, chunks):
        """Extract policy information from the text."""
        prompt = """Analyze the uploaded document and extract key information into the following structured JSON format:
        {
            "inspections": [
                {
                    "id": "auto_generated_id",
                    "name": "Flood",
                    "claim_type": {
                        "id": 1,
                        "name": "Flood"
                    },
                    "categories": [
                        {
                            "id": "auto_generated_id",
                            "name": "string",
                            "is_interior": "boolean",
                            "priority": 1,
                            "applicable": "boolean",
                            "subcategory_collection": [
                                {
                                    "id": 1,
                                    "title": "string",
                                    "description": "string",
                                    "helptext": "string",
                                    "priority": 1,
                                    "questions_collection": [
                                        {
                                            "id": 1,
                                            "title": "Has the front elevation water damage been captured?",
                                            "description": "Ensure that the front elevation's water damage due to flooding has been recorded.",
                                            "helptext": "Capture any visible water damage to the front elevation caused by flooding.",
                                            "priority": 1,
                                            "required": true,
                                            "answer_type": "boolean",
                                            "photos": true,
                                            "videos": true,
                                            "photos_360": true,
                                            "photos_response_collection": [{}],
                                            "docs": false,
                                            "video_response_collection": [],
                                            "360_photo_response_collection": [],
                                            "notes": true,
                                            "applicable": true
                                        }
                                    ]
                                }
                            ],
                            "additional_questions": [],
                            "floor_collection": []
                        }
                    ]
                }
            ]
        }"""

        extracted_info = {}
        try:
            combined_input = f"{prompt}\n\n" + '\n'.join(chunks)
            input_data = {
                "parts": [
                    {"text": combined_input}
                ]
            }
            response = self.model.generate_content(input_data) 

            if response.candidates:
                generated_content = response.candidates[0].content.parts[0].text.strip() 
                generated_content = generated_content.replace("```json", "").replace("```", "").strip() 
                # print("Cleaned Generated Content:", generated_content)
                try:
                    extracted_info = json.loads(generated_content)  
                    # print("Extracted Info:", extracted_info)  
                except json.JSONDecodeError as e:
                    # print(f"JSONDecodeError: {e} | Cleaned Generated Content: {generated_content}")
                    extracted_info = {"error": "Invalid JSON response", "content": generated_content}
            else:
                extracted_info = {"error": "No candidates found in response."}

        except Exception as e:
            print("Error during extraction:", e)
            extracted_info = {"error": str(e)}

        return extracted_info


    def main(self):
        """Main function to run the policy extraction application."""
        st.set_page_config("Insurance Policy Data Extraction")
        st.header("Insurance Policy Scan:")
        uploaded_files = st.file_uploader("Upload Policy Documents", type=["pdf", "docx", "txt", "pptx"], accept_multiple_files=True)
        if uploaded_files:
            st.write("Extracting key components...")
            raw_text = self.get_text_from_document(uploaded_files)
            chunks = self.get_text_chunks(raw_text)
            policy_info_dict = self.extract_policy_information(chunks)
            st.write("Extracted Policy Information:")
            st.json(policy_info_dict)

if __name__ == "__main__":
    app = PolicyExtractor()
    app.main()
