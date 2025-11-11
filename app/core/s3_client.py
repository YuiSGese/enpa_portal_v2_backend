import boto3
from botocore.exceptions import ClientError
import logging
import os
from pathlib import Path
from typing import Optional

# Import config từ file config.py lân cận
from . import config

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SỬA LỖI (NoSuchBucket): Thêm AWS_REGION vào config ---
AWS_REGION = config.AWS_REGION
# --------------------------------------------------------

def get_s3_client():
    """
    Tạo và trả về một S3 client (dùng cho các thao tác API cấp thấp).
    
    Tự động cấu hình endpoint cho local (MinIO) nếu
    AWS_ENDPOINT_URL_S3 được set trong .env.
    """
    
    # Kiểm tra xem có đang ở môi trường local (giả lập) không
    if config.AWS_ENDPOINT_URL_S3:
        logger.info(f"Đang dùng S3 Giả lập (MinIO) tại: {config.AWS_ENDPOINT_URL_S3}")
        s3_client = boto3.client(
            's3',
            endpoint_url=config.AWS_ENDPOINT_URL_S3,
            aws_access_key_id='minioadmin', # (Theo docker-compose)
            aws_secret_access_key='minioadmin', # (Theo docker-compose)
            # --- SỬA LỖI (NoSuchBucket): Thêm region_name ---
            region_name=AWS_REGION 
        )
    else:
        # Đây là môi trường Production (hoặc staging)
        logger.info("Đang dùng AWS S3 Production (không có endpoint_url).")
        s3_client = boto3.client(
            's3'
            # (Trên AWS Fargate, chúng ta sẽ dùng IAM Role (OIDC))
            # (Region sẽ được tự động lấy từ môi trường Fargate)
        )
        
    return s3_client

def get_s3_resource():
    """
    Tạo và trả về một S3 resource (dùng cho các thao tác upload/download).
    """
    
    if config.AWS_ENDPOINT_URL_S3:
        # (Local)
        s3_resource = boto3.resource(
            's3',
            endpoint_url=config.AWS_ENDPOINT_URL_S3,
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin',
             # --- SỬA LỖI (NoSuchBucket): Thêm region_name ---
            region_name=AWS_REGION
        )
    else:
        # (Production)
        s3_resource = boto3.resource('s3')
        
    return s3_resource
    
# === HÀM CHO WORKER (Upload/Download) ===

def upload_file_to_s3(local_file_path: str, object_key: str, bucket_name: str = config.S3_BUCKET_NAME) -> bool:
    """
    Upload một file (từ ổ cứng local) lên S3.
    
    :param local_file_path: Đường dẫn file trên máy (ví dụ: /tmp/image.jpg)
    :param object_key: Tên file trên S3 (ví dụ: tool03/job_id/image.jpg)
    :return: True nếu thành công, False nếu thất bại.
    """
    s3_resource = get_s3_resource()
    try:
        s3_resource.Bucket(bucket_name).upload_file(local_file_path, object_key)
        logger.info(f"Upload S3 thành công: {local_file_path} -> s3://{bucket_name}/{object_key}")
        return True
        
    except ClientError as e:
        logger.error(f"Lỗi S3 Client (upload_file) cho {object_key}: {e}")
        return False
    except FileNotFoundError:
        logger.error(f"Lỗi: File local không tồn tại (upload_file): {local_file_path}")
        return False
    except Exception as e:
        logger.error(f"Lỗi không xác định khi upload S3: {e}")
        return False

