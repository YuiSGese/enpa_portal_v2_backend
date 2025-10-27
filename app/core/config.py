from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

# アプリケーションルートディレクトリ（'app'フォルダを含むディレクトリ）
BASE_DIR = Path(__file__).resolve().parent.parent

# --- パス設定 ---
# 共有アセットディレクトリ
ASSETS_DIR = BASE_DIR / "assets"
# 共有フォントディレクトリ
FONTS_DIR = ASSETS_DIR / "fonts"
# Tool03用アセットディレクトリ (必要に応じてパスを修正してください)
TOOL03_ASSETS_DIR = BASE_DIR / "app" / "api" / "tool03" / "assets"
# Tool03用テンプレートディレクトリ
TOOL03_TEMPLATES_DIR = TOOL03_ASSETS_DIR / "templates"

# プロジェクトルートディレクトリ（BASE_DIRの親）にある .env ファイルをロードする設定
# 例: /path/to/enpa_portal_v2_backend/.env
env_path = BASE_DIR.parent / ".env"

class Settings(BaseSettings):
    # Pydantic設定: .envファイルから読み込む
    model_config = SettingsConfigDict(
        env_file=str(env_path) if env_path.exists() else None, # ファイルが存在する場合のみ読み込む
        extra='ignore' # .envファイルに定義されていない設定項目は無視する
    )

    # --- アプリケーション設定 ---
    APP_NAME: str = "EmpaPortalV2"
    APP_ENV: str = "development" # 環境 (例: "development", "staging", "production")
    APP_DEBUG: bool = True     # デバッグモード

    # --- 基本データベース設定 ---
    DB_HOST: str = "127.0.0.1" # デフォルトはローカル（'localhost'ではなくIP推奨）
    DB_PORT: int = 3306
    DB_USER: str = "empa"
    DB_PASS: str = "empa_pass"
    DB_NAME: str = "empa_portal_v2"

    # --- SQLAlchemy Engine/Pool 設定 ---
    # database.py から移動
    DB_ECHO: bool = False             # SQLログ出力 (デバッグ用)
    DB_POOL_SIZE: int = 5             # 接続プールの基本サイズ
    DB_MAX_OVERFLOW: int = 10         # プールサイズを超える一時的な接続数
    DB_POOL_RECYCLE: int = 3600       # 接続の再利用時間（秒）、1時間
    DB_ISOLATION_LEVEL: str = "READ COMMITTED" # デフォルトのトランザクション分離レベル

    # --- その他の設定（必要に応じて追加） ---
    # 例:
    # SECRET_KEY: str = "your_secret_key" # JWTなどに使用する秘密鍵
    # ALGORITHM: str = "HS256"            # JWTのアルゴリズム
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # アクセストークンの有効期限（分）

# アプリケーション全体で使用する設定インスタンス
settings = Settings()

# デバッグモード時に設定内容を出力（オプション）
# if settings.APP_DEBUG:
#     env_source = env_path if env_path.exists() else 'デフォルト値/環境変数'
#     print(f"DEBUG: 設定読み込み元: {env_source}")
#     print(settings.model_dump())

