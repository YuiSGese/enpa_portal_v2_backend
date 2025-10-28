from fastapi.responses import JSONResponse

def custom_error_response(status_code: int = 400, message: str = ""):
    """
    Trả về JSONResponse chuẩn, chỉ cần truyền message và status_code
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "message": message
        }
    )
