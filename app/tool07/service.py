from app.tool07.repository import Tool07Repository
from app.tool07.schemas import SettingsRead, ItemReviewData, SettingsBase, SettingsModel
from app.core.database import get_db
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont # Cần cài đặt Pillow/PIL
import os
import math
import time
from urllib.parse import urljoin
from sqlalchemy.orm import Session # Import cho Dependency Injection
from fastapi import Depends # Import cho Dependency Injection

# --- MOCK CLASSES (Thay thế cho các API thực tế) ---

class ImageGenerator:
    """Tạo hình ảnh banner đánh giá sản phẩm tùy chỉnh."""
    def __init__(self):
        # Đảm bảo đường dẫn tạm thời nằm trong tool07
        self.output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp_images')
        os.makedirs(self.output_dir, exist_ok=True)
        # Tải Font (Sử dụng font mặc định nếu không tìm thấy)
        try:
            self.font_path = "arial.ttf" # Giả định font có sẵn
            self.font_rating = ImageFont.truetype(self.font_path, 40)
            self.font_count = ImageFont.truetype(self.font_path, 20)
            self.banner_height = 100
        except IOError:
            self.font_rating = ImageFont.load_default()
            self.font_count = ImageFont.load_default()
            self.banner_height = 50 

        self.bg_color = (15, 137, 206)
        self.text_color = (255, 255, 255)

    def generate_banner(self, template_id, avg_rating, review_count, min_review_display) -> Tuple[str, str]:
        # Logic tạo ảnh (như file image_generator.py cũ)
        rating_text = f"{avg_rating:.2f}"
        
        if review_count >= min_review_display:
            count_text = f"({review_count} reviews)"
            filename_suffix = f"_{review_count}"
        else:
            count_text = "(Highly Rated)"
            filename_suffix = "_no_count"
            
        filename = f"{template_id}_{rating_text.replace('.', '_')}{filename_suffix}.png"
        file_path = os.path.join(self.output_dir, filename)
        banner_width = 800

        img = Image.new('RGB', (banner_width, self.banner_height), color=self.bg_color)
        d = ImageDraw.Draw(img)

        # Mô phỏng vẽ chữ
        x_start = 50
        y_center = self.banner_height / 2
        d.text((x_start, y_center), rating_text, fill=self.text_color, font=self.font_rating)
        
        # Lưu ảnh
        img.save(file_path)
        print(f"[IMAGE: TOOL07] Created banner: {filename}")
        return filename, file_path

class RakutenAPIGateway:
    """Mô phỏng API Rakuten (Image API và Item API)."""
    
    def __init__(self):
        self.r_cabinet_base_url = "https://image.rakuten.co.jp/{shop_url}/cabinet/{path}/"
        self.shop_url_placeholder = "myshop" 

    def upload_image(self, file_path, file_name, folder_path="review_banners") -> Optional[str]:
        """Tải hình ảnh lên R-Cabinet của Rakuten (Mô phỏng)."""
        if not os.path.exists(file_path):
            return None
        
        # --- MÔ PHỎNG GỌI API UPLOAD ---
        time.sleep(0.5) 

        remote_url = urljoin(
            self.r_cabinet_base_url.format(shop_url=self.shop_url_placeholder),
            f"{folder_path}/{file_name}"
        )
        
        print(f"[API: TOOL07] Uploaded to: {remote_url}")
        os.remove(file_path) # Xóa file cục bộ
        
        return remote_url

    def get_item_reviews(self, manage_number: str) -> Tuple[float, int]:
        """Mô phỏng lấy điểm đánh giá và số lượng."""
        import random
        # Giả lập kết quả (avg rating >= 4.00 là đủ điều kiện)
        avg_rating = round(random.uniform(4.00, 5.00), 2)
        review_count = random.randint(3, 50) # random để test điều kiện min_placement
        return avg_rating, review_count
        
    def update_item_content(self, manage_number: str, image_url: str, settings: SettingsRead, current_desc_pc: str, current_desc_sp: str):
        """Cập nhật mô tả sản phẩm (PC/SP) trên Rakuten."""
        
        pc_img_tag = f'<img src="{image_url}" width="{settings.pc_width}{settings.pc_unit}" alt="Review Banner">'
        sp_img_tag = f'<img src="{image_url}" width="{settings.sp_width}{settings.sp_unit}" alt="Review Banner">'
        
        new_pc_description = self._insert_content(current_desc_pc, pc_img_tag, settings.pc_position)
        new_sp_description = self._insert_content(current_desc_sp, sp_img_tag, settings.sp_position)
        
        # --- MÔ PHỎNG GỌI API UPDATE ITEM ---
        time.sleep(0.5) 
        
        print(f"[API: TOOL07] Item {manage_number} updated.")
        
        # Trả về nội dung mới để mô phỏng
        return new_pc_description, new_sp_description

    def _insert_content(self, original_content: str, img_tag: str, positions: List[str]) -> str:
        """Chèn thẻ IMG vào nội dung dựa trên vị trí đã chọn."""
        START_TAG = '<!-- R-REVIEW-BANNER-START -->'
        END_TAG = '<!-- R-REVIEW-BANNER-END -->'
        
        # 1. Loại bỏ banner cũ
        if START_TAG in original_content:
            start_index = original_content.find(START_TAG)
            end_index = original_content.find(END_TAG) + len(END_TAG)
            content_without_old_banner = original_content[:start_index] + original_content[end_index:]
        else:
            content_without_old_banner = original_content
            
        banner_block = f'{START_TAG}{img_tag}{END_TAG}'
        
        # 2. Chèn vào vị trí mới
        if '1' in positions: # Vị trí 1: Trước nội dung
            content_without_old_banner = banner_block + content_without_old_banner
            
        if '2' in positions: # Vị trí 2: Sau nội dung
            content_without_old_banner = content_without_old_banner + banner_block

        return content_without_old_banner

