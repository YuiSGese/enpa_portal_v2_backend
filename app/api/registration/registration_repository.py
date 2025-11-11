from sqlalchemy.orm import Session

class registration_repository:
    def __init__(self, db: Session):
        self.db = db