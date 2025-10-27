# -*- coding: utf-8 -*-
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import asyncio
from decimal import Decimal, ROUND_HALF_UP
import time # Thêm time để lưu timestamp
import tempfile
import ftplib # <<< IMPORT THÊM CHO FTP

# Import schemas từ cùng thư mục (.)
from .schemas import Tool03ProductRowInput, Tool03JobStatusResponse, Tool03ImageResult # Thêm schemas mới
# Import config và logger giữ nguyên
from app.core.config import FONTS_DIR, TOOL03_TEMPLATES_DIR
from app.core.logger import logger

# Đường dẫn lưu trữ Job
JOB_STORAGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "tool03_jobs"
JOB_STORAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

# --- Nơi lưu trữ trạng thái Job (In-memory) ---
# Cấu trúc: { job_id: {"status": str, "progress": int, "total": int, "results": Dict[str, Tool03ImageResult], "startTime": float, "endTime": float | None, "message": str | None} }
job_tracker: Dict[str, Dict[str, Any]] = {}
# ----------------------------------------------


# === Các hàm Helper (Giữ nguyên) ===
def calculate_font_size(text: str, font_path: str, box_width: int, box_height: int) -> int:
    """Tính toán kích thước font tối đa để vừa với bounding box."""
    font_size = 1
    max_font_size = box_height + 10 # Giới hạn trên để tránh vòng lặp vô hạn
    try:
        # Tăng dần font size cho đến khi vượt quá box
        while font_size <= max_font_size:
            font = ImageFont.truetype(str(font_path), font_size)
            # Lấy bounding box của text
            bbox = font.getbbox(text) # (left, top, right, bottom) relative to (0,0)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]

            if width > box_width or height > box_height:
                # Nếu vượt quá, trả về size trước đó (ít nhất là 1)
                return max(1, font_size - 1)
            font_size += 1
        # Nếu không vượt quá ngay cả ở max_font_size, trả về max_font_size
        return max(1, font_size - 1)
    except IOError:
        logger.error(f"Không thể mở file font: {font_path}")
        return 1 # Trả về size mặc định nhỏ
    except Exception as e:
        logger.error(f"Lỗi khi tính toán font size cho font '{font_path}': {e}")
        return 1 # Trả về size mặc định nhỏ


# === Factory Pattern (Giữ nguyên các class Factory đã tạo) ===

class FactoryRegistry:
    def __init__(self):
        self._factories: Dict[str, type] = {} # Lưu class, không phải instance

    def register_factory(self, key: str, factory_cls: type):
        """Đăng ký một class Factory với một key."""
        if not issubclass(factory_cls, BaseImageFactory):
            raise TypeError("factory_cls phải kế thừa từ BaseImageFactory")
        self._factories[key] = factory_cls
        logger.debug(f"Đã đăng ký Factory: {key} -> {factory_cls.__name__}")

    def get_factory(self, key: str) -> 'BaseImageFactory':
        """Lấy một instance của Factory dựa trên key."""
        logger.debug(f"Đang tìm Factory cho key: '{key}'")
        factory_cls = self._factories.get(key)

        # Nếu không tìm thấy key chính xác (ví dụ 'B-2'),
        # thử tìm key cơ bản (ví dụ 'B')
        if not factory_cls:
            base_key = key.split('-')[0]
            logger.debug(f"Không tìm thấy key '{key}', thử tìm key cơ bản: '{base_key}'")
            factory_cls = self._factories.get(base_key)

            # Nếu vẫn không tìm thấy key cơ bản
            if not factory_cls:
                logger.error(f"Template Factory không tồn tại cho cả key '{key}' và base key '{base_key}'")
                raise ValueError(f"Template Factory không tồn tại: {key}")

        logger.debug(f"Sử dụng Factory class: {factory_cls.__name__} cho key '{key}'")
        # Tạo instance mới mỗi lần gọi
        return factory_cls()

factory_registry = FactoryRegistry()

