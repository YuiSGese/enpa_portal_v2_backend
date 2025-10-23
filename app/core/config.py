from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Đường dẫn thư mục gốc của ứng dụng (nơi chứa thư mục 'app')
BASE_DIR = Path(__file__).resolve().parent.parent

# Đường dẫn đến thư mục assets chung
TOOL03_ASSETS_DIR = BASE_DIR / "tool03" / "assets"

# Đường dẫn đến thư mục fonts chung
FONTS_DIR = ASSETS_DIR / "fonts"

# Đường dẫn đến thư mục templates của Tool 03
TOOL03_TEMPLATES_DIR = TOOL03_ASSETS_DIR / "templates"

load_dotenv()

class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "EmpaPortalV2")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True") == "True"

    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER")
    DB_PASS: str = os.getenv("DB_PASS")
    DB_NAME: str = os.getenv("DB_NAME")

settings = Settings()