import logging
from flasgger import swag_from
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from datetime import datetime, timezone
from repository.event_journal_repo import EventJournalRepository
from utils import chroma

event_bp = Blueprint("event", __name__)
logger = logging.getLogger(__name__)

# BASE_URL = "http://192.168.1.109:8080" # 安的IP
BASE_URL = "https://nccu-group-8.work"   # 主機IP


@event_bp.post("/create_event")
@jwt_required()
@swag_from(
    {
        "tags": ["EventJournal"],
        "description": """
    此 API 用於創建新的事件。使用者可以提交事件的標題和內容，後端將其保存到資料庫中。

    Input:
    - 接收到包含 'event_title' 和 'event_content' 字段的 JSON 請求。

    Steps:
    1. 驗證使用者身份。
    2. 從資料庫中查詢該使用者。
    3. 檢查請求中是否包含事件標題和內容，並確認這些字段不為空。
    4. 如果所有驗證通過，將事件信息保存到資料庫。
    5. 返回創建事件的結果，包括事件 ID 和創建時間。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回成功消息、事件 ID、創建時間和更新時間。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "event_title": {
                            "type": "string",
                            "description": "事件的標題",
                            "example": "生日派對",
                        },
                        "event_content": {
                            "type": "string",
                            "description": "事件的具體內容",
                            "example": "在家舉辦一個生日派對",
                        },
                        "event_date": {
                            "type": "string",
                            "format": "date",
                            "description": "事件的日期",
                            "example": "2023-12-25"
                        },
                        "event_picture": {
                            "type": "string",
                            "description": "事件的日期",
                            "example": "event_picture1.jpg"
                        },
                    },
                    "required": ["event_title", "event_content"],
                },
            },
        ],
        "responses": {
            201: {
                "description": "事件創建成功",
                "schema": {
                    "type": "object",
                    "properties": {
                        "msg": {"type": "string", "example": "事件創建成功"},
                        "event_id": {"type": "integer", "example": 1},
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-10-08T10:00:00Z",
                        },
                        "updated_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-10-08T10:00:00Z",
                        },
                    },
                },
            },
            400: {
                "description": "標題或內容為空",
                "schema": {
                    "type": "object",
                    "properties": {"msg": {"type": "string", "example": "標題和內容不能為空"}},
                },
            },
            404: {
                "description": "使用者不存在",
                "schema": {
                    "type": "object",
                    "properties": {"message": {"type": "string", "example": "使用者不存在"}},
                },
            },
            500: {
                "description": "伺服器內部錯誤",
                "schema": {
                    "type": "object",
                    "properties": {
                        "msg": {"type": "string", "example": "創建事件時發生錯誤"},
                        "error": {"type": "string", "example": "具體的錯誤信息"},
                    },
                },
            },
        },
    }
)
def create_event():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    # 緩存請求的 JSON 數據
    data = request.get_json()

    # 驗證事件標題和內容是否為空
    event_title = data.get("event_title")
    event_content = data.get("event_content")
    event_date = data.get("event_date")
    event_picture = data.get("event_picture")

    if not event_title or not event_content:
        return jsonify({"msg": "標題和內容不能為空"}), 400

    try:
        # 創建新的事件
        event = EventJournalRepository.create_event(user.id, event_title, event_content, event_date, event_picture)

        # 新增到向量資料庫
        collection_name = f"collection_{user.id}"
        collection = chroma.create_collection(collection_name)
        metadata = {"user_id": user.id, "event_title": event_title, "event_date": event_date}
        chroma.add_document(
            collection=collection,
            document=f"{event_date}:{event_title}是{event_content}",
            id=str(event.id),
            metadata=metadata,
        )

        return (
            jsonify(
                {
                    "msg": "事件創建成功",
                    "event_id": event.id,
                    "created_at": event.created_at.isoformat(),
                    "updated_at": event.updated_at.isoformat(),
                    "event_date": event.event_date.isoformat(),
                    "event_picture": f'{BASE_URL}/userinfo/images/default/{event.event_picture}'
                }
            ),
            201,
        )

    except Exception as e:
        # 捕獲潛在的異常，並返回相應的錯誤訊息
        return jsonify({"msg": "創建事件時發生錯誤", "error": str(e)}), 500


@event_bp.get("/getevents")
@jwt_required()
@swag_from(
    {
        "tags": ["EventJournal"],
        "description": """
    此 API 用於查詢特定使用者的所有事件列表。

    Steps:
    1. 驗證使用者身份。
    2. 確認所查詢的使用者 ID 是否存在。
    3. 從資料庫查詢與該使用者 ID 關聯的所有事件。
    4. 返回事件列表，包括事件的標題、內容和創建時間。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回事件列表，包括每個事件的詳細資訊。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
        ],
        "responses": {
            200: {
                "description": "事件列表成功返回",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "integer", "example": 1},
                            "event_title": {"type": "string", "example": "生日派對"},
                            "event_content": {
                                "type": "string",
                                "example": "在家舉辦一個生日派對",
                            },
                            "created_at": {
                                "type": "string",
                                "format": "date-time",
                                "example": "2024-10-08T10:00:00Z",
                            },
                            "updated_at": {
                                "type": "string",
                                "format": "date-time",
                                "example": "2024-10-08T11:00:00Z",
                            },
                        },
                    },
                },
            },
            404: {
                "description": "使用者不存在或未找到事件",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "使用者不存在或沒有事件"}
                    },
                },
            },
            500: {
                "description": "伺服器內部錯誤",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "查詢事件時發生錯誤"}
                    },
                },
            },
        },
    }
)
def get_events():
    current_email = get_jwt_identity()

    user_id = User.get_user_by_email(current_email).id
    # 確認使用者是否存在
    user_exists = User.is_user_id_exists(user_id)
    if not user_exists:
        return jsonify({"error": "User ID not found"}), 404

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    try:
        # 查詢與該使用者 ID 關聯的所有事件
        events = EventJournalRepository.get_events_by_user_id(user.id)

        # 檢查是否有事件
        if not events:
            return jsonify(message="沒有事件存在"), 404

        # 構建事件列表的回應
        event_list = [
            {
                "event_id": event.id,
                "event_title": event.event_title,
                "event_content": event.event_content,
                "created_at": event.created_at.isoformat(),
                "updated_at": event.updated_at.isoformat(),
                "event_date": event.event_date.isoformat(),
                "event_picture": f'{BASE_URL}/userinfo/images/default/{event.event_picture}'
            }
            for event in events
        ]

        return jsonify(event_list), 200

    except Exception as e:
        return jsonify(message="查詢事件時發生錯誤", error=str(e)), 500


