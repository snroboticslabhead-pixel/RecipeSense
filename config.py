import os

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart-cooking-ai-secret-key-2024")

    # Gemini AI Configuration
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyD0-wbHtJYgIuGIgjlG9ZrZVTPPCV8WbDs")
    GEMINI_MODEL = "gemini-2.5-flash"

    # Groq AI Configuration
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
    GROQ_MODEL = "llama-3.3-70b-versatile"

    # Application Settings
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    RECIPES_FILE = "data/recipes.json"
    DATABASE_PATH = "cooking_app.db"
