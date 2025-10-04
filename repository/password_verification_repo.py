from typing import List, Optional
from models.password_verification_code import PasswordVerificationCode
from extensions import db
import logging

class PasswordVerificationCodeRepo:
    @staticmethod
    def create_password_verification_code(email, verification_code) -> Optional[PasswordVerificationCode]:
        password_verification_code = PasswordVerificationCode(email=email, verification_code=verification_code)
        db.session.add(password_verification_code)
        try:
            db.session.commit()
            return password_verification_code
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating password_verification_code for user {email}: {e}")
            return None

    @staticmethod
    def get_all_password_verification_code() -> List[PasswordVerificationCode]:
        return PasswordVerificationCode.query.all()

    @staticmethod
    def find_password_verification_code_by_email(email) -> Optional[PasswordVerificationCode]:
        return PasswordVerificationCode.query.filter_by(email=email).first()

    @staticmethod
    def delete_password_verification_code_by_email(email):
        PasswordVerificationCode.query.filter_by(email=email).delete()
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error delete password_verification_code for user {email}: {e}")