import os

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24).hex())

    # Gemini AI Configuration - NO HARDCODED KEY
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # Groq AI Configuration - NO HARDCODED KEY
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Application Settings
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    RECIPES_FILE = "data/recipes.json"
    DATABASE_PATH = "cooking_app.db"

    @classmethod
    def is_gemini_available(cls):
        return bool(cls.GEMINI_API_KEY and cls.GEMINI_API_KEY.strip())

    @classmethod
    def is_groq_available(cls):
        return bool(cls.GROQ_API_KEY and cls.GROQ_API_KEY.strip())
