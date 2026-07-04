import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart-cooking-ai-secret-key-2024")

    # Gemini Configuration (Used for Image Scanning/Vision & Chat)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6K-6q9ss9F5PKJz-V23kVZwaPNxOyMVdj5UD5xGRPG6ZA")
    GEMINI_MODEL = "gemini-2.5-flash"

    # Groq Configuration (Used for Fast Recipe Generation)
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
    GROQ_MODEL = "llama-3.3-70b-versatile"

    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    RECIPES_FILE = "data/recipes.json"
    DATABASE_PATH = "cooking_app.db"