import os
import mimetypes
from flask import Blueprint, request, jsonify, send_file
from flasgger import swag_from
import logging
import json

from flask_jwt_extended import get_jwt_identity, jwt_required

from repository.trainedmodel_repo import TrainedModelRepo
from repository.trainingfile_repo import TrainingFileRepo
from repository.userphoto_repo import UserPhotoRepo
from models.user import User

userinfo_bp = Blueprint("userinfo", __name__)
logger = logging.getLogger(__name__)

FILE_DIRECTORY = os.path.abspath("..\\user_photo_file")
TRAINING_FILE_DIRECTORY = os.path.abspath("..\\training_file")
# BASE_URL = "http://192.168.1.109:8080" # 安的IP
BASE_URL = "https://nccu-group-8.work"  # 主機IP


def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


@userinfo_bp.post("/user/upload_photo")
@jwt_required()
@swag_from(
    {
        "tags": ["UserInfo"],
        "description": """
    此 API 用於上傳使用者頭貼，支援格式為 JPG, JPEG, PNG。

    Input:
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
    - file: 要上傳的圖像檔案 (JPG, JPEG, PNG)。
    """,
        "consumes": ["multipart/form-data"],
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "file",
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "The image file to upload (JPG, JPEG, PNG)",
            },
        ],
        "responses": {
            200: {
                "description": "File uploaded successfully",
                "examples": {
                    "application/json": {"message": "File uploaded successfully"}
                },
            },
            400: {
                "description": "Bad request due to missing file, wrong file type, or invalid user information",
                "examples": {
                    "application/json": {
                        "error": "No file part in the request",
                        "error": "No file provided",
                        "error": "File type not allowed. Only png, jpg, jpeg files are allowed.",
                    }
                },
            },
            403: {
                "description": "Forbidden request due to missing or invalid user information",
                "examples": {"application/json": {"error": "Forbidden"}},
            },
            404: {
                "description": "User not found",
                "examples": {"application/json": {"error": "User ID not found"}},
            },
            500: {
                "description": "Internal server error occurred while processing the request",
                "examples": {
                    "application/json": {
                        "error": "Unable to create file.",
                        "error": "Internal Server Error",
                    }
                },
            },
        },
    }
)
def upload_photo():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    user_exists = User.is_user_id_exists(user.id)
    if not user_exists:
        return jsonify({"error": "User ID not found"}), 404

    # 檢查是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # 檢查檔案名稱是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 jpg, jpeg, png
    if file and allowed_file(file.filename, ["jpg", "jpeg", "png"]):
        # 檢查並創建檔案目錄
        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        current_file = UserPhotoRepo.find_user_photo_by_user_id(user_id=user.id)

        user_folder = os.path.join(FILE_DIRECTORY, str(user.id))

        # 上傳新的覆蓋舊的，把舊的file實體刪除
        if current_file:
            os.remove(os.path.join(user_folder, current_file.photoname))
            UserPhotoRepo.delete_user_photo_by_user_id(user.id)

        # 儲存檔案
        saved_file = UserPhotoRepo.create_user_photo(
            user_id=user.id, photoname=file.filename
        )
        if not saved_file:
            return (
                jsonify({"error": "Unable to create file."}),
                500,
            )

        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        file.save(os.path.join(user_folder, saved_file.photoname))
        return (
            jsonify(
                {
                    "message": "File uploaded successfully",
                    "user_avatar": f"{BASE_URL}/userinfo/images/{user.id}/{saved_file.photoname}",
                }
            ),
            200,
        )
    else:
        return (
            jsonify(
                {
                    "error": "File type not allowed. Only png, jpg, jpeg files are allowed."
                }
            ),
            400,
        )


# @userinfo_bp.get("/user/get_photo")
# @jwt_required()
# @swag_from(
#     {
#         "tags": ["UserInfo"],
#         "description": """
#     此API用於拿取使用者頭貼，支援格式為 JPG, JPEG, PNG。

#     Input:
#     - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
#     - user_id: 使用者的唯一ID，用來查找並返回對應的頭像。
#     """,
#         "parameters": [
#             {
#                 "name": "Authorization",
#                 "in": "header",
#                 "required": True,
#                 "description": "Bearer token for authorization",
#                 "schema": {"type": "string", "example": "Bearer "},
#             },