class BaseImageFactory:
    # --- Định nghĩa font và màu (Giữ nguyên) ---
    def __init__(self):
        self.font_path_arial=FONTS_DIR/'ARIALNB.TTF';self.font_path_yugothB=FONTS_DIR/'YuGothB.ttc';self.font_path_noto_sans_black=FONTS_DIR/'NotoSansJP-Black.ttf';self.font_path_noto_sans_bold=FONTS_DIR/'NotoSansJP-Bold.ttf';self.font_path_noto_sans_medium=FONTS_DIR/'NotoSansJP-Medium.ttf';self.font_path_noto_serif_extrabold=FONTS_DIR/'NotoSerifJP-ExtraBold.ttf';self.font_path_reddit=FONTS_DIR/'RedditSans-ExtraBold.ttf';self.font_path_reddit_condensed_extrabold=FONTS_DIR/'RedditSansCondensed-ExtraBold.ttf';self.font_path_shippori_bold=FONTS_DIR/'ShipporiMinchoB1-Bold.ttf';self.font_path_public_sans_bold=FONTS_DIR/'PublicSans-Bold.ttf'
        self.WHITE=(255,255,255);self.BLACK=(0,0,0);self.RED=(255,0,0) # Màu RED mặc định
        self.width=800;self.height=800 # Kích thước mặc định
        # Tham số mặc định cho ngày giờ mobile
        self.mobile_start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':35,'y1':1250,'x2':475,'y2':1319,'align':'right'};
        self.mobile_end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':535,'y1':1250,'x2':975,'y2':1319,'align':'left'}

    # --- Các hàm helper (Giữ nguyên) ---
    def get_template_path(self, template_key: str, has_mobile_data: bool) -> Path:
        base_key = template_key.split('-')[0] # Lấy key gốc (vd: 'B' từ 'B-2')
        template_file_name_base = f"template_{base_key}"
        suffix = ".jpg"

        mobile_template_path = TOOL03_TEMPLATES_DIR / f"{template_file_name_base}-2{suffix}"
        normal_template_path = TOOL03_TEMPLATES_DIR / f"{template_file_name_base}{suffix}"

        # Ưu tiên template mobile nếu có dữ liệu mobile và file tồn tại
        if has_mobile_data and mobile_template_path.exists():
            logger.debug(f"Sử dụng template mobile: {mobile_template_path}")
            return mobile_template_path

        # Nếu không, dùng template thường (phải tồn tại)
        if not normal_template_path.exists():
            logger.error(f"Template cơ bản không tồn tại: {normal_template_path}")
            raise FileNotFoundError(f"Template cơ bản không tồn tại: {normal_template_path}")

        logger.debug(f"Sử dụng template thường: {normal_template_path}")
        return normal_template_path

    def _get_text_size(self, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        try:
            bbox = font.getbbox(text) # (left, top, right, bottom)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height
        except Exception as e:
            logger.error(f"Lỗi _get_text_size cho '{text}': {e}")
            return 0, 0

    def _place_text(self, draw: ImageDraw, params: Dict[str, Any]):
        text = str(params.get('text', ''))
        if not text:
            logger.warning("Attempted to place empty text.")
            return

        font_path = str(params['font_path'])
        font_color = params['font_color']
        x1, y1, x2, y2 = params['x1'], params['y1'], params['x2'], params['y2']
        align = params.get('align', 'left')
        box_width = x2 - x1
        box_height = y2 - y1

        if box_width <= 0 or box_height <= 0:
            logger.warning(f"Invalid bounding box for text '{text}': ({x1},{y1})-({x2},{y2})")
            return

        font_size = calculate_font_size(text, font_path, box_width, box_height)
        if font_size <= 0:
             logger.warning(f"Calculated font size is zero or negative for text '{text}' in box ({x1},{y1})-({x2},{y2})")
             return # Không vẽ nếu font size <= 0

        try:
            font = ImageFont.truetype(font_path, font_size)
            text_width, text_height_bbox = self._get_text_size(text, font) # Chiều cao dựa trên bbox

            # Tính toán vị trí x dựa trên align
            if align == 'left':
                x = x1
            elif align == 'center':
                x = x1 + (box_width - text_width) / 2
            elif align == 'right':
                x = x2 - text_width
            else: # Mặc định là left
                x = x1

            # Tính toán vị trí y để căn giữa theo chiều dọc trong box
            # Lấy thông tin ascent/descent từ font để căn chuẩn hơn
            bbox = font.getbbox(text) # (left, top, right, bottom) relative to baseline
            text_actual_height = bbox[3] - bbox[1] # Chiều cao thực tế của ký tự
            y_offset = bbox[1] # Độ lệch của top so với baseline (thường là số âm)
            y = y1 + (box_height - text_actual_height) / 2 - y_offset

            # Vẽ text
            draw.text((x, y), text, fill=font_color, font=font)
        except Exception as e:
            logger.error(f"Lỗi khi vẽ text '{text}' với font {font_path} size {font_size}: {e}", exc_info=True)

    def _format_price(self, price_str: Optional[str]) -> str:
        if price_str is None: return ""
        try:
            # Làm tròn về số nguyên gần nhất trước khi format
            price_decimal = Decimal(price_str).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            return f"{int(price_decimal):,}" # Format với dấu phẩy
        except Exception:
            return str(price_str) # Trả về chuỗi gốc nếu không phải số

    def _calculate_discount_display(self, regular_price_str: Optional[str], sale_price_str: Optional[str], discount_type: Optional[str]) -> str:
        if regular_price_str is None or sale_price_str is None: return ""
        try:
            regular_price = Decimal(regular_price_str)
            sale_price = Decimal(sale_price_str)
            if regular_price <= sale_price: return "" # Không hiển thị nếu giá sale >= giá gốc

            difference = regular_price - sale_price

            if discount_type == "yen":
                # Làm tròn về số nguyên gần nhất
                discount_val = difference.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                return f"{int(discount_val):,}" # Format số tiền
            elif discount_type == "percent":
                 # Tính phần trăm, làm tròn về số nguyên gần nhất
                percentage = (difference / regular_price * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                return f"{int(percentage)}%" # Thêm ký tự %
            else: # Mặc định là percent nếu không rõ
                 percentage = (difference / regular_price * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                 return f"{int(percentage)}%"

        except Exception as e:
            logger.warning(f"Lỗi tính discount ({regular_price_str}, {sale_price_str}, {discount_type}): {e}")
            return ""

    def _place_price_group(self, draw: ImageDraw, price_params: Dict, unit_params: Dict, suffix_params: Dict):
        price_text = str(price_params.get('text', ''))
        unit_text = str(unit_params.get('text', ''))
        suffix_text = str(suffix_params.get('text', ''))

        if not price_text: return # Không vẽ nếu không có giá

        gap_width = 5 # Khoảng cách giữa các phần tử

        try:
            price_font = ImageFont.truetype(str(price_params['font_path']), price_params['font_size'])
            unit_font = ImageFont.truetype(str(unit_params['font_path']), unit_params['font_size']) if unit_text else None
            suffix_font = ImageFont.truetype(str(suffix_params['font_path']), suffix_params['font_size']) if suffix_text else None

            price_w, price_h = self._get_text_size(price_text, price_font)
            unit_w, unit_h = self._get_text_size(unit_text, unit_font) if unit_font else (0, 0)
            suffix_w, suffix_h = self._get_text_size(suffix_text, suffix_font) if suffix_font else (0, 0)

            # Tính tổng chiều rộng của cả nhóm
            total_width = price_w
            if unit_text: total_width += gap_width + unit_w
            if suffix_text: total_width += gap_width + suffix_w

            # Tính vị trí bắt đầu (x) để căn giữa nhóm trong container
            container_width = price_params['x_end'] - price_params['x_origin']
            start_x = price_params['x_origin'] + (container_width - total_width) / 2

            # --- Vẽ giá ---
            price_y = price_params['y_origin']
            draw.text((start_x, price_y), price_text, fill=price_params['font_color'], font=price_font)
            current_x = start_x + price_w # Cập nhật vị trí x hiện tại

            # --- Vẽ đơn vị (nếu có) ---
            if unit_font:
                current_x += gap_width # Thêm khoảng cách
                unit_y = price_y + unit_params.get('dy', 0) # Áp dụng độ lệch y (nếu có)
                draw.text((current_x, unit_y), unit_text, fill=unit_params['font_color'], font=unit_font)
                current_x += unit_w # Cập nhật vị trí x

            # --- Vẽ hậu tố (suffix) (nếu có) ---
            if suffix_font:
                current_x += gap_width # Thêm khoảng cách
                suffix_y = price_y + suffix_params.get('dy', 0) # Áp dụng độ lệch y (nếu có)
                draw.text((current_x, suffix_y), suffix_text, fill=suffix_params['font_color'], font=suffix_font)

        except Exception as e:
            logger.error(f"Lỗi _place_price_group cho giá '{price_text}': {e}", exc_info=True)


    def draw(self, row_data: Tool03ProductRowInput, template_key: str) -> Image.Image:
        """Vẽ ảnh dựa trên dữ liệu hàng và template key."""
        has_mobile_data = bool(row_data.mobileStartDate and row_data.mobileEndDate)
        try:
            template_path = self.get_template_path(template_key, has_mobile_data)

            # Cập nhật chiều cao nếu là template mobile và file tồn tại
            if has_mobile_data and template_path.name.endswith("-2.jpg") and hasattr(self, '_draw_mobile_details'):
                # Giả định chiều cao mobile là 1370 dựa trên V1
                original_height = self.height
                self.height = 1370
                logger.debug(f"Tạm thời đặt height = 1370 cho mobile template {template_path.name}")


            img = Image.open(template_path).convert("RGB")
            draw_obj = ImageDraw.Draw(img)

            # Vẽ các chi tiết chính
            self._draw_details(draw_obj, row_data)

            # Vẽ thêm chi tiết mobile nếu cần
            if has_mobile_data and hasattr(self, '_draw_mobile_details') and callable(getattr(self, '_draw_mobile_details')):
                 # Kiểm tra lại xem có nên gọi không nếu template thường được dùng
                 if template_path.name.endswith("-2.jpg"):
                     logger.debug(f"Gọi _draw_mobile_details cho {template_key}")
                     self._draw_mobile_details(draw_obj, row_data)
                 else:
                     logger.warning(f"Có dữ liệu mobile nhưng không tìm thấy template mobile cho {template_key}, bỏ qua vẽ mobile details.")

             # Khôi phục chiều cao gốc nếu đã thay đổi
            if 'original_height' in locals():
                self.height = original_height

            return img

        except FileNotFoundError:
            logger.error(f"Không tìm thấy file template cho key '{template_key}', mobile: {has_mobile_data}")
            raise # Ném lại lỗi để generate_images_background bắt
        except Exception as e:
            logger.error(f"Lỗi không xác định khi vẽ ảnh cho template key '{template_key}': {e}", exc_info=True)
            raise # Ném lại lỗi

    # --- Các hàm cần được implement bởi lớp con ---
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        """Vẽ các chi tiết chính lên ảnh (bắt buộc implement)."""
        raise NotImplementedError

    def _draw_mobile_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        """Vẽ thêm các chi tiết cho Rakuten Mobile (tùy chọn implement)."""
        # Lớp con nào hỗ trợ mobile sẽ override hàm này
        logger.debug(f"Gọi _draw_mobile_details mặc định cho {self.__class__.__name__}")
        self._place_text(draw, {**self.mobile_start_datetime_params, 'text': row_data.mobileStartDate})
        self._place_text(draw, {**self.mobile_end_datetime_params, 'text': row_data.mobileEndDate})


# --- Triển khai các Factory ---
# (LƯU Ý: Giữ nguyên toàn bộ code của các class FactoryTypeA, B, C, D, E, F và các lớp con B2, C2, D2, E2, F2 ở đây)
# --- NOTE: Keep all the code for FactoryTypeA, B, C, D, E, F and their subclasses B2, C2, D2, E2, F2 here ---
class FactoryTypeA(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 800, 880
        self.RED = (189, 41, 39) # Override màu RED
        # --- Định nghĩa params cho các element ---
        self.start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.BLACK,'x1':270,'y1':70,'x2':771,'y2':135,'align':'center'}
        self.end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.BLACK,'x1':270,'y1':180,'x2':771,'y2':245,'align':'center'}
        self.message_params={'font_path':self.font_path_noto_sans_black,'font_color':self.RED,'x1':30,'y1':280,'x2':770,'y2':370,'align':'center'}
        # --- Định nghĩa các nhóm giá ---
        self.normal_price_group={
            'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':60,'font_color':self.WHITE,'x_origin':330,'x_end':740,'y_origin':395},
            'unit':  {'text':'円', 'font_path':self.font_path_noto_sans_black, 'font_size':30,'font_color':self.WHITE,'dy':20},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':25,'font_color':self.WHITE,'dy':25}
        }
        self.discount_group={
             'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':85,'font_color':self.BLACK,'x_origin':0,'x_end':self.width,'y_origin':485},
             'unit':  {'text':'', 'font_path':self.font_path_noto_sans_black, 'font_size':50,'font_color':self.BLACK,'dy':20}, # Đơn vị sẽ là % hoặc 円
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.BLACK,'dy':45}
        }
        self.sale_price_group={
            'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':160,'font_color':self.RED,'x_origin':0,'x_end':self.width,'y_origin':620},
            'unit':  {'text':'円', 'font_path':self.font_path_noto_sans_black, 'font_size':50,'font_color':self.RED,'dy':90},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':20,'font_color':self.RED,'dy':70}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        # Vẽ ngày giờ và message
        self._place_text(draw, {**self.start_datetime_params, 'text': row_data.startDate})
        self._place_text(draw, {**self.end_datetime_params, 'text': row_data.endDate})
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""}) # Đảm bảo không phải None

        # Chuẩn bị dữ liệu giá
        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)

        # Chuẩn bị dữ liệu discount
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        # Tách số và đơn vị (%)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text

        # Vẽ các nhóm giá
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('A', FactoryTypeA)

