from datetime import date, datetime, timedelta
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from app.api.registration.registration_repository import registration_repository
from app.api.registration.registration_schemas import DefinitiveRegistrationRequest, DefinitiveRegistrationResponse, ProvisionalRegistrationCheckResponse, RegistrationRequest, RegistrationResponse
from sqlalchemy.orm import Session

from app.core.bcrypt import get_password_hash
from app.core.config import FINCODE_ENDPOINT_URL, FINCODE_PREFIX, FINCODE_SECRET_KEY, PUBLIC_FRONTEND_DOMAIN
from app.core.database import get_db
from app.core.send_mail import render_template, send_html_email
from app.domain.entities.RoleEntity import Role
from app.domain.response.custom_response import custom_error_response

router = APIRouter(prefix="/registration", tags=["registration"])

@router.post("/automatic_registration", response_model=RegistrationResponse)
def automatic_registration(registration_request: RegistrationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        with db.begin():
            repo = registration_repository(db)

            user_entity = repo.user_find_by_email(registration_request.email)
            
            if user_entity: 
                return custom_error_response(400, "ユーザーメールアドレスを使っていました。他のマールを記入してください。")

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
        subject = '登録'
        context = {
            "username": registration_request.person_name,
            "cta_link": f"{PUBLIC_FRONTEND_DOMAIN}/registration/definitive_registration?provis_regis_id={token}"
        }
        html_content = render_template(template_path, context)

        background_tasks.add_task(send_html_email, registration_request.email, subject, html_content)

        return {
            "detail": "お申し込みありがとうございます。ご入力いただいたメールアドレス宛にメールを送信いたしますので、ご確認ください。",
            "entity": entity,
        }

    except Exception as e:
        print(e)
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")

@router.get("/provisional_registration/check", response_model=ProvisionalRegistrationCheckResponse)
def provisional_registration_check(provis_regis_id: str, db: Session = Depends(get_db)):
    try:
        repo = registration_repository(db)
        prov_reg_record = repo.prov_reg_get_by_id(provis_regis_id)
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

@router.post("/definitive_registration", response_model=DefinitiveRegistrationResponse)
async def definitive_registration(form_data: DefinitiveRegistrationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):

    try:
        with db.begin():   
            repo = registration_repository(db)         
            is_valid, message = form_data_check(db, form_data)

            if is_valid == False:    
                return custom_error_response(400, message)

            company_entity_created = create_company(db, form_data)
            user_entity_created = create_user(db, form_data)
            store_entity_created = create_store(db, form_data)
            parameter_entity_created = create_parameter(db, form_data)

            # fincodeのAPIでクレジット登録メールを送信
            if company_entity_created.is_free_account == False:
                #'fincodeクレジット登録メール送信 処理'
                print('fincodeクレジット登録メール送信 処理')
                await send_fincode_credit_registration_mail(db, form_data)

            if company_entity_created.is_free_account == True:
                # タスク作成
                print('create_chatwork_task')

            # エマール送信作成
            send_intruction_mail(
                user_entity_created.username, 
                company_entity_created.company_name, 
                store_entity_created.store_name,
                user_entity_created.email,
                background_tasks,
            )

            # 仮登録情報レコード無効化
            repo.prov_reg_update_invalid_flag(form_data.prov_reg_id, True)

            return {
                "detail": "ご登録ありがとうございます。Mailにエンパポータルご利用までの流れを送信いたしますので、ご確認ください。",
            }
    except Exception as e:
        print(e)
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")
    
def form_data_check(db: Session, form_data: DefinitiveRegistrationRequest):

    is_valid = True
    message = ''
    repo = registration_repository(db)
    store_entity = repo.store_find(form_data.prov_reg_id, form_data.store_id)
    if store_entity:
        is_valid = False
        message = '既に登録されているショップIDです。再度入力を行ってください。'
        return is_valid, message
        
    user_entity = repo.user_find_by_username(form_data.username)

    if user_entity:
        is_valid = False
        message = '既に使用されているユーザー名です。再度入力を行ってください。'
        return is_valid, message
    
    return is_valid, message
    
def send_intruction_mail(username: str, company_name: str, store_name: str, email: str, background_tasks: BackgroundTasks):
    template_path = "app/assets/mail_template/instruction_template.html"
    subject = 'エンパタウンへようこそ' + username + '様'
    context = {
        "username": username,
        "company_name": company_name,
        "store_name": store_name,
    }
    attachment_files_to_send = [
    "app/assets/docs/エンパタウンPORTAL初期設定手順書.xlsx",
    ]
    html_content = render_template(template_path, context)

    background_tasks.add_task(send_html_email, email, subject, html_content, attachment_files_to_send)

    
async def send_fincode_credit_registration_mail(db: Session, form_data: DefinitiveRegistrationRequest):
    """
    fincodeのAPIを使用してクレジットカード登録用メールを送信する
    """
    repo = registration_repository(db)
    company_entity = repo.company_find_by_id(form_data.prov_reg_id)

    if not company_entity:
        raise HTTPException(400, "企業が存在しません。")

    # ユーザー情報の取得  
    user_entity = repo.user_find_by_username(form_data.username)

    if not user_entity:
        raise HTTPException(400, "ユーザーが存在しません。")
    
    user_email = user_entity.email
    company_id = company_entity.id
    # 仮登録情報該当レコード
    prov_reg_entity = repo.prov_reg_get_by_id(form_data.prov_reg_id)
    company_name = prov_reg_entity.company_name
    person_name = prov_reg_entity.person_name

    # 有効期限
    expire_date = (datetime.now() + timedelta(days=7)).strftime("%Y/%m/%d %H:%M:%S")

    # カードセッション作成用データ
    card_session_data = {
        # 成功時リダイレクトURL
        'success_url': f"{PUBLIC_FRONTEND_DOMAIN}/credit-registration-complete/?provis_regis_id={str(company_id)}",
        # 登録URL 有効期限
        'expire': expire_date,
        # 送信先メールアドレス
        'receiver_mail': user_email,
        # カード登録をするユーザーの名前
        'mail_customer_name': person_name,
        # カード登録メール 送信フラグ
        'guide_mail_send_flag': '1',
        # 完了メール 送信フラグ
        'completion_mail_send_flag': '1',
        # メールテンプレートID
        'shop_mail_template_id': None,
        # 顧客ID
        'customer_id': company_id,
        # 顧客名
        'customer_name': company_name,
        # 3Dセキュア認証を利用
        'tds_type': '0',
    }

    # APIリクエストの作成
    authorization_header = FINCODE_PREFIX + FINCODE_SECRET_KEY

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            FINCODE_ENDPOINT_URL,
            headers={
                "Authorization": authorization_header,
                "Content-Type": "application/json",
            },
            json=card_session_data
        )

    if response.status_code == 200:
        print('success fincode')


