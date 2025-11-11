from sqlalchemy.orm import Session, joinedload
from app.domain.entities.UserEntity import UserEntity
from app.domain.entities.CompanyEntity import CompanyEntity
from app.domain.entities.RoleEntity import RoleEntity
from sqlalchemy import select

class login_repository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str):
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
            .where(UserEntity.username == username)
        )

        result = self.db.execute(stmt).first()
        return result