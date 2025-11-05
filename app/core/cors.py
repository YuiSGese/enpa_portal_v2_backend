from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app, env: str = "development"):
    """
    Thiết lập CORS cho ứng dụng FastAPI
    :param app: instance của FastAPI
    :param env: môi trường hiện tại (development | production)
    """
    if env == "development":
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    else:
        origins = [
            "https://your-frontend-domain.com",  # Production domain
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