class FactoryTypeB(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1000, 1000
        self.YELLOW=(255,239,0); self.RED=(215,0,0)
        self.start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.RED,'x1':25,'y1':162,'x2':465,'y2':231,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.RED,'x1':555,'y1':162,'x2':995,'y2':231,'align':'left'}
        self.message_params={'font_path':self.font_path_noto_sans_black,'font_color':self.RED,'x1':107,'y1':38,'x2':894,'y2':148,'align':'center'}
        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_reddit,'font_size':130,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':370},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.WHITE,'dy':35},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':self.WHITE,'dy':65}
        }
        self.discount_group={
             'price': {'text':'','font_path':self.font_path_reddit,'font_size':95,'font_color':self.RED,'x_origin':0,'x_end':self.width,'y_origin':540},
             'unit':  {'text':'','font_path':self.font_path_noto_sans_black,'font_size':60,'font_color':self.RED,'dy':20},
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':40,'font_color':self.RED,'dy':45}
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_reddit,'font_size':230,'font_color':self.YELLOW,'x_origin':0,'x_end':self.width,'y_origin':660},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.YELLOW,'dy':130},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.YELLOW,'dy':100}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': row_data.startDate})
        self._place_text(draw, {**self.end_datetime_params, 'text': row_data.endDate})
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})
        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('B', FactoryTypeB)