#         ],
#         "responses": {
#             200: {
#                 "description": "成功回傳使用者頭像",
#                 "content": {"image/jpeg": {}, "image/png": {}, "image/jpg": {}},
#             },
#             403: {
#                 "description": "禁止請求",
#                 "content": {"application/json": {"example": {"error": "Forbidden"}}},
#             },
#             404: {
#                 "description": "使用者或照片找不到",
#                 "content": {
#                     "application/json": {"example": {"error": "User ID not found"}}
#                 },
#             },
#             500: {
#                 "description": "內部伺服器錯誤",
#                 "content": {
#                     "application/json": {"example": {"error": "Internal Server Error"}}
#                 },
#             },
#         },
#     }
# )
# def get_photo():
#     current_email = get_jwt_identity()

#     # 從資料庫中查詢使用者
#     user_id = User.get_user_by_email(current_email).id
#     if user_id is None:
#         return jsonify(message="使用者不存在"), 404

#     user_info = UserPhotoRepo.find_user_photo_by_user_id(user_id)

#     # 如果使用者頭像是 null，則回傳預設圖片
#     photo_name = "avatar.png"

#     if user_info:
#         photo_name =user_info.photoname

#     # 傳回使用者的圖片檔案
#     return jsonify({"photo": f"{BASE_URL}/userinfo/images/{photo_name}"}), 200


