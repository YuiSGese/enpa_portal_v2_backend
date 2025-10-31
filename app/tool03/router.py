# -*- coding: utf-8 -*-
from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Body
from fastapi.responses import FileResponse
import os
import shutil
from typing import List, Dict
import datetime # datetime をインポート

# 同一ディレクトリ (.) から schemas と controller をインポート
from . import schemas
from . import controller
from . import service as tool03_service # ジョブステータス確認用の service をインポート

router = APIRouter(
    prefix="/tools/03",
    tags=["Tool 03 - 二重価格画像作成"],
)

# --- エンドポイント /jobs (POST) ---
@router.post(
    "/jobs",
    response_model=schemas.Tool03CreateJobResponse,
    status_code=202 # 受理 (Accepted)
)
async def create_image_generation_job(
    request: schemas.Tool03CreateJobRequest,
    background_tasks: BackgroundTasks
):
    """画像生成ジョブをバックグラウンドで開始します。"""
    return controller.start_image_generation_job(request.productRows, background_tasks)

# --- エンドポイント /jobs/{job_id} (PATCH) ---
@router.patch(
    "/jobs/{job_id}",
    status_code=202 # 受理 (Accepted)
    # コマンドを受け取るだけなので response_model は不要
)
async def update_image_generation_job(
    request: schemas.Tool03CreateJobRequest, # 既存のスキーマを再利用
    background_tasks: BackgroundTasks,
    job_id: str = Path(..., description="更新対象のジョブID", min_length=36, max_length=36)
):
    """ジョブ内の指定された画像を再生成するためのバックグラウンドタスクを開始します。"""
    if not request.productRows:
         # 実行する内容がないため、202 (または 200 OK) を返す
         return {"message": "更新対象の行が指定されていません。"} 

    # controller を呼び出してバックグラウンド更新タスクを開始
    controller.start_image_regeneration_job(job_id, request.productRows, background_tasks)
    return {"message": f"ジョブ {job_id} の画像再生成タスクが開始されました。"}

# --- エンドポイント /jobs/{job_id}/status (GET) ---
@router.get(
    "/jobs/{job_id}/status",
    response_model=schemas.Tool03JobStatusResponse
)
async def get_job_status(
    job_id: str = Path(..., description="確認対象のジョブID", min_length=36, max_length=36) # UUID長制約
):
    """画像生成ジョブのステータスを確認します。"""
    status_data = controller.get_job_status_controller(job_id)
    if status_data is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    return status_data

# --- エンドポイント /jobs/{job_id}/image/{filename} (GET) ---
@router.get(
    "/jobs/{job_id}/image/{filename}",
    response_class=FileResponse
)
async def get_image_file(
    job_id: str = Path(..., description="ジョブID", min_length=36, max_length=36),
    filename: str = Path(..., description="取得対象の画像ファイル名")
):
    """ジョブによって生成された画像ファイルを取得します。"""
    file_path = controller.get_image_file_path_controller(job_id, filename)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="画像が見つかりません")
    
    # ファイル名が有効かチェック (セキュリティエラー回避)
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="無効なファイル名です")

    return FileResponse(file_path, media_type="image/jpeg", filename=filename)


# --- エンドポイント /jobs/{job_id}/download (GET) ---
@router.get(
    "/jobs/{job_id}/download",
    response_class=FileResponse
)
async def download_images_zip(
    job_id: str = Path(..., description="ダウンロード対象のジョブID", min_length=36, max_length=36)
):
    """ジョブの全画像を含む Zip ファイルを作成してダウンロードします。"""
    zip_path = controller.create_images_zip_controller(job_id)
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="ジョブが見つからないか、Zip の作成に失敗しました")
    
    # ユーザーに返す Zip ファイル名を生成
    # download_filename = f"tool03_images_{job_id}.zip" # <<< 古い行
    today_str = datetime.date.today().strftime('%Y%m%d') # 現在の日付 (YYYYMMDD) を取得
    download_filename = f"{today_str}_image.zip"         # 新しいファイル名を生成

    # FileResponse を使用して Zip ファイルを送信
    # background=BackgroundTask(os.remove, zip_path) # 送信後に Zip ファイルを自動削除 (任意)
    return FileResponse(
        path=zip_path,
        filename=download_filename,
        media_type='application/zip',
        # background=BackgroundTask(os.remove, zip_path) # 自動削除する場合はコメント解除
    )

# --- エンドポイント /jobs/{job_id}/upload (POST) ---
@router.post(
    "/jobs/{job_id}/upload",
    status_code=202 # 受理 (Accepted)
)
async def upload_images_to_ftp(
    job_id: str = Path(..., description="アップロード対象のジョブID", min_length=36, max_length=36),
    payload: Dict[str, str] = Body(..., example={"target": "gold"}),
    background_tasks: BackgroundTasks = BackgroundTasks() # 変数名の衝突を避ける
):
    """FTP (GOLD または R-Cabinet) への画像アップロードタスクをバックグラウンドで開始します。"""
    target = payload.get("target")
    if target not in ["gold", "rcabinet"]:
        raise HTTPException(status_code=400, detail="無効なターゲットが指定されました。'gold' または 'rcabinet' を使用してください。")

    # controller を呼び出してバックグラウンドアップロードを開始
    controller.start_ftp_upload_controller(job_id, target, background_tasks)

    # すぐに 202 を返す
    return {"message": f"ジョブ {job_id} の {target} へのFTPアップロードタスクがバックグラウンドで開始されました。"}