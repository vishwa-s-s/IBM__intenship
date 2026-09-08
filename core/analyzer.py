import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise Exception("Gemini API key is missing. Please set GEMINI_API_KEY in your .env file.")

# Create a client with your API key
client = genai.Client(api_key=api_key)

def analyze_text(text: str, language: str = "English") -> str:
    """
    Analyzes and summarizes the given text using Gemini 1.5 Flash.
    Returns the summary in the requested language.
    """
    try:
        prompt = f"""
        You are an expert research assistant. Read the following text and provide a concise,
        highly informative summary. Extract the key points and findings.

        The summary MUST be written in the following language: {language}.

        Text:
        {text[:15000]}
        """

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        raise Exception(f"Failed to analyze text with Gemini: {str(e)}")
