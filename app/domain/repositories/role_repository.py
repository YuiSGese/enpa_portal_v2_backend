from sqlalchemy.orm import Session
from app.domain.entities.RoleEntity import RoleEntity

class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, role_id: int) -> RoleEntity | None:
        return self.db.query(RoleEntity).filter(RoleEntity.id == role_id).first()

    def get_by_name(self, role_name: str) -> RoleEntity | None:
        return self.db.query(RoleEntity).filter(RoleEntity.role_name == role_name).first()

    def list_all(self) -> list[RoleEntity]:
        return self.db.query(RoleEntity).all()
