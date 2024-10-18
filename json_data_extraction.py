import streamlit as st
from PyPDF2 import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from docx import Document
from pptx import Presentation
import pandas as pd
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# Safety settings for GenAI model
safety_settings = [
    {"category": category, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} 
    for category in [
        "HARM_CATEGORY_HARASSMENT", 
        "HARM_CATEGORY_HATE_SPEECH", 
        "HARM_CATEGORY_SEXUALLY_EXPLICIT", 
        "HARM_CATEGORY_DANGEROUS_CONTENT"
    ]
]

class PolicyExtractor:
    def __init__(self):
        self.model = genai.GenerativeModel(model_name='gemini-1.5-flash-002', safety_settings=safety_settings)

    def get_text_from_document(self, uploaded_files):
        text = ""
        for file in uploaded_files:
            if file.name.lower().endswith((".pdf", ".docx", ".txt", ".pptx", ".csv")):
                try:
                    if file.name.lower().endswith(".pdf"):
                        pdf_reader = PdfReader(file)
                        for page in pdf_reader.pages:
                            text += page.extract_text()
                    elif file.name.endswith(".docx"):
                        doc_content = Document(file)
                        text += "\n".join([paragraph.text for paragraph in doc_content.paragraphs])
                    elif file.name.endswith(".txt"):
                        text += file.read().decode('utf-8', errors='ignore')
                    elif file.name.endswith(".pptx"):
                        presentation = Presentation(file)
                        for slide in presentation.slides:
                            for shape in slide.shapes:
                                if hasattr(shape, "text"):
                                    text += shape.text + "\n"
                    elif file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                        text += df.to_csv(index=False)
                except Exception as e:
                    st.error(f"Error processing {file.name}: {e}")
        return text

    def get_text_chunks(self, text):
        """
        Split text into chunks.
        """
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

    import json

    def extract_policy_information(self, chunks):
        """
        Extract policy information from text chunks.
        """
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
                        },
                        {
                            "id": 3,
                            "name": "Interior",
                            "is_interior": true,
                            "priority": 3,
                            "applicable": true,
                            "questions_collection": [],
                            "additional_questions": [],
                            "floor_collection": [
                                {
                                    "id": 1,
                                    "name": "Basement",
                                    "priority": 1,
                                    "rooms": [
                                        {
                                            "id": 1,
                                            "value": "Bedroom",
                                            "name": "Rebecca's Room",
                                            "area": "23truem",
                                            "photos": true,
                                            "videos": true,
                                            "photos_360": true,
                                            "entry_from": "Hall",
                                            "item_collection": [],
                                            "questions_collection": [],
                                            "additional_questions": [],
                                            "photos_response_collection": [{}],
                                            "docs": false,
                                            "video_response_collection": [],
                                            "360_photo_response_collection": [],
                                            "notes": true
                                        },
                                        {
                                            "id": 4,
                                            "value": "Entry / Foyer",
                                            "name": "Rebecca's Entry / Foyer",
                                            "area": "23truem",
                                            "photos": true,
                                            "videos": true,
                                            "photos_360": true,
                                            "entry_from": "Hall",
                                            "item_collection": [],
                                            "questions_collection": [
                                                {
                                                    "id": 14,
                                                    "title": "Have you taken a picture of the stairs?",
                                                    "description": "Have you taken a picture of the stairs?",
                                                    "helptext": "Have you taken a picture of the stairs?",
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
                                            ],
                                            "additional_questions": []
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }"""

        extracted_info = {}
        try:
            # Join chunks into a single string for input
            input_data = {"input_text": "\n".join(chunks), "target_prompt": prompt}
            input_data_json = json.dumps(input_data)
            
            # Call the model to generate content
            response = self.model.generate_content(input_data_json)

            # Check if response is valid JSON and parse it
            if response and isinstance(response, str):
                try:
                    extracted_info = json.loads(response)
                except json.JSONDecodeError:
                    print("Failed to decode JSON response:", response)
                    extracted_info = {"error": "Invalid JSON response"}
            else:
                extracted_info = {"error": "Empty response from model"}
                
        except Exception as e:
            print("Error during extraction:", e)
            extracted_info = {"error": str(e)}  # Return the error as part of the response

        return extracted_info





    


    def main(self):
        """
        Main function to run the policy extraction application.
        """
        st.set_page_config("Insurance Policy Data Extraction")
        st.header("Insurance Policy Scan:", divider='rainbow')
        uploaded_files = st.file_uploader("Upload Policy Documents", type=["pdf", "docx", "txt", "pptx"], accept_multiple_files=True)
        if uploaded_files:
            st.write("Extracting key components...")
            raw_text = self.get_text_from_document(uploaded_files)
            chunks = self.get_text_chunks(raw_text)
            policy_info_dict = self.extract_policy_information(chunks)
            st.write("Extracted Policy Information:")
            st.json(policy_info_dict)
            # for key, value in policy_info_dict.items():
            #     st.write(f"- {key}: {value}")

if __name__ == "__main__":
    app = PolicyExtractor()
    app.main()
