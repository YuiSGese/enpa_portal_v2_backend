# test_db.py
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.core.config import settings # 使用中の設定を確認するためにインポート

def test_connection():
    """データベース接続をテストします。"""
    print("--- データベース接続テスト開始 ---")
    # 接続情報を表示（パスワードは隠す）
    print(f"接続先情報: mariadb+mariadbconnector://{settings.DB_USER}:***@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"SQLAlchemy Echo設定: {settings.DB_ECHO}")
    print("-" * 30)

    db: Session | None = None # db変数をNoneで初期化
    try:
        # 1. セッション取得試行
        print("セッション取得試行中...")
        db = SessionLocal()
        print("セッション取得成功。")

        # 2. 簡単なSQLクエリ実行試行 (SELECT 1)
        print("単純なクエリ実行試行 (SELECT 1)...")
        result = db.execute(text("SELECT 1"))
        value = result.scalar_one() # 結果を1つ取得
        print(f"クエリ成功。結果: {value}")

        # 3. MariaDBバージョン取得試行
        print("MariaDBバージョン取得試行中...")
        version_result = db.execute(text("SELECT VERSION()"))
        version = version_result.scalar_one()
        print(f"接続成功。MariaDB バージョン: {version}")
        print("-" * 30)
        print(">>> 接続テスト成功！ <<<")

    except Exception as e:
        # エラー発生時の処理
        print("\n!!! 接続テスト失敗 !!!")
        print(f"エラータイプ: {type(e).__name__}")
        print(f"エラー詳細: {e}")
        # 詳細なデバッグが必要な場合はトレースバックを出力
        # import traceback
        # traceback.print_exc()

    finally:
        # セッションが取得できていれば必ずクローズする
        if db:
            print("セッションクローズ中...")
            db.close()
            print("セッションクローズ完了。")
        print("--- テスト終了 ---")

# スクリプトとして直接実行された場合にテストを実行
if __name__ == "__main__":
    test_connection()
