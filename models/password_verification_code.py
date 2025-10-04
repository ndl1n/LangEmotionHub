from datetime import timedelta
from sqlalchemy import DateTime, func
from extensions import db


class PasswordVerificationCode(db.Model):
    __tablename__ = "password_verification_code"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False)
    verification_code = db.Column(db.String(255), nullable=True)
    created_at = db.Column(DateTime, server_default=func.now())
    expires_at = db.Column(DateTime, server_default=(func.now() + timedelta(minutes=15)))

    def __init__(self, email, verification_code):
        self.email = email
        self.verification_code = verification_code
        
        