@event_bp.get("/getevent/<int:event_id>")
@jwt_required()
@swag_from(
    {
        "tags": ["EventJournal"],
        "description": """
    此 API 用於查詢特定使用者的單個事件。

    Steps:
    1. 驗證使用者身份。
    2. 確認所查詢的事件 ID 是否存在並屬於當前使用者。
    3. 從資料庫查詢與該事件 ID 關聯的事件。
    4. 返回事件的詳細資訊，包括標題、內容和創建時間。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回事件的詳細資訊。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
        "parameters": [
            {
                "name": "event_id",
                "in": "path",
                "required": True,
                "type": "integer",
                "description": "要查詢的事件 ID",
                "example": 1,
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
        ],
        "responses": {
            200: {
                "description": "事件成功返回",
                "schema": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "integer", "example": 1},
                        "event_title": {"type": "string", "example": "生日派對"},
                        "event_content": {"type": "string", "example": "在家舉辦一個生日派對"},
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-10-08T10:00:00Z",
                        },
                        "updated_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-10-08T10:00:00Z",
                        },
                    },
                },
            },
            403: {
                "description": "事件不屬於當前用戶",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "事件不屬於當前用戶"}
                    },
                },
            },
            404: {
                "description": "事件不存在",
                "schema": {
                    "type": "object",
                    "properties": {"message": {"type": "string", "example": "事件不存在"}},
                },
            },
            500: {
                "description": "伺服器內部錯誤",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "查詢事件時發生錯誤"}
                    },
                },
            },
        },
    }
)
def get_event(event_id):
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    try:
        # 查詢與該事件 ID 關聯的事件
        event = EventJournalRepository.get_event_by_event_id(event_id)

        # 檢查事件是否存在
        if event is None:
            return jsonify(message="事件不存在"), 404

        # 檢查該事件是否屬於當前使用者
        if event.user_id != user.id:
            return jsonify(message="事件不屬於當前用戶"), 403

        # 構建事件的回應
        event_response = {
            "event_id": event.id,
            "event_title": event.event_title,
            "event_content": event.event_content,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.updated_at.isoformat(),
            "event_date": event.event_date.isoformat(),
            "event_picture": f'{BASE_URL}/userinfo/images/default/{event.event_picture}'
        }

        return jsonify(event_response), 200

    except Exception as e:
        return jsonify(message="查詢事件時發生錯誤", error=str(e)), 500


@event_bp.put("/update_event/<int:event_id>")
@jwt_required()
@swag_from(
    {
        "tags": ["EventJournal"],
        "description": """
    此 API 用於更新已存在的事件內容或標題。

    Steps:
    1. 驗證使用者身份。
    2. 查詢並驗證該事件是否屬於當前使用者。
    3. 更新事件內容到資料庫。
    4. 返回更新後的事件詳情。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回更新後的事件詳情。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
        "parameters": [
            {
                "name": "event_id",
                "in": "path",
                "required": True,
                "type": "integer",
                "description": "要更新的事件 ID",
                "example": 1,
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "event_title": {"type": "string", "example": "更新的生日派對"},
                        "event_content": {"type": "string", "example": "這是一個更新的生日派對內容"},
                        "event_date": {"type": "string", "example": "更新更新的時間"},
                        "event_picture": {"type": "string", "example": "更新的照片"},

                    },
                    "required": ["event_title", "event_content"],
                },
            },
        ],
        "responses": {
            200: {
                "description": "事件更新成功",
                "schema": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "integer", "example": 1},
                        "event_title": {"type": "string", "example": "更新的生日派對"},
                        "event_content": {"type": "string", "example": "這是一個更新的生日派對內容"},
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-10-08T12:00:00Z",
                        },
                        "updated_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-10-08T12:00:00Z",
                        },
                    },
                },
            },
            404: {
                "description": "事件不存在或不屬於當前用戶",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "事件不存在或不屬於當前用戶"}
                    },
                },
            },
            403: {
                "description": "事件不屬於當前用戶",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "事件不屬於當前用戶"}
                    },
                },
            },
            500: {
                "description": "伺服器內部錯誤",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "更新事件時發生錯誤"}
                    },
                },
            },
        },
    }
)
def update_event(event_id):
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    # 查詢事件是否存在並屬於當前使用者
    event = EventJournalRepository.get_event_by_event_id(event_id)
    if event is None:
        logging.warning(f"Event with ID {event_id} not found.")
        return jsonify(message="事件不存在"), 404

    # 檢查該事件是否屬於當前使用者
    if event.user_id != user.id:
        return jsonify(message="事件不屬於當前用戶"), 403

    # 獲取請求中的更新內容
    data = request.get_json()
    event_title = data.get("event_title")
    event_content = data.get("event_content")
    event_date = data.get("event_date")
    event_picture = data.get("event_picture")

    updated_at = datetime.now(timezone.utc)

    try:
        # 將變更保存到資料庫
        updated_event = EventJournalRepository.update_event(
            event.id, event_title, event_content, updated_at, event_date, event_picture
        )
        collection_name = f"collection_{user.id}"
        collection = chroma.create_collection(collection_name)
        metadata = {"user_id": user.id, "event_title": event_title}
        chroma.update_document(
            collection=collection,
            id=str(event.id),
            document=f"{event_date}:{event_title}是{event_content}",
            metadata=metadata,
        )
        # 構建回應
        updated_event_response = {
            "event_id": updated_event.id,
            "event_title": updated_event.event_title,
            "event_content": updated_event.event_content,
            "created_at": updated_event.created_at.isoformat(),
            "updated_at": updated_event.updated_at.isoformat(),
            "event_date": event.event_date.isoformat(),
            "event_picture": f'{BASE_URL}/userinfo/images/default/{event.event_picture}'
        }

        return jsonify(updated_event_response), 200

    except Exception as e:
        logging.error(f"更新事件時發生錯誤: {str(e)}")
        return jsonify(message="更新事件時發生錯誤", error=str(e)), 500


