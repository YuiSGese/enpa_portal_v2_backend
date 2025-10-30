from app.tool07.shemas import SettingsBase, SettingsModel, ItemReviewModel, ItemReviewData
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import update
from datetime import datetime

class Tool07Repository:
    """Xử lý CRUD cho bảng settings và review_data (Sử dụng SQLAlchemy ORM)."""

    def __init__(self, db: Session): 
        # Dependency Injection: Nhận SQLAlchemy Session
        self.db = db

    def get_settings(self) -> Optional[SettingsModel]:
        """Tải cài đặt hiện tại (và khởi tạo nếu chưa có)."""
        settings = self.db.query(SettingsModel).filter(SettingsModel.id == 1).first()
        
        if not settings:
            # Khởi tạo giá trị mặc định nếu chưa tồn tại
            default_settings = SettingsModel(
                id=1,
                template_id='template_A',
                min_review_placement=5,
                min_review_display=15,
                pc_width=600,
                pc_unit='px',
                sp_width=90,
                sp_unit='%',
                pc_position=['1'],
                sp_position=['1'],
                last_updated=datetime.now()
            )
            try:
                self.db.add(default_settings)
                self.db.commit()
                self.db.refresh(default_settings)
                print("Đã khởi tạo cài đặt mặc định cho Tool07 (SQLAlchemy).")
                return default_settings
            except Exception as e:
                # Nếu xảy ra lỗi (ví dụ: duplicate key), rollback và log lỗi
                self.db.rollback()
                print(f"Lỗi khi khởi tạo cài đặt Tool07: {e}")
                return None
                
        return settings

    def save_settings(self, data: SettingsBase) -> None:
        """Lưu cấu hình mới vào DB (Cập nhật bản ghi có id=1)."""
        
        update_data = data.dict()
        update_data['last_updated'] = datetime.now()
        
        # SQLAlchemy ORM sẽ tự động chuyển đổi List/Dict Python thành JSON cho MariaDB.
        
        # Thực hiện UPDATE
        stmt = update(SettingsModel).where(SettingsModel.id == 1).values(update_data)
        self.db.execute(stmt)
        self.db.commit()

    def update_item_status(self, item_data: ItemReviewData) -> None:
        """Cập nhật trạng thái xử lý của sản phẩm (UPSERT bằng ORM)."""
        
        # Tìm bản ghi hiện có
        existing_item = self.db.query(ItemReviewModel).filter(
            ItemReviewModel.path_name == item_data.path_name,
            ItemReviewModel.manageNumber == item_data.manageNumber
        ).first()

        item_dict = item_data.dict(exclude_unset=True)
        item_dict['Update_datetime'] = datetime.now()

        if existing_item:
            # Nếu tồn tại, cập nhật các trường
            for key, value in item_dict.items():
                if key not in ['path_name', 'manageNumber']: # Không cập nhật primary key
                    setattr(existing_item, key, value)
        else:
            # Nếu không tồn tại, tạo bản ghi mới
            new_item = ItemReviewModel(**item_data.dict(), Update_datetime=datetime.now())
            self.db.add(new_item)

        self.db.commit()
