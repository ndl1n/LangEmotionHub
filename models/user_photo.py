from extensions import db

class UserPhoto(db.Model):
    __tablename__ = "user_photo"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    photoname = db.Column(db.String(255), nullable=True)

    def __init__(self, user_id, photoname=None):
        self.user_id = user_id
        self.photoname = photoname
