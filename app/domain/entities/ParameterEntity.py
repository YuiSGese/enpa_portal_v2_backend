from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, CHAR, Boolean, func
from app.core.database import Base
import uuid

class ParameterEntity(Base):
    __tablename__ = "m_parameters"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(8), nullable=True)
    path_name = Column(String(100), nullable=True)
    bundle_execution = Column(String(10), nullable=True)
    bundle_Default_manageNumber = Column("bundle_Default_manageNumber", String(30), nullable=True)
    similar_title = Column(String(50), nullable=True)
    similar_category = Column(String(5), nullable=True)
    similar_genre = Column(String(5), nullable=True)
    similar_created = Column(String(5), nullable=True)
    rpp_execution = Column(String(5), nullable=True)
    limit_CPC = Column("limit_CPC", Integer, nullable=True)
    ranking_execution = Column(Boolean, nullable=True)
    ranking_template = Column(String(100), nullable=True)
    ranking_item_image = Column(Boolean, nullable=True)
    rakuten_report_execution = Column(Boolean, nullable=True)
    rakuten_report_num_items = Column(Integer, nullable=True)
    rakuten_outlier_execution = Column(Boolean, nullable=True)
    review_img_execution = Column(Boolean, nullable=True)
    review_img_in_ItemImg = Column("review_img_in_ItemImg", Boolean, nullable=True)
    review_count_RefValue_mini = Column("review_count_RefValue_mini", Integer, nullable=True)
    review_count_RefValue = Column("review_count_RefValue", Integer, nullable=True)
    review_template = Column(String(5), nullable=True)
    Default_profit_margin = Column("Default_profit_margin", String(5), nullable=True)
    Default_taxRate = Column("Default_taxRate", String(10), nullable=True)
    rakuten_daily_enabled = Column(Boolean, nullable=True)
    ranking_image_pc_width = Column(String(100), nullable=True)
    rpp_budget_alart_execution = Column(Boolean, nullable=True)
    rpp_budget_alart_threshold = Column(Integer, nullable=True)
    rpp_schedule_execution = Column(Boolean, nullable=True)
    search_ranking_execution = Column(Boolean, nullable=True)
    tax_Rounding = Column("tax_Rounding", String(5), nullable=True)

    delete_flg = Column(Boolean, nullable=True, default=False)
    create_datetime = Column(DateTime, default=datetime.now)
    update_datetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)