class FactoryTypeB2(FactoryTypeB):
    pass
factory_registry.register_factory('B-2', FactoryTypeB2)

class FactoryTypeC(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1000, 1000
        self.YELLOW=(235, 210, 150); self.RED=(150,0,0)
        self.start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        self.message_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.WHITE,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':self.WHITE,'dy':95}
        }
        self.discount_group={
             'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':95,'font_color':self.RED,'x_origin':0,'x_end':self.width,'y_origin':530},
             'unit':  {'text':'','font_path':self.font_path_shippori_bold,'font_size':60,'font_color':self.RED,'dy':40},
             'suffix':{'text':'OFF','font_path':self.font_path_shippori_bold,'font_size':40,'font_color':self.RED,'dy':65}
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':self.YELLOW,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.YELLOW,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':self.YELLOW,'dy':115}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': row_data.startDate})
        self._place_text(draw, {**self.end_datetime_params, 'text': row_data.endDate})
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})
        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('C', FactoryTypeC)

class FactoryTypeC2(FactoryTypeC):
    pass
factory_registry.register_factory('C-2', FactoryTypeC2)

class FactoryTypeD(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1000, 1000
        self.BROWN=(90,70,50); self.RED=(215,0,0)
        self.start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        self.message_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':130,'font_color':self.BROWN,'x_origin':0,'x_end':self.width,'y_origin':380},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.BROWN,'dy':35},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':self.BROWN,'dy':60}
        }
        self.discount_group={
             'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':85,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':550},
             'unit':  {'text':'','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':self.WHITE,'dy':15},
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.WHITE,'dy':40}
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':200,'font_color':self.RED,'x_origin':0,'x_end':self.width,'y_origin':700},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.RED,'dy':95},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.RED,'dy':65}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': row_data.startDate})
        self._place_text(draw, {**self.end_datetime_params, 'text': row_data.endDate})
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})
        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('D', FactoryTypeD)

