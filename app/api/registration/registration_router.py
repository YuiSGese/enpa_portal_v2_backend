from fastapi import APIRouter, Depends, HTTPException
from app.api.registration.registration_repository import registration_repository
from app.api.registration.registration_schemas import RegistrationRequest, RegistrationResponse, VerifyRegistrationResponse
from sqlalchemy.orm import Session

from app.core.config import PUBLIC_BACKEND_DOMAIN
from app.core.database import get_db
from app.core.security import require_roles
from app.core.send_mail import render_template, send_html_email
from app.domain.entities.RoleEntity import Role
from app.domain.response.custom_response import custom_error_response

router = APIRouter(prefix="/registration", tags=["registration"])

@router.post("/automatic_registration", response_model=RegistrationResponse)
def automatic_registration(registration_request: RegistrationRequest, db: Session = Depends(get_db)):
    try:
        with db.begin():
            repo = registration_repository(db)
            entity = repo.create_provisional_registration(
                registration_request.company_name,
                registration_request.person_name,
                registration_request.email,
                registration_request.telephone_number,
                registration_request.note,
                registration_request.consulting_flag,
                0,
            )

        token = entity.id
        template_path = "app/assets/mail_template/registration_template.html"
        context = {
            "username": registration_request.person_name,
            "cta_link": f"{PUBLIC_BACKEND_DOMAIN}/registration/verify?token={token}"
        }
        html_content = render_template(template_path, context)

        send_html_email(registration_request.email, "test subject", html_content)

        return {
            "detail": "お申し込みありがとうございます。ご入力いただいたメールアドレス宛にメールを送信いたしますので、ご確認ください。",
            "entity": entity,
        }

    except Exception as e:
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")

# @router.post("/verify", response_model=VerifyRegistrationResponse)
# def verify_registration(token: str, db: Session = Depends(get_db)):
#     try:
        

#     except Exception as e:
#         return custom_error_response(400, "問題が発生しました!! もう一度お試しください")