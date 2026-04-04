import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    FUSEKI_URL: str = os.getenv("FUSEKI_URL", "http://localhost:3030/amaturis")
    FUSEKI_QUERY: str = os.getenv("FUSEKI_QUERY", f"{FUSEKI_URL}/query")
    FUSEKI_UPDATE: str = os.getenv("FUSEKI_UPDATE", f"{FUSEKI_URL}/update")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()