class FactoryTypeD2(FactoryTypeD):
    pass
factory_registry.register_factory('D-2', FactoryTypeD2)

class FactoryTypeE(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1000, 1000
        self.SILVER=(204,204,204); self.GOLD=(235, 210, 150)
        self.start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':25,'y1':200,'x2':465,'y2':265,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':530,'y1':200,'x2':960,'y2':265,'align':'left'}
        self.message_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':self.SILVER,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.SILVER,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':self.SILVER,'dy':95}
        }
        self.discount_params={ # Dùng _place_text riêng cho discount
            'font_path':self.font_path_shippori_bold,
            'font_color':self.GOLD,
            'x1': 645, 'y1': 620, 'x2': 965, 'y2': 670,
            'align':'center'
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':self.GOLD,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.GOLD,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':self.GOLD,'dy':115}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': row_data.startDate})
        self._place_text(draw, {**self.end_datetime_params, 'text': row_data.endDate})
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})

        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)

        # Xử lý hiển thị discount riêng cho template E
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_display_text = ""
        if discount_text_val:
             discount_number = discount_text_val.replace('%', '').replace('円', '')
             if '%' in discount_text_val:
                 discount_display_text = f"{discount_number}%OFF"
             elif '円' in discount_text_val:
                 discount_display_text = f"{discount_number}円OFF"

        self._place_text(draw, {**self.discount_params, 'text': discount_display_text})

        # Vẽ các nhóm giá còn lại
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('E', FactoryTypeE)

class FactoryTypeE2(FactoryTypeE):
    pass
factory_registry.register_factory('E-2', FactoryTypeE2)

class FactoryTypeF(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1000, 1000
        self.BLACK=(93, 95, 96); self.GOLD=(210, 172, 67)
        self.start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.GOLD,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.GOLD,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        self.message_params={'font_path':self.font_path_shippori_bold,'font_color':self.GOLD,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':self.BLACK,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.BLACK,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':self.BLACK,'dy':95}
        }
        self.discount_group={
             'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':95,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':530},
             'unit':  {'text':'','font_path':self.font_path_shippori_bold,'font_size':60,'font_color':self.WHITE,'dy':40},
             'suffix':{'text':'OFF','font_path':self.font_path_shippori_bold,'font_size':40,'font_color':self.WHITE,'dy':65}
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':self.GOLD,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.GOLD,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':self.GOLD,'dy':115}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': row_data.startDate})
        self._place_text(draw, {**self.end_datetime_params, 'text': row_data.endDate})
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})
        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('F', FactoryTypeF)

class FactoryTypeF2(FactoryTypeF):
    pass
factory_registry.register_factory('F-2', FactoryTypeF2)


