from typing import List, Optional
import uuid
from models.training_file import TrainingFile
from extensions import db
import logging


class TrainingFileRepo:
    @staticmethod
    def create_trainingfile(
        user_id, model_id, original_file_name, filename=None
    ) -> Optional[TrainingFile]:
        file = TrainingFile(
            user_id=user_id,
            model_id=model_id,
            original_file_name=original_file_name,
            filename=filename,
        )
        db.session.add(file)
        try:
            db.session.commit()
            return file
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating training_file for user {user_id}: {e}")
            return None

    @staticmethod
    def get_all_trainingfile() -> List[TrainingFile]:
        return TrainingFile.query.all()

    @staticmethod
    def find_training_file_by_id(id) -> Optional[TrainingFile]:
        return TrainingFile.query.filter_by(id=id).first()

    @staticmethod
    def find_trainingfile_by_user_id(user_id) -> List[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id).all()

    # 取得已訓練的file
    @staticmethod
    def find_training_file_by_user_id(user_id) -> List[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id, is_trained=True).all()

    # 取得未訓練的file
    @staticmethod
    def find_not_training_file_by_user_id(user_id) -> List[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id, is_trained=False).all()

    @staticmethod
    def find_first_training_file_by_user_id(user_id) -> Optional[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id).first()

    @staticmethod
    def find_first_training_file_by_user_and_model_id(
        user_id, model_id
    ) -> Optional[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id, model_id=model_id).first()

    # 上傳時就的file會覆蓋舊的file，所以這個array永遠只會有一個items
    @staticmethod
    def find_training_file_by_user_and_model_id(
        user_id, model_id
    ) -> list[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id, model_id=model_id).all()

    @staticmethod
    def delete_training_file_by_file_id(file_id):
        TrainingFile.query.filter_by(id=file_id).delete()
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error delete training_file for file {file_id}: {e}")

    @staticmethod
    def delete_training_file_by_user_and_model_id(user_id: int, model_id: int) -> bool:
        try:
            TrainingFile.query.filter_by(user_id=user_id, id=model_id).delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting training files for model {model_id}: {e}")
            return False

    @staticmethod
    def save_training_file():
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating file: {e}")
