from sqlalchemy import DateTime, func
from extensions import db
import uuid


class SharedModel(db.Model):
    __tablename__ = "shared_model"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_date: DateTime = db.Column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    # 模型
    model_id = db.Column(db.Integer, db.ForeignKey("trained_model.id"), nullable=False)
    # 取走模型的人（一個link只能用一次）
    acquirer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    link: str = db.Column(db.String(50), nullable=False)

    def __init__(self, model_id):
        self.model_id = model_id
        self.link = str(uuid.uuid4())
