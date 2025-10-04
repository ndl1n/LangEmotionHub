from datetime import timedelta
from flasgger import swag_from
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)
from models.user import User, RefreshToken
from sqlalchemy.exc import SQLAlchemyError
from utils.validators import is_valid_email, is_strong_password
import logging

import utils.mail_sender as mail_sender
from repository.password_verification_repo import PasswordVerificationCodeRepo
import pyotp
from repository.userphoto_repo import UserPhotoRepo

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

# BASE_URL = "http://192.168.1.109:8080" # 安的IP
BASE_URL = "https://nccu-group-8.work"   # 主機IP

@auth_bp.post("/register")
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此API用來處理用戶註冊，會檢查用戶名、密碼是否有效，並將新用戶保存至資料庫。

    Input:
        - JSON 格式的請求，包含 'lastname'、'firstname'、'email' 和 'password' 字段。

    Steps:
        1. 檢查所有必須的字段是否提供且有效。
        2. 檢查使用者電子郵件是否已被使用。
        3. 檢查密碼強度。
        4. 如果所有檢查通過，創建新的用戶並保存到資料庫。
        5. 處理可能的資料庫錯誤或其他異常。

    Returns:
        - JSON 格式的回應消息:
            - 註冊成功: 包含成功消息。
            - 註冊失敗: 包含錯誤消息和相應的 HTTP status code。
    """,
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'lastname': {
                        'type': 'string',
                        'description': '用戶姓氏',
                        'example': 'Lin'
                    },
                    'firstname': {
                        'type': 'string',
                        'description': '用戶名字',
                        'example': 'An-An'
                    },
                    'email': {
                        'type': 'string',
                        'description': '用戶電子郵件',
                        'example': 'andy1234@example.com'
                    },
                    'password': {
                        'type': 'string',
                        'description': '用戶密碼，必須至少8個字符，並包含字母和數字',
                        'example': 'andy1234'
                    }
                },
                'required': ['lastname', 'firstname', 'email', 'password']
            }
        }
    ],
    'responses': {
        200: {
            'description': '註冊成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '註冊成功'
                    }
                }
            }
        },
        400: {
            'description': '註冊失敗，輸入無效或電子郵件已存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '此電子郵件已被使用'
                    }
                }
            }
        },
        500: {
            'description': '伺服器錯誤，可能是資料庫異常',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '資料庫錯誤，請稍後再試'
                    }
                }
            }
        }
    }
})
def register():
    try:
        # 從請求中獲取用戶輸入的姓名、電子郵件和密碼
        lastname = request.json.get("lastname", None)
        firstname = request.json.get("firstname", None)
        email = request.json.get("email", None)
        password = request.json.get("password", None)

        # 檢查輸入是否有效
        if not lastname or not firstname or not email or not password:
            return jsonify(message="姓氏、名字、電子郵件和密碼不可為空"), 400

        # 檢查電子郵件是否符合規範
        if not is_valid_email(email):
            return jsonify(message="使用者電子郵件不符合規範"), 400

        # 檢查密碼強度
        if not is_strong_password(password):
            return jsonify(message="密碼必須至少包含8個字符，並包含字母和數字"), 400

        # 創建新的用戶實例
        new_user = User(lastname=lastname, firstname=firstname, email=email, password=password)

        # 檢查電子郵件是否已存在
        user = User.get_user_by_email(email=email)
        if user is not None:
            return jsonify(message="此電子郵件已被使用"), 400

        # 保存新用戶到數據庫
        new_user.save()

        # 返回成功消息
        return jsonify(message="註冊成功"), 200

    except SQLAlchemyError as e:
        # 記錄資料庫錯誤並返回錯誤消息
        logger.error(f"Database error: {e}")
        return jsonify(message="資料庫錯誤，請稍後再試"), 500
    except Exception as e:
        # 記錄一般錯誤並返回錯誤消息
        logger.error(f"Registration failed: {e}")
        return jsonify(message=f"註冊失敗: {str(e)}"), 500


@auth_bp.post("/login")
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此API用來處理用戶登入，會驗證電子郵件和密碼，並返回 access token 和 refresh token。

    Input:
    - 期望接收到包含 'email' 和 'password' 字段的 JSON 請求。

    Steps:
    1. 驗證電子郵件和密碼是否存在。
    2. 使用提供的電子郵件從數據庫中檢索用戶。
    3. 將輸入的密碼與存儲的哈希密碼進行驗證。
    4. 如果身份驗證成功，生成並返回 access token 和 refresh token。
    5. 處理潛在錯誤並返回適當的 HTTP 狀態碼。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回成功消息、用戶資訊、access token 和 refresh token。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'email': {
                        'type': 'string',
                        'description': '用戶電子郵件',
                        'example': 'andy1234@example.com'
                    },
                    'password': {
                        'type': 'string',
                        'description': '用戶密碼',
                        'example': 'andy1234'
                    }
                },
                'required': ['email', 'password']
            }
        }
    ],
    'responses': {
        200: {
            'description': '登入成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '登入成功'
                    },
                    'user_id': {
                        'type': 'integer',
                        'example': 1
                    },
                    'lastname': {
                        'type': 'string',
                        'example': 'Lin'
                    },
                    'firstname': {
                        'type': 'string',
                        'example': 'An-An'
                    },
                    'email': {
                        'type': 'string',
                        'example': 'andy1234@example.com'
                    },
                    'access_token': {
                        'type': 'string',
                        'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                    },
                    'refresh_token': {
                        'type': 'string',
                        'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                    }
                }
            }
        },
        400: {
            'description': '請求中缺少電子郵件或密碼',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '電子郵件或密碼不可為空'
                    }
                }
            }
        },
        401: {
            'description': '電子郵件或密碼錯誤',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '電子郵件或密碼錯誤'
                    }
                }
            }
        },
        500: {
            'description': '伺服器內部錯誤',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '資料庫錯誤，請稍後再試'
                    }
                }
            }
        }
    }
})
def login():
    try:
        # 從請求中獲取用戶輸入的電子郵件和密碼
        email = request.json.get("email", None)
        password = request.json.get("password")

        # 檢查是否提供了電子郵件和密碼
        if not email or not password:
            return jsonify(message="電子郵件或密碼不可為空"), 400

        # 從數據庫中檢索用戶
        user = User.get_user_by_email(email=email)
        if user is None or not user.check_password(password):
            return jsonify(message="電子郵件或密碼錯誤"), 401
        
        photo_name = "avatar.png"
        user_info = UserPhotoRepo.find_user_photo_by_user_id(user.id)
        if user_info:
            photo_name =user_info.photoname
        
        if photo_name == "avatar.png":
            photo_path = f"{BASE_URL}/userinfo/images/default/{photo_name}"
        else:
            photo_path = f"{BASE_URL}/userinfo/images/{user.id}/{photo_name}"

        # 刪除之前的 refresh token
        RefreshToken.delete_revoked_tokens(user.id)

        # 成功登入時生成 token
        access_token = create_access_token(
            identity=email, expires_delta=timedelta(minutes=30)
        )
        refresh_token = create_refresh_token(
            identity=email, expires_delta=timedelta(days=7)
        )

        # 保存新的 refresh token 到數據庫
        new_refresh_token = RefreshToken(
            user_id=user.id,  # 使用用戶ID
            token=refresh_token,
        )

        new_refresh_token.save()

        return (
            jsonify(
                message="登入成功", 
                user_id=user.id,
                lastname=user.lastname,
                firstname=user.firstname,
                email=user.email,
                access_token=access_token, 
                refresh_token=refresh_token,
                photo=photo_path
            ),
            200,
        )

    except SQLAlchemyError as e:
        # 處理與數據庫相關的錯誤
        logger.error(f"資料庫錯誤: {str(e)}")
        return jsonify(message="資料庫錯誤，請稍後再試"), 500

    except Exception as e:
        # 處理其他潛在的異常
        logger.error(f"登入過程中出現錯誤: {str(e)}")
        return jsonify(message=f"登入失敗: {str(e)}"), 500


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此 API 用於使用已驗證的 Refresh Token 來生成新的 Access Token。

    Steps:
    1. 使用裝飾器 `@jwt_required(refresh=True)` 驗證請求中的 Refresh Token。
    2. 獲取當前用戶的身份（即 `current_email`）。
    3. 為當前用戶生成新的 Access Token。
    4. 返回新的 Access Token 給客戶端。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回新的 Access Token。
      - 失敗時：由 `@jwt_required` 裝飾器自動處理，通常會返回 401 或 422 錯誤。
    """,
    'parameters': [
        {
            "name": "Authorization",
            "in": "header",
            "required": True,
            "description": "Bearer token for authorization",
            "schema": {
                "type": "string",
                "example": "Bearer "
            }
        }
    ],
    'responses': {
        200: {
            'description': '成功刷新 Access Token',
            'schema': {
                'type': 'object',
                'properties': {
                    'access_token': {
                        'type': 'string',
                        'description': '新的 Access Token',
                        'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                    }
                }
            }
        },
        401: {
            'description': 'Refresh Token 無效或已撤銷',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': 'Refresh Token 已失效或已撤銷'
                    }
                }
            }
        },
        500: {
            'description': '伺服器內部錯誤',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '刷新 Access Token 失敗: 詳細錯誤信息'
                    }
                }
            }
        }
    },
    'security': [
        {
            'Bearer': []
        }
    ]
})
def refresh():
    try:
        # 從 JWT 中獲取當前使用者身份 (email)
        current_email = get_jwt_identity()
        user = User.get_user_by_email(current_email)

        # 檢查 Authorization header 並提取 refresh token
        auth_header = request.headers.get("Authorization", None)
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify(message="Authorization header 缺失或格式錯誤"), 401

        refresh_token = auth_header.split(" ")[1]

        # 從資料庫中查找這個 Refresh Token
        stored_token = RefreshToken.find_by_token_and_user(refresh_token, user.id)

        if not stored_token or stored_token.revoked:
            return jsonify(message="Refresh Token 已失效或已撤銷"), 401

        # 為當前使用者生成新的 Access Token
        new_access_token = create_access_token(identity=current_email)

        # 返回新的 Access Token
        return jsonify(access_token=new_access_token), 200

    except Exception as e:
        # 處理可能發生的異常，並記錄錯誤信息
        logger.error(f"刷新 Access Token 過程錯誤: {str(e)}")
        return jsonify(message=f"刷新 Access Token 失敗: {str(e)}"), 500


