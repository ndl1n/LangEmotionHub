from sqlalchemy import DateTime, func
from extensions import db


class EventJournal(db.Model):
    __tablename__ = 'event_journal'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 假設你有一個 users 表
    event_title = db.Column(db.String(255), nullable=False)
    event_content = db.Column(db.Text, nullable=False)
    event_date = db.Column(DateTime(timezone=True), nullable=False)
    event_picture = db.Column(db.String(255), nullable=False)
    created_at = db.Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    def __init__(self, user_id,event_title, event_content, event_date, event_picture):
        self.user_id = user_id
        self.event_title = event_title
        self.event_date = event_date
        self.event_picture = event_picture
        self.event_content = event_content