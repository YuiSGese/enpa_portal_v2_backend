from sqlalchemy.orm import Session
from app.domain.entities.UserEntity import UserEntity
from app.domain.entities.CompanyEntity import CompanyEntity
from app.domain.entities.RoleEntity import RoleEntity
from sqlalchemy import select

class staff_repository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> UserEntity | None:
        return self.db.query(UserEntity).filter_by(username=username).first()

    def get_role_by_role_name(self, role_name: str) -> RoleEntity | None:
        return self.db.query(RoleEntity).filter_by(role_name=role_name).first()

    def get_by_email(self, email: str) -> UserEntity | None:
        return self.db.query(UserEntity).filter(UserEntity.email == email).first()
    
    def create_user(self, userEntity: UserEntity):
        self.db.add(userEntity)
        self.db.commit()
        self.db.refresh(userEntity)
        return userEntity

    def get_list_user_by_company_id(self, company_id: int):
        stmt = (
            select(
                UserEntity.id,
                UserEntity.username,
                UserEntity.email,
                UserEntity.role_id,
                UserEntity.company_id,
                UserEntity.password,
                CompanyEntity.company_name,
                RoleEntity.role_name,
            )
            .join(CompanyEntity, UserEntity.company_id == CompanyEntity.id, isouter=True)
            .join(RoleEntity, UserEntity.role_id == RoleEntity.id, isouter=True)
            .where(UserEntity.company_id == company_id)
        )

        result = self.db.execute(stmt).all()
        return result
    
    def delete_user_by_username(self, username: str):
        user = self.db.query(UserEntity).filter(UserEntity.username == username).first()
        
        if user is None:
            return None

        # Xóa user
        self.db.delete(user)
        self.db.commit()

        return user
    