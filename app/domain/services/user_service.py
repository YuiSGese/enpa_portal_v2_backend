from app.domain.repositories.user_repository import UserRepository

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def create_user(self, name: str, email: str, password: str):
        existing = self.repo.get_by_email(email)
        if existing:
            raise ValueError("Email đã tồn tại.")
        return self.repo.create(name, email, password)

    def list_users(self):
        return self.repo.get_all()