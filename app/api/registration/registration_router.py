from fastapi import APIRouter, Depends, HTTPException
from app.api.registration.registration_schemas import RegistrationRequest, RegistrationResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/registration", tags=["registration"])

@router.post("/automatic_registration", response_model=RegistrationResponse)
def automatic_registration(registration_request: RegistrationRequest, db: Session = Depends(get_db)):

    return {
        
    }
