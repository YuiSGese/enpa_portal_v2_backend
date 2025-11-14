import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.domain.entities.CompanyEntity import CompanyEntity
from app.domain.entities.ParameterEntity import ParameterEntity
from app.domain.entities.ProvisionalRegistrationEntity import ProvisionalRegistrationEntity
from app.domain.entities.RoleEntity import RoleEntity
from app.domain.entities.StoreEntity import StoreEntity
from app.domain.entities.UserEntity import UserEntity

class registration_repository:
    def __init__(self, db: Session):
        self.db = db

    def create_provisional_registration(
        self,
        company_name: str,
        person_name: str,
        email: str,
        telephone_number: str,
        note: str | None,
        consulting_flag: str,
        invalid_flag: str = "0",
    ) -> ProvisionalRegistrationEntity:

        expiration_datetime = datetime.now() + timedelta(days=7)

        new_record = ProvisionalRegistrationEntity(
            id=str(uuid.uuid4()),
            company_name=company_name,
            person_name=person_name,
            email=email,
            telephone_number=telephone_number,
            note=note,
            consulting_flag=consulting_flag,
            invalid_flag=invalid_flag,
            expiration_datetime=expiration_datetime,
        )

        self.db.add(new_record)
        self.db.flush()
        self.db.refresh(new_record)

        return new_record
    
    def prov_reg_get_by_id(self, id: str) -> ProvisionalRegistrationEntity | None:
        return self.db.query(ProvisionalRegistrationEntity)\
                      .filter(ProvisionalRegistrationEntity.id == id)\
                      .first()
    
    def prov_reg_update_invalid_flag(self, provisional_id: str, value: bool):
        record = self.db.query(ProvisionalRegistrationEntity).filter(
            ProvisionalRegistrationEntity.id == provisional_id
        ).first()

        if not record:
            return False

        record.invalid_flag = value
        record.update_datetime = datetime.now()

        self.db.flush()
        self.db.refresh(record)

        return True
    
    def store_find(self, company_id: int, store_id: str) -> StoreEntity | None:
        return (
            self.db.query(StoreEntity)
            .filter(
                StoreEntity.company_id == company_id,
                StoreEntity.store_id == store_id,
                StoreEntity.delete_flg == False
            )
            .first()
        )
    
    def user_find_by_username(self, username: str):
        return (
            self.db.query(UserEntity)
            .filter(
                UserEntity.username == username,
                UserEntity.delete_flg == False
            )
            .first()
        )
    
    def user_find_by_email(self, email: str):
        return (
            self.db.query(UserEntity)
            .filter(
                UserEntity.email == email,
                UserEntity.delete_flg == False
            )
            .first()
        )
    
    def company_find_by_id(self, company_id: str):
        return (
            self.db.query(CompanyEntity)
            .filter(
                CompanyEntity.id == company_id,
                CompanyEntity.delete_flg == False
            )
            .first()
        )   
    
    def create_company(
        self,
        company_id: str,
        company_name: str,
        is_valid: bool = False,
        is_free_account: bool = False
    ) -> CompanyEntity:
        new_company = CompanyEntity(
            id=company_id,
            company_name=company_name,
            is_valid=is_valid,
            is_free_account=is_free_account
        )
        self.db.add(new_company)
        self.db.flush()
        self.db.refresh(new_company)
        return new_company
    
    def create_user(self, username: str, email: str, password: str, company_id: str = None, role_id: str = None) -> UserEntity:
        new_user = UserEntity(
            username=username,
            email=email,
            password=password,
            company_id=company_id,
            role_id=role_id,
            is_mail_verified=True
        )

        self.db.add(new_user)
        self.db.flush()
        self.db.refresh(new_user)    
        return new_user
    
    def get_role_by_role_name(self, role_name: str) -> RoleEntity | None:
        return self.db.query(RoleEntity).filter_by(role_name=role_name).first()
    
    def create_store(
        self,
        store_id: str,
        store_name: str,
        path_name: str,
        company_id: str,
        get_search_type: str = None,
        consulting: bool = None,
        start_date=None,
        telephone_number: str = None
    ) -> StoreEntity:
        new_store = StoreEntity(
            id=str(uuid.uuid4()),
            store_id=store_id,
            store_name=store_name,
            path_name=path_name,
            company_id=company_id,
            get_search_type=get_search_type,
            consulting=consulting,
            start_date=start_date,
            telephone_number=telephone_number
        )
        self.db.add(new_store)
        self.db.flush()
        self.db.refresh(new_store)
        return new_store
    
    def create_parameter(
        self,
        store_id: str,
        path_name: str,
        bundle_execution: str,
        bundle_Default_manageNumber: str,
        similar_title: str,
        similar_category: str,
        similar_genre: str,
        similar_created: str,
        rpp_execution: str,
        ranking_template: str,
        ranking_image_pc_width: str,
        rakuten_report_execution: bool,
        rakuten_outlier_execution: bool,
        review_count_RefValue_mini: int,
        review_template: str,
        Default_taxRate: str,
        tax_Rounding: str,
        Default_profit_margin: str
    ) -> ParameterEntity:
        new_param = ParameterEntity(
            id=str(uuid.uuid4()),
            store_id=store_id,
            path_name=path_name,
            bundle_execution=bundle_execution,
            bundle_Default_manageNumber=bundle_Default_manageNumber,
            similar_title=similar_title,
            similar_category=similar_category,
            similar_genre=similar_genre,
            similar_created=similar_created,
            rpp_execution=rpp_execution,
            ranking_template=ranking_template,
            ranking_image_pc_width=ranking_image_pc_width,
            rakuten_report_execution=rakuten_report_execution,
            rakuten_outlier_execution=rakuten_outlier_execution,
            review_count_RefValue_mini=review_count_RefValue_mini,
            review_template=review_template,
            Default_taxRate=Default_taxRate,
            tax_Rounding=tax_Rounding,
            Default_profit_margin=Default_profit_margin
        )
        self.db.add(new_param)
        self.db.flush() 
        self.db.refresh(new_param)
        return new_param