@event_bp.delete("/delete_event/<int:event_id>")
@jwt_required()
@swag_from(
    {
        "tags": ["EventJournal"],
        "description": """
    此 API 用於刪除特定使用者的事件。

    Steps:
    1. 驗證使用者身份。
    2. 查詢並確認該事件屬於當前使用者。
    3. 從資料庫中刪除事件。
    4. 返回刪除成功的回應。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回成功消息。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
        "parameters": [
            {
                "name": "event_id",
                "in": "path",
                "required": True,
                "type": "integer",
                "description": "要刪除的事件 ID",
                "example": 1,
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
        ],
        "responses": {
            204: {"description": "事件刪除成功"},
            404: {
                "description": "事件不存在或不屬於當前用戶",
                "schema": {
                    "type": "object",
                    "properties": {"message": {"type": "string", "example": "事件不存在"}},
                },
            },
            403: {
                "description": "事件不屬於當前用戶",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "事件不屬於當前用戶"}
                    },
                },
            },
            500: {
                "description": "伺服器內部錯誤",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "刪除事件時發生錯誤"}
                    },
                },
            },
        },
    }
)
def delete_event(event_id):
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    # 查詢事件是否存在並屬於當前使用者
    event = EventJournalRepository.get_event_by_event_id(event_id)
    if event is None:
        return jsonify(message="事件不存在"), 404

    # 檢查該事件是否屬於當前使用者
    if event.user_id != user.id:
        return jsonify(message="事件不屬於當前用戶"), 403

    try:
        # 從資料庫中刪除事件
        EventJournalRepository.delete_event(event_id)

        collection_name = f"collection_{user.id}"
        collection = chroma.create_collection(collection_name)
        chroma.delete_document(collection=collection, id=str(event.id))
        # 返回成功的回應
        return jsonify(message="事件已成功刪除"), 204

    except Exception as e:
        return jsonify(message="刪除事件時發生錯誤", error=str(e)), 500


@event_bp.get("/getevents/<target_year>")
@jwt_required()
@swag_from(
    {
        "tags": ["EventJournal"],
        "description": """
    此 API 用於查詢特定使用者的所有事件列表。

    Steps:
    1. 驗證使用者身份。
    2. 確認所查詢的使用者 ID 是否存在。
    3. 從資料庫查詢與該使用者 ID 關聯的所有事件。
    4. 返回事件列表，包括事件的標題、內容和創建時間。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回事件列表，包括每個事件的詳細資訊。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
        "parameters": [
            {
                "name": "target_year",
                "in": "path",
                "required": True,
                "description": "the target year to get events",
                "schema": {"type": "string", "example": "2023 "},
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
        ],
        "responses": {
            200: {
                "description": "事件列表成功返回",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "integer", "example": 1},
                            "event_title": {"type": "string", "example": "生日派對"},
                            "event_content": {
                                "type": "string",
                                "example": "在家舉辦一個生日派對",
                            },
                            "created_at": {
                                "type": "string",
                                "format": "date-time",
                                "example": "2024-10-08T10:00:00Z",
                            },
                            "updated_at": {
                                "type": "string",
                                "format": "date-time",
                                "example": "2024-10-08T11:00:00Z",
                            },
                        },
                    },
                },
            },
            404: {
                "description": "使用者不存在或未找到事件",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "使用者不存在或沒有事件"}
                    },
                },
            },
            500: {
                "description": "伺服器內部錯誤",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "查詢事件時發生錯誤"}
                    },
                },
            },
        },
    }
)
def get_events_by_year(target_year):
    current_email = get_jwt_identity()

    # 只查詢一次使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    try:
        # 確保 target_year 是一個有效的整數
        try:
            target_year = int(target_year)
        except ValueError:
            return jsonify(message="請提供有效的年份格式"), 400

        # 查詢與該使用者 ID 關聯的所有事件
        events = EventJournalRepository.get_events_by_date(user.id, target_year)

        # 檢查是否有事件
        if not events:
            return jsonify(message="沒有事件存在"), 404

        # 構建事件列表的回應
        event_list = [
            {
                "event_id": event.id,
                "event_title": event.event_title,
                "event_content": event.event_content,
                "created_at": event.created_at.isoformat(),
                "updated_at": event.updated_at.isoformat(),
                "event_date": event.event_date.isoformat(),
                "event_picture": f'{BASE_URL}/userinfo/images/default/{event.event_picture}'
            }
            for event in events
        ]

        return jsonify(event_list), 200

    except Exception as e:
        return jsonify(message="查詢事件時發生錯誤", error=str(e)), 500
