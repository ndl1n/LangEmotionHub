from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lastname = db.Column(db.String(50), nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __init__(self, lastname, firstname, email, password):
        self.lastname = lastname
        self.firstname = firstname
        self.email = email
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """
        驗證輸入的密碼是否與存儲的哈希密碼相符。

        Parameters:
        - password (str): 用戶輸入的明文密碼。

        Returns:
        - bool: 如果密碼相符，返回 True，否則返回 False。
        """
        return check_password_hash(self.password, password)

    @classmethod
    def get_user_by_email(cls, email):
        """
        根據信箱查找並返回對應的 User 實例。

        Parameters:
        - email (str): 要查找的信箱。

        Returns:
        - User 實例，如果找到；否則返回 None。
        """
        return cls.query.filter_by(email=email).first()

    @classmethod
    def is_user_id_exists(cls, user_id):
        """
        檢查給定的 user_id 是否存在於資料庫中。

        Parameters:
        - user_id (int): 要查找的使用者 ID。

        Returns:
        - bool: 如果 user_id 存在於資料庫，返回 True，否則返回 False。
        """
        return db.session.query(cls.id).filter_by(id=user_id).scalar() is not None

    def change_password(self, new_password):
        """
        更改使用者的密碼，並將加密後的新密碼保存到資料庫中。

        Parameters:
        - new_password (str): 使用者的新密碼。

        Returns:
        - None
        """
        self.password = generate_password_hash(new_password)
        db.session.commit()

    def save(self):
        """
        將當前 User 實例保存到資料庫中。
        """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """
        從資料庫中刪除當前 User 實例。
        """
        db.session.delete(self)
        db.session.commit()


class RefreshToken(db.Model):
    __tablename__ = "refreshTokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    token = db.Column(db.Text, nullable=False)
    revoked = db.Column(db.Boolean, default=False)

    def save(self):
        """
        將當前 RefreshToken 實例保存到資料庫中。
        """
        db.session.add(self)
        db.session.commit()

    def revoke(self):
        """
        撤銷當前的 RefreshToken，將其設置為已撤銷狀態。
        """
        self.revoked = True
        db.session.commit()

    @classmethod
    def find_by_token_and_user(cls, token, user_id):
        """
        根據 token 和 user_id 查找對應的 RefreshToken 實例。

        Parameters:
        - token (str): 要查找的 Refresh Token。
        - user_id (int): 用戶的 ID。

        Returns:
        - RefreshToken 實例，如果找到；否則返回 None。
        """
        return cls.query.filter_by(token=token, user_id=user_id).first()

    @classmethod
    def delete_revoked_tokens(cls, user_id):
        """
        刪除指定用戶所有已撤銷的 refresh token。

        Parameters:
        - user_id (int): 用戶的 ID。

        Returns:
        - None
        """
        cls.query.filter_by(user_id=user_id, revoked=True).delete()
        db.session.commit()

    @classmethod
    def find_by_userId(cls, user_id):
        """
        根據用戶 ID 查找對應的 refresh token。

        Parameters:
        - user_id (int): 用戶的 ID。

        Returns:
        - RefreshToken 實例，如果找到；否則返回 None。
        """
        return cls.query.filter_by(user_id=user_id).first()