def create_company(db: Session, form_data: DefinitiveRegistrationRequest):
    repo = registration_repository(db)
    company_id = form_data.prov_reg_id
    # 仮登録情報
    prov_reg_entity = repo.prov_reg_get_by_id(form_data.prov_reg_id)

    if not prov_reg_entity:
        raise HTTPException(400, "仮登録情報が存在しません。")

    company_name = prov_reg_entity.company_name
    consulting_flag = prov_reg_entity.consulting_flag
    is_free_account = False
    if consulting_flag == True:
        is_free_account = True

    entity = repo.create_company(company_id, company_name, True, is_free_account)
    return entity

def create_user(db: Session, form_data: DefinitiveRegistrationRequest):
    repo = registration_repository(db)
    prov_reg_entity = repo.prov_reg_get_by_id(form_data.prov_reg_id)
    if not prov_reg_entity:
        raise HTTPException(400, "仮登録情報が存在しません。")
    
    company_id = form_data.prov_reg_id
    username = form_data.username
    email = prov_reg_entity.email
    password = get_password_hash("password") # code v1 random pass 15 ki tu
    role_user_entity = repo.get_role_by_role_name(Role.USER.value) # create voi ROLE_USER
    if not role_user_entity:
        raise HTTPException(400, "役割データが存在しません。")
    entity = repo.create_user(username, email, password, company_id, role_user_entity.id)
    return entity

def create_store(db: Session, form_data: DefinitiveRegistrationRequest):
    repo = registration_repository(db)
    prov_reg_entity = repo.prov_reg_get_by_id(form_data.prov_reg_id)
    if not prov_reg_entity:
        raise HTTPException(400, "仮登録情報が存在しません。")
    store_id = form_data.store_id
    store_name = form_data.store_name
    path_name = form_data.store_url
    company_id = form_data.prov_reg_id
    get_search_type = 'get'
    consulting = prov_reg_entity.consulting_flag
    start_date =  date.today()
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
