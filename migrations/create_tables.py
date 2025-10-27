import sys
import os

# Thêm root project vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base
from app.domain.entities.user_entity import User

Base.metadata.create_all(bind=engine)
print("Tables created successfully.")