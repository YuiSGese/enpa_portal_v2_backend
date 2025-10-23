    # -*- coding: utf-8 -*-
import os
import uuid
import shutil
from pathlib import Path
from typing import List
from PIL import Image, ImageDraw, ImageFont
import asyncio

    # SỬA ĐƯỜNG DẪN IMPORT: Import schemas từ cùng thư mục (.)
from .schemas import Tool03ProductRowInput
    # Import config và logger giữ nguyên
from app.core.config import FONTS_DIR, TOOL03_TEMPLATES_DIR, TOOL03_ASSETS_DIR
from app.core.logger import logger

    # Đường dẫn lưu trữ Job (Giữ nguyên hoặc bạn có thể điều chỉnh nếu muốn)
JOB_STORAGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "tool03_jobs"
JOB_STORAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

    # === Các hàm Helper (Giữ nguyên) ===
def calculate_font_size(text: str, font_path: str, box_width: int, box_height: int) -> int:
        """Tính toán kích thước font tối đa để vừa với bounding box."""
        font_size = 1
        try:
            font = ImageFont.truetype(str(font_path), font_size)
            while True:
                bbox = font.getbbox(text)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                if width >= box_width or height >= box_height:
                    break
                font_size += 1
                font = ImageFont.truetype(str(font_path), font_size)
            return max(1, font_size - 1)
        except IOError:
            logger.error(f"Không thể mở file font: {font_path}")
            return 1
        except Exception as e:
            logger.error(f"Lỗi khi tính toán font size: {e}")
            return 1

    # === Factory Pattern (TODO) ===
class BaseImageFactory:
        def __init__(self):
            self.font_path_noto_sans_black = FONTS_DIR / "NotoSansJP-Black.ttf"
            # ...
            pass
        def draw(self, row_data: Tool03ProductRowInput) -> Image.Image:
            raise NotImplementedError
        def _place_text(self, draw: ImageDraw, params: dict):
            pass

    # === Service chính (Giữ nguyên logic) ===
async def generate_images_background(job_id: str, product_rows: List[Tool03ProductRowInput]):
        logger.info(f"[Job {job_id}] Bắt đầu xử lý {len(product_rows)} ảnh.")
        job_dir = JOB_STORAGE_BASE_DIR / job_id
        job_dir.mkdir(exist_ok=True)
        image_results = {}
        try:
            for index, row in enumerate(product_rows):
                logger.debug(f"[Job {job_id}] Đang xử lý ảnh {index + 1}/{len(product_rows)}: {row.productCode}")
                template_name = row.template
                template_file_name_base = template_name.replace("テンプレート", "template_")
                if template_name == "テンプレートB" and row.mobileStartDate:
                    template_file_name = f"{template_file_name_base}-2.jpg"
                else:
                    template_file_name = f"{template_file_name_base}.jpg"

                # SỬA ĐƯỜNG DẪN TEMPLATE: Sử dụng TOOL03_TEMPLATES_DIR từ config
                template_path = TOOL03_TEMPLATES_DIR / template_file_name
                if not template_path.exists():
                    logger.error(f"[Job {job_id}] Template không tồn tại: {template_path}")
                    continue

                try:
                    img = Image.open(template_path).convert("RGB")
                    draw = ImageDraw.Draw(img)
                    font_test = ImageFont.truetype(str(FONTS_DIR / "NotoSansJP-Black.ttf"), 30)
                    draw.text((10, 10), row.productCode, fill="black", font=font_test)
                    # === TODO: Logic vẽ chi tiết ===
                    output_filename = f"{row.productCode}.jpg"
                    output_path = job_dir / output_filename
                    img.save(output_path, "JPEG", quality=95)
                    image_results[row.id] = str(output_path)
                    img.close()
                except Exception as draw_error:
                    logger.error(f"[Job {job_id}] Lỗi khi vẽ ảnh cho {row.productCode}: {draw_error}", exc_info=True)

                await asyncio.sleep(0.05)

            logger.info(f"[Job {job_id}] Hoàn thành xử lý {len(image_results)} ảnh.")
            # TODO: Cập nhật trạng thái Job
        except Exception as e:
            logger.error(f"[Job {job_id}] Gặp lỗi nghiêm trọng: {e}", exc_info=True)
            # TODO: Cập nhật trạng thái Job thành "Failed"

    # === TODO: Tạo các lớp Factory ===
    