# --- LỚP SERVICE CHÍNH ---

class Tool07Service:
    """Logic nghiệp vụ chính cho công cụ Review Image."""

    def __init__(self, repo: Tool07Repository):
        self.repo = repo
        self.api_gateway = RakutenAPIGateway()
        self.image_generator = ImageGenerator()

    def get_settings(self) -> SettingsRead:
        """Lấy cài đặt từ Repository."""
        # Repo bây giờ trả về SettingsModel hoặc None
        settings_model: Optional[SettingsModel] = self.repo.get_settings()
        
        if settings_model is None:
             # Nếu DB trống hoặc lỗi khởi tạo, trả về mặc định hardcode
             return SettingsRead(
                id=1, template_id='template_A', min_review_placement=5, min_review_display=15,
                pc_width=600, pc_unit='px', sp_width=90, sp_unit='%',
                pc_position=['1'], sp_position=['1']
            )

        # Trả về Pydantic Schema từ SQLAlchemy Model
        return SettingsRead.from_orm(settings_model)

    def save_settings(self, data: SettingsBase) -> None:
        """Lưu cài đặt vào Repository."""
        self.repo.save_settings(data)
        
    def get_candidate_items(self) -> List[Dict[str, str]]:
        """Mô phỏng lấy danh sách sản phẩm cần kiểm tra (Trong thực tế lấy từ Rakuten API)."""
        # Giả lập 3 sản phẩm
        return [
            {'manageNumber': 'A001', 'path_name': 'shop', 'current_desc_pc': 'PC desc A001', 'current_desc_sp': 'SP desc A001'},
            {'manageNumber': 'A002', 'path_name': 'shop', 'current_desc_pc': 'PC desc A002', 'current_desc_sp': 'SP desc A002'},
            {'manageNumber': 'A003', 'path_name': 'shop', 'current_desc_pc': 'PC desc A003', 'current_desc_sp': 'SP desc A003'},
        ]

    def run_full_process(self):
        """Thực thi toàn bộ quy trình: Lấy cấu hình -> Xử lý từng sản phẩm -> Cập nhật."""
        
        print("\n--- Bắt đầu XỬ LÝ TỰ ĐỘNG Tool07 ---")
        
        settings = self.get_settings()
        candidate_items = self.get_candidate_items()

        for item in candidate_items:
            manage_number = item['manageNumber']
            
            # 1. Lấy thông tin đánh giá
            avg_rating, review_count = self.api_gateway.get_item_reviews(manage_number)
            print(f"  [ITEM: {manage_number}] Rating: {avg_rating} ({review_count} reviews)")

            # 2. Kiểm tra điều kiện chèn (>= 4.00, count >= min_placement)
            if review_count >= settings.min_review_placement and avg_rating >= 4.00:
                print(f"  -> Eligible. Generating banner...")
                
                # 3. TẠO HÌNH ẢNH
                filename, file_path = self.image_generator.generate_banner(
                    settings.template_id, avg_rating, review_count, settings.min_review_display
                )
                
                # 4. TẢI HÌNH ẢNH LÊN RAKUTEN (API)
                remote_url = self.api_gateway.upload_image(file_path, filename)
                
                if remote_url:
                    # 5. CẬP NHẬT NỘI DUNG SẢN PHẨM TRÊN RAKUTEN (API)
                    new_pc_desc, new_sp_desc = self.api_gateway.update_item_content(
                        manage_number, remote_url, settings, 
                        item['current_desc_pc'], item['current_desc_sp']
                    )

                    # 6. CẬP NHẬT TRẠNG THÁI VÀO DB NỘI BỘ
                    item_data = ItemReviewData(
                        path_name=item['path_name'], manageNumber=manage_number, 
                        review_count=review_count, review_averageRating=avg_rating, 
                        template_id=settings.template_id, img_remote_url=remote_url, 
                        img_width=settings.pc_width, img_unit=settings.pc_unit, 
                        delete_flg='0' # 0: Cần cập nhật
                    )
                    self.repo.update_item_status(item_data)
                    print(f"  -> SUCCESS: Item {manage_number} status updated in DB.")
            
            else:
                print("  -> Not eligible (Bỏ qua hoặc Xóa banner cũ).")
        
        print("--- Hoàn tất XỬ LÝ TỰ ĐỘNG Tool07 ---")

# Dependency Injection cho Service
# Đã cập nhật để sử dụng SQLAlchemy Session
def get_tool07_service(db: Session = Depends(get_db)) -> Tool07Service:
    """Hàm cung cấp Tool07Service cho Controller/Scheduled Job."""
    repo = Tool07Repository(db)
    return Tool07Service(repo)
