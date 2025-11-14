from datetime import datetime, timedelta
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from playwright.sync_api import sync_playwright
from app.core.database import get_db
from app.domain.repositories.user_repository import UserRepository
from app.core.security import require_roles
from app.domain.entities.RoleEntity import Role
from app.test.validate import TestFincodeRequest

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
    

# @router.get("/db")
# def get_users(db: Session = Depends(get_db)):
#     repo = UserRepository(db)
#     users = repo.get_all()
#     return {"status": "success", "data": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}

# @router.post("/db", response_model=dict)
# def create_user(user: UserCreate, db: Session = Depends(get_db)):
#     repo = UserRepository(db)

#     if repo.get_by_email(user.email):
#         raise HTTPException(status_code=400, detail="Email đã tồn tại")

#     new_user = repo.create(user.name, user.email, user.password)
#     return {"id": new_user.id, "name": new_user.name, "email": new_user.email}

@router.get("/admin/dashboard")
def admin_dashboard(request: Request, user=Depends(require_roles(Role.ADMIN))):
    user = request.state.user
    return {"msg": f"Hello admin name: {user['user_name']} with role {user['role_name']}"}

@router.get("/user/dashboard")
def user_dashboard(request: Request, user=Depends(require_roles(Role.USER))):
    user = request.state.user
    return {"msg": f"Hello user name: {user['user_name']} with role {user['role_name']}"}


@router.get("/all")
def user_dashboard(request: Request):
    user = request.state.user
    return {"msg": f"Hello user name: {user['user_name']} with role {user['role_name']}"}


"""
✅ Thẻ VISA (Test Card)
4012 8888 8888 1881     12/30       123

✅ Thẻ MasterCard (Test Card)
5555 5555 5555 4444     12/30       123

✅ Thẻ gây lỗi (để test error)
4000 0000 0000 0002	    12/30	    123	    Bị từ chối (Do Not Honor)
4000 0000 0000 9995	    12/30	    123	    Thẻ hết hạn
4000 0000 0000 0010	    12/30	    123	    Số dư không đủ

"""
@router.post("/fincode/test-send-mail")
async def test_send_card_mail(form_data: TestFincodeRequest):
    """
    Gửi mail test đăng ký thẻ qua sandbox Fincode
    """
    FINCODE_PREFIX = "Bearer "
    FINCODE_SECRET_KEY = "m_test_MDIwNTZhOTItMGE0Mi00OTI1LWJhYTItZDA1OGYwOTAzOTJmNzUxZmVlYzUtYzk3Ni00NDlmLTk0Y2ItYTUzOTVhZjc2MzQzc18yNTExMTQzODQ3OA"
    # Test MODE
    FINCODE_API_KEY = FINCODE_PREFIX + FINCODE_SECRET_KEY
    FINCODE_BASE_URL = "https://api.test.fincode.jp"

    TEST_SUCCESS_URL = "https://example.com/test/credit-complete"

    # Expire 7 ngày
    expire_date = (datetime.now() + timedelta(days=7)).strftime("%Y/%m/%d %H:%M:%S")

    data = {
        "success_url": TEST_SUCCESS_URL,
        "expire": expire_date,
        "receiver_mail": form_data.email,
        "mail_customer_name": form_data.customer_name,
        "guide_mail_send_flag": "1",
        "completion_mail_send_flag": "1",
        "shop_mail_template_id": None,
        "customer_id": "test_cus_001",
        "customer_name": form_data.customer_name,
        "tds_type": "0",
    }

    url = FINCODE_BASE_URL + "/v1/card_sessions"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": FINCODE_API_KEY,
                "Content-Type": "application/json",
            },
            json=data
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return {
        "message": "Fincode test mail sent!",
        "response": response.json()
    }