import boto3
from botocore.exceptions import ClientError
import logging
import json
from typing import Dict, Any, Optional

# Import config từ file config.py lân cận
from . import config

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sqs_client():
    """
    Tạo và trả về một SQS client.
    
    Tự động cấu hình endpoint cho local (ElasticMQ) nếu
    AWS_ENDPOINT_URL_SQS được set trong .env.
    """
    
    # Kiểm tra xem có đang ở môi trường local (giả lập) không
    if config.AWS_ENDPOINT_URL_SQS:
        logger.info(f"Đang dùng SQS Giả lập (ElasticMQ) tại: {config.AWS_ENDPOINT_URL_SQS}")
        sqs_client = boto3.client(
            'sqs',
            endpoint_url=config.AWS_ENDPOINT_URL_SQS,
            aws_access_key_id='x', # Bất cứ giá trị gì (cho ElasticMQ)
            aws_secret_access_key='x', # Bất cứ giá trị gì
            region_name='us-east-1' # Bất cứ giá trị gì
        )
    else:
        # Đây là môi trường Production (hoặc staging)
        logger.info("Đang dùng AWS SQS Production (không có endpoint_url).")
        sqs_client = boto3.client(
            'sqs'
            # Trên AWS Fargate, chúng ta sẽ dùng IAM Role (OIDC)
        )
        
    return sqs_client

def get_queue_url(queue_name: str = config.SQS_QUEUE_NAME) -> str:
    """
    Lấy URL của SQS queue dựa trên tên của nó.
    Hàm này sẽ tự tạo queue nếu nó chưa tồn tại (chủ yếu cho local).
    """
    sqs_client = get_sqs_client()
    try:
        # Thử lấy URL của queue
        response = sqs_client.get_queue_url(QueueName=queue_name)
        return response['QueueUrl']
    except ClientError as e:
        if e.response['Error']['Code'] == 'QueueDoesNotExist':
            logger.warning(f"Queue '{queue_name}' không tồn tại. Đang thử tạo...")
            try:
                # Nếu là local (ElasticMQ), chúng ta có thể tự tạo
                if config.AWS_ENDPOINT_URL_SQS:
                    create_response = sqs_client.create_queue(QueueName=queue_name)
                    logger.info(f"Đã tự động tạo queue (local): {create_response['QueueUrl']}")
                    return create_response['QueueUrl']
                else:
                    # Nếu là production, đây là lỗi CẤU HÌNH
                    logger.error(f"LỖI NGHIÊM TRỌNG: Queue '{queue_name}' không tồn tại trên AWS Production!")
                    raise e
            except Exception as create_e:
                logger.error(f"Không thể tạo queue '{queue_name}': {create_e}")
                raise create_e
        else:
            logger.error(f"Lỗi SQS Client (get_queue_url): {e}")
            raise e

# --- HÀM CHO API (Gửi job) ---

def send_sqs_message(message_body: Dict[str, Any], queue_name: str = config.SQS_QUEUE_NAME) -> str | None:
    """
    Gửi một tin nhắn (dưới dạng dict) vào SQS queue.
    
    :param message_body: Một dict Python (sẽ được convert sang JSON)
    :return: MessageId nếu thành công, None nếu thất bại.
    """
    sqs_client = get_sqs_client()
    try:
        queue_url = get_queue_url(queue_name)
        
        # Convert dict Python thành chuỗi JSON
        json_message_body = json.dumps(message_body)
        
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json_message_body
        )
        message_id = response.get('MessageId')
        if message_id:
            logger.info(f"Gửi SQS thành công (Queue: {queue_name}), MessageID: {message_id}")
            return message_id
        else:
            logger.error(f"Gửi SQS thất bại (Không có MessageId): {response}")
            return None
            
    except ClientError as e:
        logger.error(f"Lỗi SQS Client (send_message): {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi không xác định khi gửi SQS: {e}")
        return None

# --- CÁC HÀM CHO WORKER (Nhận/Xóa job) ---

def receive_sqs_message(queue_name: str = config.SQS_QUEUE_NAME, max_messages: int = 1, wait_time: int = 5) -> Optional[Dict[str, Any]]:
    """
    Nhận một tin nhắn từ SQS (dùng cho Worker).
    Hàm này sử dụng Long Polling (wait_time).
    """
    sqs_client = get_sqs_client()
    try:
        queue_url = get_queue_url(queue_name)
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time, # Long Polling
            AttributeNames=['All'],
            MessageAttributeNames=['All']
        )
        
        messages = response.get('Messages', [])
        if messages:
            # Chỉ lấy tin nhắn đầu tiên
            return messages[0] 
        else:
            # Không có tin nhắn nào
            return None
            
    except ClientError as e:
        logger.error(f"Lỗi SQS Client (receive_message): {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi không xác định khi nhận SQS: {e}")
        return None

def delete_sqs_message(receipt_handle: str, queue_name: str = config.SQS_QUEUE_NAME):
    """
    Xóa một tin nhắn khỏi queue sau khi xử lý xong (dùng cho Worker).
    
    :param receipt_handle: "Tay cầm" của tin nhắn (lấy từ hàm receive_message)
    """
    sqs_client = get_sqs_client()
    try:
        queue_url = get_queue_url(queue_name)
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logger.info(f"Đã xóa SQS message (Receipt: ...{receipt_handle[-10:]})")
    except ClientError as e:
        logger.error(f"Lỗi SQS Client (delete_message): {e}")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi xóa SQS: {e}")