# tool_35_coupon_image_creation/factory/base_factory.py
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from ..schemas import CouponInput


class Factory:
    """
    Lớp cơ sở cho tất cả template factory.
    Chứa logic vẽ text, tính font-size, bố trí, v.v.
    """

    def __init__(self):
        self.font_dir = os.path.join(os.getcwd(), "fonts")
        # Các font mặc định (bạn có thể thay đường dẫn thật)
        self.font_path_NotoSans_EB = os.path.join(self.font_dir, "NotoSansJP-ExtraBold.ttf")
        self.font_path_NotoSans_M = os.path.join(self.font_dir, "NotoSansJP-Medium.ttf")
        self.font_path_Serif = os.path.join(self.font_dir, "NotoSerifJP-ExtraBold.ttf")
        self.font_path_Lato = os.path.join(self.font_dir, "Lato-Black.ttf")

    # -------------------- HÀM CƠ BẢN --------------------

    def place_text(self, draw: ImageDraw, text: str, font_path: str, x: int, y: int, size: int, color=(0, 0, 0), align="center"):
        """Vẽ text vào vị trí xác định."""
        font = ImageFont.truetype(font_path, size)
        text_w, text_h = font.getbbox(text)[2:4]

        if align == "center":
            draw.text((x - text_w / 2, y - text_h / 2), text, fill=color, font=font)
        elif align == "left":
            draw.text((x, y - text_h / 2), text, fill=color, font=font)
        elif align == "right":
            draw.text((x - text_w, y - text_h / 2), text, fill=color, font=font)
        else:
            draw.text((x, y), text, fill=color, font=font)

    def calculate_font_size(self, text: str, font_path: str, max_w: int, max_h: int) -> int:
        """Tính font-size tối đa vừa khung."""
        font_size = 1
        font = ImageFont.truetype(font_path, font_size)
        while True:
            w, h = font.getbbox(text)[2:4]
            if w > max_w or h > max_h:
                break
            font_size += 1
            font = ImageFont.truetype(font_path, font_size)
        return font_size - 1

    # -------------------- HÀM CHÍNH --------------------

    def draw_from_json(self, data: CouponInput, save_path: str):
        """
        Tạo ảnh từ dữ liệu JSON (CouponInput).
        Các template cụ thể sẽ override hàm này.
        """
        raise NotImplementedError("draw_from_json() phải được override trong subclass.")
