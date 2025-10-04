from typing import List, Optional
from models.user_photo import UserPhoto
from extensions import db
import logging


class UserPhotoRepo:
    @staticmethod
    def create_user_photo(user_id, photoname) -> Optional[UserPhoto]:
        user_photo = UserPhoto(user_id=user_id, photoname=photoname)
        db.session.add(user_photo)
        try:
            db.session.commit()
            return user_photo
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating user_info for user {user_id}: {e}")
            return None

    @staticmethod
    def get_all_user_photo() -> List[UserPhoto]:
        return UserPhoto.query.all()

    @staticmethod
    def find_user_photo_by_user_id(user_id) -> Optional[UserPhoto]:
        return UserPhoto.query.filter_by(user_id=user_id).first()

    @staticmethod
    def delete_user_photo_by_user_id(user_id):
        UserPhoto.query.filter_by(user_id=user_id).delete()
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error delete user_info for user {user_id}: {e}")