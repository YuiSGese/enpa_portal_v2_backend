from sqlalchemy.orm import Session
from app.domain.entities.UserEntity import UserEntity

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(UserEntity).all()
    
    def get_by_username(self, username: str) -> UserEntity | None:
        return self.db.query(UserEntity).filter_by(username=username).first()

    def get_by_email(self, email: str) -> UserEntity | None:
        return self.db.query(UserEntity).filter(UserEntity.email == email).first()

    def create_user(self, userEntity: UserEntity):
        self.db.add(userEntity)
        self.db.commit()
        self.db.refresh(userEntity)
        return userEntity