from sqlalchemy import DateTime, func
from extensions import db
import uuid


class TrainingFile(db.Model):
    __tablename__ = "training_file"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    model_id = db.Column(db.Integer, db.ForeignKey("trained_model.id"))
    filename = db.Column(db.String(50), nullable=False)
    # original_file_name是user上傳時，本機的file name
    original_file_name = db.Column(db.String(255), nullable=False)
    # 是否開始訓練
    start_train: bool = db.Column(db.Boolean, default=False, nullable=False)
    # 是否訓練完成
    is_trained: bool = db.Column(db.Boolean, default=False, nullable=False)
    upload_time = db.Column(DateTime(timezone=True), default=func.now())
    error_msg = db.Column(db.String(65), nullable=False)

    # 上傳file後先生成TrainingFile物件，再從TrainingFile object拿filename做為檔名存file。
    def __init__(self, user_id, model_id, original_file_name, filename=None):
        self.user_id = user_id
        self.model_id = model_id
        if filename is not None:
            self.filename = filename
        else:
            self.filename = str(uuid.uuid4()) + ".csv"
        self.original_file_name = original_file_name
        self.start_train = False
        self.is_trained = False
        self.error_msg = False
        

    def set_start_train(self, start_train: bool):
        self.start_train = start_train

    def set_is_trained(self, is_trained: bool):
        self.is_trained = is_trained
