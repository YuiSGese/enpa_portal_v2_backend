
from fastapi import APIRouter, Depends, HTTPException
from playwright.sync_api import sync_playwright
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.domain.repositories.user_repository import UserRepository
from app.test.validate import UserCreate
from app.core.bcrypt import get_password_hash

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/", summary="")
def test():
    return {"message": "Hello World"}

@router.get("/scrape-rakuten")
def scrape_rakuten():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.rakuten.co.jp/")
        content = page.inner_text("body")
        links = page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
        browser.close()
        return {"content_snippet": content[:500], "links_count": len(links), "links_sample": links[:10]}
    

@router.get("/db")
def get_users(db: Session = Depends(get_db)):
    repo = UserRepository(db)
    users = repo.get_all()
    return {"status": "success", "data": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}

@router.post("/db", response_model=dict)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)

    if repo.get_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email đã tồn tại")

    new_user = repo.create(user.name, user.email, user.password)
    return {"id": new_user.id, "name": new_user.name, "email": new_user.email}

@router.get("/pass")
def get_users(db: Session = Depends(get_db)):
    
    passwordHash = get_password_hash("khanh")
    return {"pass": passwordHash}