@auth_bp.post("/logout")
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此 API 用於當用戶登出時，撤銷與用戶關聯的 Refresh Token 並返回登出成功的訊息。

    Steps:
    1. 獲取當前使用者的身份。
    2. 根據身份從資料庫中檢索對應的使用者。
    3. 從資料庫查找當前使用者的 refresh token。
    4. 如果找到 refresh token 且尚未被撤銷，將其標記為已撤銷。
    5. 返回成功的登出消息。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回登出成功的消息。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
    'parameters': [
        {
            "name": "Authorization",
            "in": "header",
            "required": True,
            "description": "Bearer token for authorization",
            "schema": {
                "type": "string",
                "example": "Bearer "
            }
        }
    ],
    'responses': {
        200: {
            'description': '成功登出並撤銷 Refresh Token',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '登出成功'
                    }
                }
            }
        },
        500: {
            'description': '伺服器內部錯誤',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '登出失敗: 詳細錯誤信息'
                    }
                }
            }
        }
    },
    'security': [
        {
            'Bearer': []
        }
    ]
})
def logout():
    try:
        # 獲取當前用戶的身份
        current_email = get_jwt_identity()
        user = User.get_user_by_email(current_email)

        # 從資料庫查找對應的 Refresh Token
        stored_token = RefreshToken.find_by_userId(user.id)

        if stored_token and not stored_token.revoked:
            stored_token.revoke()

        return jsonify(message="登出成功"), 200

    except Exception as e:
        logger.error(f"登出過程錯誤: {str(e)}")
        return jsonify(message=f"登出失敗: {str(e)}"), 500