@userinfo_bp.get("/images/<id>/<photoname>")
@swag_from(
    {
        "tags": ["UserInfo"],
        "description": """
        此API 拿取照片。

        Input:
        - photopath: 欲獲取的照片路徑

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
                "name": "photoname",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "User information in JSON format",
            },
        ],
        "responses": {
            "200": {
                "description": "成功回傳使用者頭像",
                "content": {"image/jpeg": {}, "image/png": {}, "image/jpg": {}},
            },
            "400": {
                "description": "Bad request due to missing file or wrong file type",
                "examples": {
                    "application/json": {"error": "Bad request - invalid path"}
                },
            },
            "404": {
                "description": "Image not found",
                "examples": {"application/json": {"error": "Image not found"}},
            },
            "500": {
                "description": "Internal Error",
                "examples": {"application/json": {"error": "Internal Server Error"}},
            },
        },
    }
)
def get_image(id, photoname):
    if id == "default":
        file_path = os.path.join(FILE_DIRECTORY, "default", photoname)
    else:
        file_path = os.path.join(FILE_DIRECTORY, str(id), photoname)

    if not os.path.exists(file_path):
        default_image_path = os.path.join(FILE_DIRECTORY, "default", "avatar.png")
        if os.path.exists(default_image_path):
            return send_file(default_image_path, mimetype="image/png")
        else:
            return jsonify({"error": "User or photo not found"}), 404

    return send_file(file_path, mimetype=mimetypes.guess_type(file_path)[0])


@userinfo_bp.post("/user/create_model")
@jwt_required()
@swag_from(
    {
        "tags": ["UserInfo"],
        "description": """
    此API 用於上傳使用者頭貼，支援格式為 JPG, JPEG, PNG。

    Input:
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
    - user_info: 包含使用者的基本訊息 (例如 user_Id)。
    - file: 要上傳的圖像檔案 (JPG, JPEG, PNG)。
    """,
        "consumes": ["multipart/form-data"],
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "model_original_name",
                "in": "formData",
                "required": True,
                "type": "string",
                "description": "model_original_name",
                "example": "model_original_name",
            },
            {
                "name": "anticipation",
                "in": "formData",
                "required": True,
                "type": "string",
                "description": "anticipation",
                "example": "anticipation",
            },
            {
                "name": "file",
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "The image file to upload (JPG, JPEG, PNG)",
            },
        ],
        "responses": {
            200: {
                "description": "model created successfully",
                "examples": {
                    "application/json": {"message": "model created successfully"}
                },
            },
            400: {
                "description": "Bad request due to missing file, wrong file type, or invalid user information",
                "examples": {
                    "application/json": {
                        "error": "No file part in the request",
                        "error": "File type not allowed. Only png, jpg, jpeg files are allowed.",
                        "error": "Invalid user_info format",
                    }
                },
            },
            403: {
                "description": "Forbidden request due to missing or invalid user information",
                "examples": {"application/json": {"error": "Forbidden"}},
            },
            404: {
                "description": "User ID not found",
                "examples": {"application/json": {"error": "User ID not found"}},
            },
            500: {
                "description": "Internal server error occurred while processing the request",
                "examples": {"application/json": {"error": "Internal Server Error"}},
            },
        },
    }
)
def create_model():
    current_email = get_jwt_identity()
    user_id = User.get_user_by_email(current_email).id

    if user_id is None:
        return jsonify({"error": "User ID not found"}), 404

    model_original_name = request.form.get("model_original_name")
    if model_original_name is None or model_original_name == "":
        return jsonify({"error": "model_original_name is required"}), 400

    anticipation = request.form.get("anticipation")
    if anticipation == "":
        anticipation = None

    # 檢查是否有檔案
    if "file" not in request.files:
        model_photo = None

    else:
        file = request.files["file"]
        # 檢查檔案名稱是否存在
        if file.filename == "":
            return jsonify({"error": "No file provided"}), 400
        model_photo = file.filename
        # 確認檔案類型是否為 jpg, jpeg, png
        if file and allowed_file(file.filename, ["jpg", "jpeg", "png"]):
            # 檢查並創建檔案目錄
            if not os.path.exists(FILE_DIRECTORY):
                os.makedirs(FILE_DIRECTORY)

            user_folder = os.path.join(FILE_DIRECTORY, str(user_id))

            # 儲存檔案
            saved_model = TrainedModelRepo.create_trainedmodel(
                user_id=user_id,
                model_original_name=model_original_name,
                modelphoto=model_photo,
                anticipation=anticipation,
            )
            if not saved_model:
                return (
                    jsonify({"error": "Unable to create file."}),
                    500,
                )

            if not os.path.exists(user_folder):
                os.makedirs(user_folder)

            file.save(os.path.join(user_folder, saved_model.modelphoto))
            return (
                jsonify(
                    {
                        "message": "model created successfully",
                        "model_id": saved_model.id,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "error": "File type not allowed. Only png, jpg, jpeg files are allowed."
                    }
                ),
                400,
            )


@userinfo_bp.delete("/user/delete_model/<int:model_id>")
@jwt_required()
@swag_from(
    {
        "tags": ["UserInfo"],
        "description": "Delete a user’s model and all associated files based on the model ID.",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "model_id",
                "in": "path",
                "type": "integer",
                "required": True,
                "description": "ID of the model to be deleted",
            },
        ],
        "responses": {
            200: {
                "description": "Model and related files deleted successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Model deleted successfully",
                        }
                    },
                },
            },
            404: {
                "description": "User ID or model not found, or model does not belong to the user",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "example": "User ID not found"}
                    },
                },
            },
            500: {
                "description": "Internal server error during deletion",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "example": "An error occurred while deleting the model",
                        }
                    },
                },
            },
        },
    }
)
def delete_model(model_id):
    current_email = get_jwt_identity()
    user = User.get_user_by_email(current_email)

    if user is None:
        return jsonify(message="使用者不存在"), 404

    # 從資料庫中取得指定 model_id 的模型
    model = TrainedModelRepo.find_trainedmodel_by_user_and_model_id(
        user_id=user.id, model_id=model_id
    )

    # 檢查模型是否存在
    if model is None:
        return jsonify({"error": "Model not found or does not belong to the user"}), 404
    try:
        # 刪除該模型的訓練檔案
        model_training_file = (
            TrainingFileRepo.find_first_training_file_by_user_and_model_id(
                user.id, model_id
            )
        )
        if model_training_file is not None:
            file_path = os.path.join(
                TRAINING_FILE_DIRECTORY, model_training_file.filename
            )
            if os.path.exists(file_path):
                os.remove(file_path)
            # delete_trainingfile_success = TrainingFileRepo.delete_training_file_by_user_and_model_id(user_id=user_id, model_id=model_id)
            TrainingFileRepo.delete_training_file_by_file_id(model_training_file.id)

        # 刪除資料庫中的模型記錄
        delete_model_success = (
            TrainedModelRepo.delete_trainedmodel_by_user_and_model_id(
                user_id=user.id, model_id=model_id
            )
        )

        if not delete_model_success:
            return jsonify({"error": "Unable to delete model from database"}), 500

        # 刪除模型照片
        photo_folder = os.path.join(FILE_DIRECTORY, str(user.id))
        file_path = os.path.join(photo_folder, model.modelphoto)
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        print(f"Error deleting model or related files: {e}")
        return jsonify({"error": "An error occurred while deleting the model"}), 500

    return jsonify({"message": "Model deleted successfully"}), 200
