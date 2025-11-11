import sys
import os

# Thêm root project vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base

# ⚠️ Quan trọng: import các entity để SQLAlchemy "nhận biết"
from app.domain.entities.UserEntity import UserEntity
from app.domain.entities.RoleEntity import RoleEntity
from app.domain.entities.CompanyEntity import CompanyEntity
from app.domain.entities.SampleEntity import SampleEntity
from app.domain.entities.JobEntity import JobEntity

# Tạo bảng
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully.")