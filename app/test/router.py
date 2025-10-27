
from fastapi import APIRouter, Depends
from playwright.sync_api import sync_playwright
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.domain.repositories.user_repository import UserRepository

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
    

# Dependency để inject DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/db")
def get_users(db: Session = Depends(get_db)):
    repo = UserRepository(db)
    users = repo.get_all()
    return {"status": "success", "data": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}