@auth_bp.post("/delete")
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此 API 用於刪除當前登入用戶的帳號，並返回相應的訊息。

    Steps:
    1. 驗證請求中的 Access Token，確保用戶已登入。
    2. 根據目前用戶的身份獲取用戶資訊。
    3. 如果找到對應的用戶，從資料庫刪除該用戶。
    4. 返回成功或失敗的訊息給客戶端。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回 "帳號刪除成功" 訊息和 HTTP 200 狀態碼。
      - 失敗時：返回錯誤訊息和相應的 HTTP 狀態碼。
    """,
    'parameters': [
        {
            "name": "Authorization",
            "in": "header",
            "required": True,
            "description": "Bearer token for authorization",
            "schema": {
                "type": "string",
                "example": "Bearer "
            }
        }
    ],
    'responses': {
        200: {
            'description': '帳號刪除成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '帳號刪除成功'
                    }
                }
            }
        },
        404: {
            'description': '找不到要刪除的帳號',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '找不到要刪除的帳號'
                    }
                }
            }
        },
        500: {
            'description': '伺服器錯誤，帳號刪除失敗',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '帳號刪除失敗: 具體錯誤信息'
                    }
                }
            }
        }
    },
    'security': [
        {
            'Bearer': []
        }
    ],
})
def delete():
    current_email = get_jwt_identity()

    try:
        user_to_delete = User.get_user_by_email(current_email)
        if user_to_delete:
            try:
                # 刪除用戶並提交變更
                User.delete(user_to_delete)
                logger.info(f"用戶 {current_email} 帳號刪除成功")
                return jsonify(message="帳號刪除成功"), 200
            except Exception as e:
                logger.error(f"刪除用戶 {current_email} 帳號時發生錯誤: {str(e)}")
                return jsonify(message=f"帳號刪除失敗: {str(e)}"), 500
        else:
            logger.warning(f"用戶 {current_email} 帳號刪除失敗：帳號不存在")
            return jsonify(message="找不到要刪除的帳號"), 404
    except Exception as e:
        logger.error(f"處理帳號刪除請求時發生錯誤: {str(e)}")
        return jsonify(message=f"帳號刪除失敗: {str(e)}"), 500


@auth_bp.post("/forgotPassword")
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此API用來處理用戶的忘記密碼請求，將驗證碼發送到用戶的電子郵件並保存至資料庫。

    Input:
        - JSON: 'email' 

    Steps:
        1. 檢查所有必須的字段是否提供且有效。
        2. 檢查使用者電子郵件是否存在於系統中。
        3. 如果該用戶之前請求過，則刪除之前的驗證碼。
        4. 創建新的驗證碼並保存到資料庫中。
        5. 向用戶的電子郵件地址發送驗證碼。

    Returns:
        - JSON 格式的回應消息:
            - 成功請求驗證碼: 包含成功消息並發送電子郵件。
            - 請求失敗: 包含錯誤消息和相應的 HTTP 狀態碼。
    """,
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'email': {
                        'type': 'string',
                        'description': '用戶電子郵件地址',
                        'example': 'andy1234@example.com'
                    },
                },
                'required': ['email']
            }
        }
    ],
    'responses': {
        200: {
            'description': '請求成功，驗證信已寄出',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '驗證信已成功寄出'
                    }
                }
            }
        },
        400: {
            'description': '請求失敗，輸入無效或電子郵件不存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '此電子郵件不存在或無效'
                    }
                }
            }
        },
        500: {
            'description': '伺服器錯誤，可能是資料庫或其他問題',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '資料庫錯誤，請稍後再試'
                    }
                }
            }
        }
    }
})
def forgotPassword():
    try:
        # 從請求中獲取用戶輸入的電子郵件
        email = request.json.get("email", None)
        
        # 檢查電子郵件是否符合規範
        if not is_valid_email(email):
            return jsonify(message="使用者電子郵件不符合規範"), 400

        # 檢查電子郵件是否已存在
        user = User.get_user_by_email(email=email)
        if user is None:
            return jsonify(message="此電子郵件不存在"), 400
        
        # 刪除之前的驗證碼
        saved_verification_code = PasswordVerificationCodeRepo.find_password_verification_code_by_email(email=email)
        if saved_verification_code is not None:
            PasswordVerificationCodeRepo.delete_password_verification_code_by_email(saved_verification_code.email)

        # 創建新的OTP
        totp = pyotp.TOTP(pyotp.random_base32())
        verification_code = totp.now() 

        # 保存忘記密碼的驗證碼到DB
        saved_verification_code = PasswordVerificationCodeRepo.create_password_verification_code(email=email, verification_code=verification_code)
        if saved_verification_code is None:
            return jsonify(message="資料庫錯誤，請稍後再試"), 500
        
        subject = "忘記密碼驗證碼"
        mail_content = f"您的驗證碼是 {verification_code}"

        # 寄送驗證信
        mail_sender.send_email(email, subject, mail_content)

        # 返回成功消息
        return jsonify(message="驗證信已成功寄出"), 200

    except SQLAlchemyError as e:
        # 記錄資料庫錯誤並返回錯誤消息
        logger.error(f"Database error: {e}")
        return jsonify(message="資料庫錯誤，請稍後再試"), 500
    except Exception as e:
        # 記錄一般錯誤並返回錯誤消息
        logger.error(f"Registration failed: {e}")
        return jsonify(message=f"請求失敗: {str(e)}"), 500