# === Service chính (Background Task - Đã sửa lỗi break) ===
async def generate_images_background(job_id: str, product_rows: List[Tool03ProductRowInput]):
    """Tác vụ nền để tạo ảnh."""
    logger.info(f"[Job {job_id}] Bắt đầu xử lý {len(product_rows)} ảnh.")
    job_dir = JOB_STORAGE_BASE_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    start_time = time.time()
    initial_job_data = {
        "status": "Processing", "progress": 0, "total": len(product_rows),
        "results": {}, "startTime": start_time, "endTime": None, "message": None
    }
    job_tracker[job_id] = initial_job_data
    error_count = 0
    final_status = "Processing" # Trạng thái cuối cùng của job

    try:
        for index, row in enumerate(product_rows):
            logger.debug(f"[Job {job_id}] Đang xử lý ảnh {index + 1}/{len(product_rows)}: {row.productCode}")
            row_id = row.id
            current_result = Tool03ImageResult(status="Processing", filename=None, message=None)

            template_name = row.template or "テンプレートA" # Mặc định là A nếu rỗng
            base_key = template_name.replace("テンプレート", "") # Bỏ tiền tố
            factory_key = base_key # Key mặc định
            has_mobile_data = bool(row.mobileStartDate and row.mobileEndDate)
            potential_mobile_key = f"{base_key}-2"

            if has_mobile_data and potential_mobile_key in factory_registry._factories:
                factory_key = potential_mobile_key # Ưu tiên key mobile

            logger.debug(f"[Job {job_id}] Processing row {index+1}:")
            logger.debug(f"  - Received template name: '{row.template}'")
            logger.debug(f"  - Calculated base_key: '{base_key}'")
            logger.debug(f"  - Final factory_key: '{factory_key}'")

            try:
                factory = factory_registry.get_factory(factory_key)
                img: Image.Image = factory.draw(row, factory_key) # Truyền factory_key vào draw
                output_filename = f"{row.productCode}.jpg"
                output_path = job_dir / output_filename
                img.save(output_path, "JPEG", quality=95)
                current_result.status = "Success"
                current_result.filename = output_filename
                img.close()

            except (FileNotFoundError, ValueError, NotImplementedError) as e:
                logger.error(f"[Job {job_id}] Lỗi xử lý ảnh {index + 1} ({row.productCode}, template '{factory_key}'): {e}")
                current_result.status = "Error"
                current_result.message = str(e)
                error_count += 1
            except Exception as draw_error:
                logger.error(f"[Job {job_id}] Lỗi không xác định khi vẽ ảnh {index + 1} ({row.productCode}, template '{factory_key}'): {draw_error}", exc_info=True)
                current_result.status = "Error"
                current_result.message = "Lỗi không xác định khi vẽ ảnh."
                error_count += 1
            finally:
                # Lưu kết quả cuối cùng của row (dạng dict) và cập nhật progress
                if job_id in job_tracker: # Kiểm tra job còn tồn tại
                    job_tracker[job_id]["results"][row_id] = current_result.model_dump()
                    job_tracker[job_id]["progress"] = index + 1
                else:
                    logger.warning(f"[Job {job_id}] Job không còn trong tracker khi xử lý xong row {index+1}")
            return # Thoát hẳn khỏi function nếu job bị xóa

        await asyncio.sleep(0.01) # Tạm dừng nhỏ

        # Chỉ cập nhật trạng thái cuối nếu job còn trong tracker
        if job_id in job_tracker:
            final_status = "Completed" if error_count == 0 else "Completed with errors"
            logger.info(f"[Job {job_id}] Hoàn thành xử lý. Status: {final_status}. Lỗi: {error_count}/{len(product_rows)}.")

    except Exception as e:
        final_status = "Failed"
        logger.error(f"[Job {job_id}] Gặp lỗi nghiêm trọng trong background task: {e}", exc_info=True)
        if job_id in job_tracker:
             job_tracker[job_id]["message"] = f"Lỗi hệ thống: {e}" # Gán lỗi chung
    finally:
        # Cập nhật trạng thái cuối cùng và thời gian kết thúc nếu job còn
        if job_id in job_tracker:
            end_time = time.time()
            job_tracker[job_id]["status"] = final_status
            job_tracker[job_id]["endTime"] = end_time
            logger.info(f"[Job {job_id}] Thời gian xử lý: {end_time - start_time:.2f} giây.")

