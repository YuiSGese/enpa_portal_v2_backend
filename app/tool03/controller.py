# -*- coding: utf-8 -*-
import uuid
from fastapi import BackgroundTasks, HTTPException
from typing import List, Optional, Dict
import os
import shutil
from app.core.logger import logger # logger をインポート

# 同一ディレクトリ (.) から schemas と service をインポート
from . import schemas
from . import service as tool03_service

# --- start_image_generation_job 関数 ---
def start_image_generation_job(
    product_rows: List[schemas.Tool03ProductRowInput],
    background_tasks: BackgroundTasks
) -> schemas.Tool03CreateJobResponse:
    if not product_rows:
        raise HTTPException(status_code=400, detail="商品リストを空にすることはできません")

    job_id = str(uuid.uuid4())
    # job をバックグラウンドタスクに追加
    background_tasks.add_task(tool03_service.generate_images_background, job_id, product_rows)

    # job_id をすぐに返す
    return schemas.Tool03CreateJobResponse(jobId=job_id, totalItems=len(product_rows))

# --- get_job_status_controller 関数 ---
def get_job_status_controller(job_id: str) -> Optional[schemas.Tool03JobStatusResponse]:
    status_dict = tool03_service.get_job_status(job_id)
    if status_dict:
        # --- job_id を辞書に追加 ---
        status_dict_with_id = {"jobId": job_id, **status_dict}
        # ---------------------------
        try:
            # dict を Pydantic モデルに変換して検証し、返す
            return schemas.Tool03JobStatusResponse(**status_dict_with_id)
        except Exception as e:
            # 予期せぬ検証エラーがあればログに記録
            logger.error(f"ジョブ {job_id} の JobStatusResponse 検証エラー: {e}")
            logger.error(f"元のデータ: {status_dict_with_id}")
            # データ構造がモデルと一致しない場合は 500 エラーを返す
            raise HTTPException(status_code=500, detail="ジョブステータスデータの処理エラー。")
    
    # service がジョブを見つけられない場合は None を返す (router が 404 を返す)
    return None


# --- get_image_file_path_controller 関数 ---
def get_image_file_path_controller(job_id: str, filename: str) -> Optional[str]:
     job_dir = tool03_service.JOB_STORAGE_BASE_DIR / job_id
     file_path = job_dir / filename
     # パストラバーサル攻撃の試行をチェック
     if not str(file_path.resolve()).startswith(str(job_dir.resolve())):
          logger.warning(f"パストラバーサルの試行: {job_id}/{filename}")
          return None
     if file_path.is_file():
          return str(file_path)
     return None

# --- create_images_zip_controller 関数 ---
def create_images_zip_controller(job_id: str) -> Optional[str]:
    try:
        zip_path = tool03_service.create_job_zip_archive(job_id)
        return zip_path
    except FileNotFoundError:
         raise HTTPException(status_code=404, detail="ジョブディレクトリが見つかりません。")
    except Exception as e:
         logger.error(f"ジョブ {job_id} の Zip 作成エラー: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail="Zip ファイルの作成に失敗しました。")

# --- start_ftp_upload_controller 関数 ---
def start_ftp_upload_controller(job_id: str, target: str, background_tasks: BackgroundTasks):
    job_status = tool03_service.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません。")
    
    # 必要に応じて、ジョブが完了しているかどうかのチェック (現在はコメントアウト)
    # if job_status.get("status") not in ["Completed", "Completed with errors"]:
    #     raise HTTPException(status_code=400, detail="ジョブはまだ完了していません。")

    logger.info(f"ジョブ {job_id} の {target} への FTP アップロードタスクをバックグラウンドに追加します。")
    background_tasks.add_task(tool03_service.upload_job_images_to_ftp, job_id, target)

# --- start_image_regeneration_job 関数 ---
def start_image_regeneration_job(
    job_id: str,
    modified_rows: List[schemas.Tool03ProductRowInput],
    background_tasks: BackgroundTasks
):
    """指定された画像を再生成するためのバックグラウンドタスクを追加します。"""
    # ジョブが存在するか確認
    existing_job_status = tool03_service.get_job_status(job_id)
    if not existing_job_status:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    # 必要に応じて、ジョブが失敗状態でないかチェック (現在はコメントアウト)
    # if existing_job_status.get("status") == "Failed":
    #     raise HTTPException(status_code=400, detail="失敗したジョブは更新できません。")

    logger.info(f"ジョブ {job_id} に {len(modified_rows)} 件の画像再生成タスクを追加します。")
    background_tasks.add_task(tool03_service.regenerate_specific_images_background, job_id, modified_rows)