@auth_bp.post("/resetPassword")
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此API用來處理用戶重設密碼請求並保存新密碼至資料庫。

    Input:
        - JSON: 'email', 'verificationCode', 'password1', 和 'password2'

    Steps:
        1. 檢查所有必須的字段是否提供且有效。
        2. 驗證使用者的電子郵件和驗證碼。
        3. 確認新密碼是否符合強密碼規範且兩次輸入一致。
        4. 如果驗證通過，則更新用戶密碼並刪除驗證碼。

    Returns:
        - JSON 格式的回應消息:
            - 密碼更新成功: 包含成功消息。
            - 密碼更新失敗: 包含錯誤消息和相應的 HTTP 狀態碼。
    """,
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'email': {
                        'type': 'string',
                        'description': '用戶電子郵件',
                        'example': 'andy1234@example.com'
                    },
                    'verificationCode': {
                        'type': 'string',
                        'description': '驗證碼，用來驗證用戶的身份',
                        'example': '123456'
                    },
                    'password1': {
                        'type': 'string',
                        'description': '第一次輸入的新密碼',
                        'example': 'ABC1234abc'
                    },
                    'password2': {
                        'type': 'string',
                        'description': '第二次輸入的新密碼（必須與第一次密碼一致）',
                        'example': 'ABC1234abc'
                    }
                },
                'required': ['email', 'verificationCode', 'password1', 'password2']
            }
        }
    ],
    'responses': {
        200: {
            'description': '密碼更新成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '密碼更新成功'
                    }
                }
            }
        },
        400: {
            'description': '請求失敗，驗證碼錯誤、密碼格式錯誤或兩次密碼不一致',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '驗證碼錯誤或密碼不一致'
                    }
                }
            }
        },
        500: {
            'description': '伺服器錯誤，可能是資料庫異常',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '資料庫錯誤，請稍後再試'
                    }
                }
            }
        }
    }
})
def resetPassword():
    try:
        # 從請求中獲取用戶輸入的電子郵件
        email = request.json.get("email", None)
        verficationCode = request.json.get("verificationCode", None)
        password1 = request.json.get("password1", None)
        password2 = request.json.get("password2", None)
        
        verficationCode_exist = PasswordVerificationCodeRepo.find_password_verification_code_by_email(email=email).verification_code
        if verficationCode_exist != str(verficationCode):
            return jsonify(message="驗證碼錯誤"), 400
        
        if is_strong_password(password1) == False:
            return jsonify(message="密碼格式錯誤"), 400
        
        if password1 != password2:
            return jsonify(message="兩次密碼不一致"), 400
        
        user = User.get_user_by_email(email=email)
        user.change_password(password1)
        
        # 若密碼更新成功，刪除驗證碼
        PasswordVerificationCodeRepo.delete_password_verification_code_by_email(email=email)

        return jsonify(message="密碼更新成功"), 200

    except SQLAlchemyError as e:
        # 記錄資料庫錯誤並返回錯誤消息
        logger.error(f"Database error: {e}")
        return jsonify(message="資料庫錯誤，請稍後再試"), 500
    except Exception as e:
        # 記錄一般錯誤並返回錯誤消息
        logger.error(f"Registration failed: {e}")
        return jsonify(message=f"請求失敗: {str(e)}"), 500