from typing import Optional
from sqlalchemy import DateTime, func
from extensions import db
import uuid


class TrainedModel(db.Model):
    __tablename__ = "trained_model"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("user.id"))
    modelname: str = db.Column(db.String(50), nullable=False)
    model_original_name: str = db.Column(db.String(255), nullable=True)
    modelphoto: str = db.Column(db.String(255), nullable=True)
    anticipation = db.Column(db.Text, nullable=True)
    start_time: DateTime = db.Column(DateTime(timezone=True), nullable=True)
    end_time: Optional[DateTime] = db.Column(DateTime(timezone=True), nullable=True)

    def __init__(
        self, user_id, model_original_name, modelphoto, anticipation, end_time=None
    ):
        self.user_id = user_id
        self.modelname = str(uuid.uuid4())
        self.model_original_name = model_original_name
        self.modelphoto = modelphoto
        self.anticipation = anticipation
        self.end_time = end_time