def download_file_from_s3(object_key: str, local_file_path: str, bucket_name: str = config.S3_BUCKET_NAME) -> bool:
    """
    Download một file (từ S3) về ổ cứng local.
    
    :param object_key: Tên file trên S3 (ví dụ: tool03/job_id/image.jpg)
    :param local_file_path: Nơi lưu file (ví dụ: /tmp/image.jpg)
    :return: True nếu thành công, False nếu thất bại.
    """
    s3_resource = get_s3_resource()
    try:
        # (Đảm bảo thư mục cha tồn tại)
        Path(local_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        s3_resource.Bucket(bucket_name).download_file(object_key, local_file_path)
        logger.info(f"Download S3 thành công: s3://{bucket_name}/{object_key} -> {local_file_path}")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
             logger.error(f"Lỗi 404: File không tồn tại trên S3 (download_file): {object_key}")
        else:
             logger.error(f"Lỗi S3 Client (download_file) cho {object_key}: {e}")
        return False
    except Exception as e:
        logger.error(f"Lỗi không xác định khi download S3: {e}")
        return False

# === HÀM CHO API (Tạo Link) / WORKER (Dọn dẹp) ===

def create_presigned_url(object_key: str, bucket_name: str = config.S3_BUCKET_NAME, expiration_seconds: int = 3600) -> str | None:
    """
    Tạo một S3 Presigned URL (link download có thời hạn).
    """
    s3_client = get_s3_client()
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration_seconds
        )
        return response
        
    except ClientError as e:
        logger.error(f"Lỗi S3 Client (presigned_url) cho {object_key}: {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi không xác định khi tạo S3 Presigned URL: {e}")
        return None

def delete_files_by_prefix_from_s3(prefix: str, bucket_name: str = config.S3_BUCKET_NAME) -> bool:
    """
    Xóa tất cả các file trên S3 có chung một prefix (thư mục).
    (Dùng cho Worker khi PATCH job).
    
    :param prefix: Đường dẫn thư mục (ví dụ: tool03/job_id/)
    :return: True (nếu logic chạy xong), False (nếu có lỗi nghiêm trọng)
    """
    s3_client = get_s3_client()
    s3_resource = get_s3_resource()
    
    delete_count = 0
    error_count = 0
    
    try:
        # 1. Liệt kê tất cả objects
        # (Phải dùng paginator nếu có > 1000 file, nhưng ở đây dùng cách đơn giản)
        
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        objects_to_delete = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})

        if not objects_to_delete:
            logger.info(f"Dọn dẹp S3 (Prefix: {prefix}): Không tìm thấy file nào để xóa.")
            return True # (Không có gì để xóa -> Thành công)
            
        logger.info(f"Dọn dẹp S3 (Prefix: {prefix}): Tìm thấy {len(objects_to_delete)} file. Đang xóa...")

        # 2. Xóa (Delete)
        bucket = s3_resource.Bucket(bucket_name)
        response = bucket.delete_objects(
            Delete={
                'Objects': objects_to_delete,
                'Quiet': False # (Muốn biết kết quả)
            }
        )
        
        deleted_list = response.get('Deleted', [])
        delete_count = len(deleted_list)
        
        error_list = response.get('Errors', [])
        error_count = len(error_list)
        if error_count > 0:
             logger.error(f"Dọn dẹp S3 (Prefix: {prefix}): Xóa thành công {delete_count}, LỖI {error_count}. Lỗi đầu tiên: {error_list[0]}")
             
        logger.info(f"Dọn dẹp S3 (Prefix: {prefix}) hoàn tất. Đã xóa: {delete_count}, Lỗi: {error_count}.")
        
        # (Chúng ta trả về True ngay cả khi có lỗi xóa, 
        # vì đây không phải lỗi hệ thống (như CSDL sập)
        # mà là lỗi nghiệp vụ (S3 permission...))
        return True

    except ClientError as e:
        # (Lỗi nghiêm trọng, ví dụ: Access Denied, NoSuchBucket)
        logger.error(f"Lỗi S3 Client (delete_files_by_prefix) cho {prefix}: {e}")
        return False # (Báo Worker hủy job)
    except Exception as e:
        logger.error(f"Lỗi không xác định khi dọn dẹp S3: {e}")
        return False # (Báo Worker hủy job)