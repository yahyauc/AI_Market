import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'smart_supermarket.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "smart-supermarket-secret-2025")
    LOW_STOCK_THRESHOLD = 5

    # ── YOLO Vision Models ────────────────────────────────────────
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
    MODULES_DIR  = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "Modules"))
    YOLO_EMPTY_SHELF_MODEL   = os.path.join(MODULES_DIR, "impty_shelfs.pt")
    YOLO_PRODUCT_DETECTOR    = os.path.join(MODULES_DIR, "Product_detector_model.pt")

    # ── Gmail SMTP ────────────────────────────────────────────────
    MAIL_SERVER  = "smtp.gmail.com"
    MAIL_PORT    = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_DEBUG   = False
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = ("Smart Supermarket", os.getenv("MAIL_USERNAME", ""))