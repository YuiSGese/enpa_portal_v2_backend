from datetime import datetime
import re
from fastapi import APIRouter, Depends, HTTPException
from app.api.registration.registration_repository import registration_repository
from app.api.registration.registration_schemas import DefinitiveRegistrationRequest, DefinitiveRegistrationResponse, ProvisionalRegistrationCheckResponse, RegistrationRequest, RegistrationResponse
from sqlalchemy.orm import Session

from app.core.bcrypt import get_password_hash
from app.core.config import PUBLIC_FRONTEND_DOMAIN
from app.core.database import get_db
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
            "cta_link": f"{PUBLIC_FRONTEND_DOMAIN}/registration/verify?token={token}" #doi url FE
        }
        html_content = render_template(template_path, context)

        send_html_email(registration_request.email, "test subject", html_content)

        return {
            "detail": "お申し込みありがとうございます。ご入力いただいたメールアドレス宛にメールを送信いたしますので、ご確認ください。",
            "entity": entity,
        }

    except Exception as e:
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")

@router.get("/provisional_registration/check", response_model=ProvisionalRegistrationCheckResponse)
def provisional_registration_check(token: str, db: Session = Depends(get_db)):
    try:
        repo = registration_repository(db)
        prov_reg_record = repo.prov_reg_get_by_id(token)
        if not prov_reg_record:
            return custom_error_response(400, "仮登録情報が見つかりません。")

        if prov_reg_record.invalid_flag == True:
            return custom_error_response(400, "仮登録情報が無効になりました。")
        
        if prov_reg_record.expiration_datetime < datetime.now():
            return custom_error_response(400, "仮登録の期限が切れていました。")
        
        return {
            "detail": "仮登録有効しています。",
            "valid": True
        }

    except Exception as e:
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")
    
@router.get("/definitive_registration", response_model=DefinitiveRegistrationResponse)
def definitive_registration(form_data: DefinitiveRegistrationRequest, db: Session = Depends(get_db)):

    try:
        with db.begin():
            repo = registration_repository(db)
            store_entity = repo.store_find(form_data.prov_reg_id, form_data.store_id)
            
            if store_entity: 
                return custom_error_response(400, '既に登録されているショップIDです。再度入力を行ってください。') 

            user_entity = repo.user_find_by_username(form_data.username)

            if user_entity: 
                return custom_error_response(400, '既に使用されているユーザー名です。再度入力を行ってください。') 

            user_entity = repo.user_find_by_email(form_data.email)

            if user_entity: 
                return custom_error_response(400, '既に登録済みのユーザーメールアドレスです。再度入力を行ってください。') 

            company_entity_created = create_company(db, form_data)
            usery_entity_created = create_user(db, form_data)
            store_entity_created = create_store(db, form_data)
            parameter_entity_created = create_parameter(db, form_data)

            if company_entity_created.is_free_account == False:
                #'fincodeクレジット登録メール送信 処理'
                print('fincodeクレジット登録メール送信 処理')

            
            # send_html_email(registration_request.email, "test subject", html_content)

            return {
                "detail": "ご登録ありがとうございます。Mailにエンパポータルご利用までの流れを送信いたしますので、ご確認ください。",
            }
    except Exception as e:
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")
    

def create_company(db: Session, form_data: DefinitiveRegistrationRequest):
    repo = registration_repository(db)
    company_id = form_data.prov_reg_id
    # 仮登録情報
    prov_reg_entity = repo.prov_reg_get_by_id(form_data.prov_reg_id)

    company_name = prov_reg_entity.company_name
    consulting_flag = prov_reg_entity.consulting_flag
    is_free_account = False
    if consulting_flag == True:
        is_free_account = True        

    entity = repo.create_company(company_id, company_name, True, is_free_account)
    return entity

def create_user(db: Session, form_data: DefinitiveRegistrationRequest):
    repo = registration_repository(db)
    company_id = form_data.prov_reg_id
    username = form_data.username
    email = form_data.email
    password = get_password_hash("password") # code v1 random pass 15 ki tu
    role_user_entity = repo.get_role_by_role_name(Role.USER.value) # create voi ROLE_USER
    entity = repo.create_user(username, email, password, company_id, role_user_entity.id)
    return entity

def create_store(db: Session, form_data: DefinitiveRegistrationRequest):
    repo = registration_repository(db)
    prov_reg_entity = repo.prov_reg_get_by_id(form_data.prov_reg_id)
    store_id = form_data.store_id
    store_name = form_data.store_name
    path_name = form_data.store_url
    company_id = form_data.prov_reg_id
    get_search_type = 'get'
    consulting = prov_reg_entity.consulting_flag
    start_date =  datetime.date.today()
    telephone_number = prov_reg_entity.telephone_number
    entity = repo.create_store(
        store_id,
        store_name,
        path_name,
        company_id,
        get_search_type,
        consulting,
        start_date,
        telephone_number
    )
    return entity

def create_parameter(db: Session, form_data: DefinitiveRegistrationRequest):
    repo = registration_repository(db)   

    store_id = form_data.store_id
    path_name = f"{form_data.store_id}_{form_data.store_url}"
    bundle_execution = ""
    bundle_Default_manageNumber = ""
    similar_title = ""
    similar_category = ""
    similar_genre = ""
    similar_created = ""
    rpp_execution = ""
    ranking_template = "A"
    ranking_image_pc_width = '100%'
    rakuten_report_execution = True
    rakuten_outlier_execution = True
    review_count_RefValue_mini = 20
    review_template = 'E'
    Default_taxRate = form_data.default_tax_rate
    tax_Rounding = form_data.tax_rounding
    Default_profit_margin = '0.0'
    entity = repo.create_parameter(
        store_id,
        path_name,
        bundle_execution,
        bundle_Default_manageNumber,
        similar_title,
        similar_category,
        similar_genre,
        similar_created,
        rpp_execution,
        ranking_template,
        ranking_image_pc_width,
        rakuten_report_execution,
        rakuten_outlier_execution,
        review_count_RefValue_mini,
        review_template,
        Default_taxRate,
        tax_Rounding,
        Default_profit_margin
    )
    return entity