# === Hàm lấy trạng thái Job (Giữ nguyên) ===
def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin trạng thái của job từ tracker."""
    return job_tracker.get(job_id)

# --- HÀM TẠO ZIP (Đã sửa lỗi thụt dòng và raise Exception) ---
def create_job_zip_archive(job_id: str) -> Optional[str]:
    """Tạo file zip từ thư mục ảnh của job và trả về đường dẫn file zip."""
    job_dir = JOB_STORAGE_BASE_DIR / job_id
    if not job_dir.is_dir():
        logger.error(f"Thư mục job không tồn tại: {job_dir}")
        raise FileNotFoundError("Job directory not found.")

    # Tạo file zip trong thư mục tạm của hệ thống
    temp_dir = tempfile.gettempdir()
    zip_filename_base = f"tool03_images_{job_id}" # Tên file tạm thời, không phải tên download
    zip_output_path_base = os.path.join(temp_dir, zip_filename_base)

    try:
        # Sử dụng shutil.make_archive để tạo zip
        zip_path = shutil.make_archive(
            base_name=zip_output_path_base, # Đường dẫn file zip tạm (không có đuôi .zip)
            format='zip',                 # Định dạng nén
            root_dir=str(job_dir)         # Thư mục gốc để nén (nội dung bên trong sẽ được nén)
        )
        logger.info(f"Đã tạo file zip thành công: {zip_path}")
        return zip_path # Trả về đường dẫn đầy đủ của file zip tạm đã tạo
    except Exception as e:
        logger.error(f"Lỗi khi tạo file zip cho job {job_id}: {e}", exc_info=True)
        # Dọn dẹp file zip nếu tạo lỗi (tùy chọn)
        zip_file = f"{zip_output_path_base}.zip"
        if os.path.exists(zip_file):
            try:
                 os.remove(zip_file)
            except OSError as remove_e:
                 logger.error(f"Không thể xóa file zip tạm bị lỗi: {zip_file}, lỗi: {remove_e}")
        # Ném lại lỗi để controller xử lý thành 500
        raise Exception("Failed to create zip file.") from e

# === Tác vụ nền MỚI để tạo lại ảnh ===
async def regenerate_specific_images_background(job_id: str, modified_rows: List[Tool03ProductRowInput]):
    """Tác vụ nền để tạo lại các ảnh cụ thể trong một job đã tồn tại."""
    logger.info(f"[Job {job_id}] Bắt đầu TẠO LẠI {len(modified_rows)} ảnh.")

    # Lấy trạng thái job hiện tại
    current_job_data = job_tracker.get(job_id)
    if not current_job_data:
        logger.error(f"[Job {job_id}] Không tìm thấy job để tạo lại ảnh.")
        return

    job_dir = JOB_STORAGE_BASE_DIR / job_id
    if not job_dir.is_dir():
         logger.error(f"[Job {job_id}] Thư mục job không tồn tại: {job_dir}")
         current_job_data["status"] = "Failed"
         current_job_data["message"] = "Thư mục lưu trữ ảnh bị mất."
         return

    # Cập nhật trạng thái job thành Processing (nếu cần)
    current_job_data["status"] = "Processing"
    current_job_data["message"] = None # Xóa lỗi cũ nếu có
    current_job_data["endTime"] = None # Reset thời gian kết thúc

    local_error_count = 0 # Đếm lỗi chỉ trong lần chạy này
    final_status = "Processing" # Trạng thái cuối cùng của job

    try:
        for row in modified_rows:
            row_id = row.id
            logger.debug(f"[Job {job_id}] Đang TẠO LẠI ảnh cho row ID: {row_id} ({row.productCode})")

            # Cập nhật trạng thái của ảnh này thành Processing
            if row_id in current_job_data["results"]:
                current_job_data["results"][row_id]["status"] = "Processing"
                current_job_data["results"][row_id]["message"] = None
            else:
                 # Nếu row ID này chưa từng tồn tại (khó xảy ra nếu frontend gửi đúng)
                 current_job_data["results"][row_id] = Tool03ImageResult(status="Processing").model_dump()

            # Logic tạo ảnh giống như hàm generate_images_background
            template_name = row.template or "テンプレートA"
            base_key = template_name.replace("テンプレート", "")
            factory_key = base_key
            has_mobile_data = bool(row.mobileStartDate and row.mobileEndDate)
            potential_mobile_key = f"{base_key}-2"
            if has_mobile_data and potential_mobile_key in factory_registry._factories:
                factory_key = potential_mobile_key

            current_result_update = {"status": "Processing"} # Dùng dict để cập nhật

            try:
                factory = factory_registry.get_factory(factory_key)
                img: Image.Image = factory.draw(row, factory_key)
                output_filename = f"{row.productCode}.jpg"
                output_path = job_dir / output_filename
                img.save(output_path, "JPEG", quality=95) # Ghi đè file cũ
                current_result_update["status"] = "Success"
                current_result_update["filename"] = output_filename
                current_result_update["message"] = None
                img.close()

            except (FileNotFoundError, ValueError, NotImplementedError) as e:
                logger.error(f"[Job {job_id}] Lỗi TẠO LẠI ảnh ({row.productCode}, template '{factory_key}'): {e}")
                current_result_update["status"] = "Error"
                current_result_update["message"] = str(e)
                local_error_count += 1
            except Exception as draw_error:
                logger.error(f"[Job {job_id}] Lỗi không xác định khi TẠO LẠI ảnh ({row.productCode}, template '{factory_key}'): {draw_error}", exc_info=True)
                current_result_update["status"] = "Error"
                current_result_update["message"] = "Lỗi không xác định khi vẽ ảnh."
                local_error_count += 1
            finally:
                 # Cập nhật kết quả cho ảnh này trong job_tracker
                 if job_id in job_tracker and row_id in job_tracker[job_id]["results"]:
                     job_tracker[job_id]["results"][row_id].update(current_result_update)
                 elif job_id not in job_tracker:
                     logger.warning(f"[Job {job_id}] Job không còn trong tracker khi xử lý xong TẠO LẠI row {row_id}")
            return # Thoát nếu job bị xóa

            await asyncio.sleep(0.01)

        # --- Xác định trạng thái cuối cùng sau khi tạo lại ---
        # Kiểm tra xem còn ảnh nào đang Processing không (có thể do lỗi từ trước hoặc job bị cancel)
        # Hoặc kiểm tra xem có ảnh nào bị Error không (bao gồm cả lỗi mới và lỗi cũ)
        final_status = "Completed"
        has_errors = False
        if job_id in job_tracker: # Kiểm tra job còn không
             # Đếm lại progress dựa trên các ảnh không còn Processing
             completed_count = 0
             for res in job_tracker[job_id]["results"].values():
                  if res.get("status") == "Error":
                       has_errors = True
                  if res.get("status") != "Processing":
                       completed_count += 1
             job_tracker[job_id]["progress"] = completed_count # Cập nhật progress thực tế

             if has_errors:
                  final_status = "Completed with errors"
        else:
             final_status = "Failed" # Job đã bị xóa?

        logger.info(f"[Job {job_id}] Hoàn thành TẠO LẠI ảnh. Status mới: {final_status}. Lỗi trong lần chạy này: {local_error_count}/{len(modified_rows)}.")

    except Exception as e:
        final_status = "Failed" # Lỗi nghiêm trọng trong quá trình tạo lại
        logger.error(f"[Job {job_id}] Gặp lỗi nghiêm trọng khi TẠO LẠI ảnh: {e}", exc_info=True)
        if job_id in job_tracker:
            job_tracker[job_id]["message"] = f"Lỗi hệ thống khi tạo lại ảnh: {e}"
    finally:
        # Cập nhật trạng thái cuối cùng và thời gian kết thúc nếu job còn
        if job_id in job_tracker:
            end_time = time.time()
            job_tracker[job_id]["status"] = final_status
            job_tracker[job_id]["endTime"] = end_time


# === HÀM UPLOAD FTP ===
def upload_job_images_to_ftp(job_id: str, target: str):
    """
    Tác vụ nền để upload ảnh của một job lên server FTP.
    (Background task to upload a job's images to an FTP server.)
    """
    # --- Hardcode thông tin FTP (SỬA LẠI ĐƯỜNG DẪN NẾU CẦN) ---
    ftp_configs = {
        "gold": {
            "host": "ftp.rakuten.ne.jp",
            "port": 16910,
            "user": "auc-ronnefeldt",
            "password": "Ronne@04",
            "remote_dir": "/public_html/tools/03/" # Sửa thành thư mục đúng trên GOLD
        },
        "rcabinet": {
            # Thêm config cho R-Cabinet nếu cần
        }
    }

    config = ftp_configs.get(target)
    if not config:
        logger.error(f"[Job {job_id}] Không tìm thấy cấu hình FTP cho target: {target}")
        return

    job_dir = JOB_STORAGE_BASE_DIR / job_id
    if not job_dir.is_dir():
        logger.error(f"[Job {job_id}] Thư mục job không tồn tại để upload: {job_dir}")
        return

    logger.info(f"[Job {job_id}] Bắt đầu upload lên FTP target '{target}' tại host {config['host']}.")

    ftp = None
    try:
        ftp = ftplib.FTP()
        ftp.connect(config['host'], config['port'], timeout=30)
        ftp.login(config['user'], config['password'])
        ftp.set_pasv(True)

        logger.info(f"[Job {job_id}] Đang chuyển đến thư mục FTP: {config['remote_dir']}")
        try:
             ftp.cwd(config['remote_dir'])
        except ftplib.error_perm as e:
             if "550" in str(e):
                  try:
                       logger.warning(f"[Job {job_id}] Thư mục {config['remote_dir']} không tồn tại, đang thử tạo...")
                       ftp.mkd(config['remote_dir'])
                       ftp.cwd(config['remote_dir'])
                       logger.info(f"[Job {job_id}] Đã tạo và chuyển đến thư mục {config['remote_dir']}")
                  except ftplib.all_errors as mkd_e:
                       logger.error(f"[Job {job_id}] Không thể tạo hoặc chuyển đến thư mục {config['remote_dir']}: {mkd_e}", exc_info=True)
                       raise
             else:
                  logger.error(f"[Job {job_id}] Lỗi quyền khi chuyển thư mục FTP: {e}", exc_info=True)
                  raise

        image_files = [f for f in os.listdir(job_dir) if f.lower().endswith('.jpg')]
        successful_uploads = 0
        for filename in image_files:
            local_path = os.path.join(job_dir, filename)
            remote_path = filename
            try:
                with open(local_path, 'rb') as file:
                    ftp.storbinary(f'STOR {remote_path}', file)
                    logger.info(f"[Job {job_id}] Đã upload thành công file: {filename}")
                    successful_uploads += 1
            except ftplib.all_errors as upload_e:
                 logger.error(f"[Job {job_id}] Lỗi khi upload file {filename}: {upload_e}", exc_info=True)

        logger.info(f"[Job {job_id}] Hoàn tất upload. Thành công: {successful_uploads}/{len(image_files)} file(s) lên {target}.")

    except ftplib.all_errors as e:
        logger.error(f"[Job {job_id}] Lỗi FTP khi upload tới {target}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"[Job {job_id}] Lỗi không xác định khi upload FTP: {e}", exc_info=True)
    finally:
        if ftp:
            try:
                ftp.quit()
                logger.info(f"[Job {job_id}] Đã đóng kết nối FTP.")
            except ftplib.all_errors as e:
                logger.error(f"[Job {job_id}] Lỗi khi đóng kết nối FTP: {e}")

# === Hàm dọn dẹp job cũ (Giữ nguyên) ===
async def cleanup_old_jobs():
     """Xóa thông tin job và file ảnh cũ sau một khoảng thời gian."""
     current_time = time.time()
     timeout = 3600 # 1 giờ = 3600 giây
     jobs_to_delete = [
          job_id for job_id, data in job_tracker.items()
          if current_time - (data.get("endTime") or data.get("startTime", 0)) > timeout
     ]

     if jobs_to_delete:
          logger.info(f"Chuẩn bị dọn dẹp {len(jobs_to_delete)} job(s) cũ.")
          for job_id in jobs_to_delete:
               logger.info(f"Dọn dẹp job cũ: {job_id}")
               try:
                    if job_id in job_tracker: del job_tracker[job_id]
                    job_dir = JOB_STORAGE_BASE_DIR / job_id
                    if job_dir.exists():
                         shutil.rmtree(job_dir)
               except Exception as e:
                    logger.error(f"Lỗi khi dọn dẹp job {job_id}: {e}")

     # Lên lịch chạy lại sau 10 phút
     await asyncio.sleep(600)
     # Tạo task mới thay vì gọi đệ quy trực tiếp để tránh stack overflow
     asyncio.create_task(cleanup_old_jobs())

# --- Khởi chạy cleanup task khi ứng dụng khởi động (có thể đặt trong main.py) ---
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Khởi chạy tác vụ dọn dẹp job cũ...")
#     asyncio.create_task(cleanup_old_jobs())
#     ... (các startup khác)

