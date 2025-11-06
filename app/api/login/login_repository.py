from sqlalchemy.orm import Session, joinedload
from app.domain.entities.UserEntity import UserEntity
from app.domain.entities.CompanyEntity import CompanyEntity
from sqlalchemy import select

class login_repository:
    def get_by_username(self, username: str):
        stmt = (
            select(
                UserEntity.id,
                UserEntity.username,
                UserEntity.email,
                UserEntity.role_id,
                UserEntity.company_id,
                CompanyEntity.company_name
            )
            .join(
                CompanyEntity,
                UserEntity.company_id == CompanyEntity.id,
                isouter=True
            )
            .where(UserEntity.username == username)
        )

        result = self.db.execute(stmt).first()
        return result