from flask import (
    Blueprint,
    request,
    jsonify,
)
from flasgger import swag_from
from flask_jwt_extended import get_jwt_identity, jwt_required
from models import shared_model
from repository.shared_model_repo import SharedModelRepo
from repository.trainedmodel_repo import TrainedModelRepo
from repository.trainingfile_repo import TrainingFileRepo
from models.user import User
import json
import os
import logging
import utils.linetxt_to_llama as linetxt_to_llama
from typing import Dict
from sqlalchemy.exc import SQLAlchemyError

utils_bp = Blueprint("utils", __name__)
logger = logging.getLogger(__name__)


FILE_DIRECTORY = "..\\training_file"

# BASE_URL = "http://192.168.1.109:8080" # 安的IP
BASE_URL = "https://nccu-group-8.work"  # 主機IP


def allowed_file(filename, extension):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == extension


def model_to_dict(model, is_shared=False) -> Dict:
    return {
        "model_id": model.id,
        "user_id": model.user_id,
        "modelname": model.modelname,
        "model_original_name": model.model_original_name,
        "modelphoto": f"{BASE_URL}/userinfo/images/{model.user_id}/{model.modelphoto}",
        "anticipation": model.anticipation,
        "is_shared": is_shared,
    }


@utils_bp.post("/user/upload_csv_file")
@jwt_required()
@swag_from(
    {
        "tags": ["Utils"],
        "description": """
        此API 用於上傳或更新 CSV 檔案。

        Input:
        - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
        - user_info: 使用者的資訊，必須是 JSON 格式，其中包含 `model_Id`。
        - file: 要上傳的 CSV 檔案。

        如果同一用戶和模型的檔案已存在且尚未完成訓練，將會覆蓋原有檔案。
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
                "name": "user_info",
                "in": "formData",
                "required": True,
                "description": "User information in JSON format, must include `model_Id`",
                "schema": {"type": "string", "example": '{"model_Id": "1"}'},
            },
            {
                "name": "file",
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "The CSV file to upload",
            },
        ],
        "responses": {
            "200": {
                "description": "File uploaded successfully or updated if a previous file existed and was not trained",
                "examples": {
                    "application/json": {"message": "File uploaded successfully"}
                },
            },
            "400": {
                "description": "Bad request due to missing file, missing `model_Id`, or wrong file type",
                "examples": {
                    "application/json": {
                        "error": "No file part in the request",
                        "error": "No file provided",
                        "error": "model_Id is missing",
                        "error": "File type not allowed. Only CSV files are allowed.",
                    }
                },
            },
            "403": {
                "description": "Forbidden request due to missing user info",
                "examples": {"application/json": {"error": "Forbidden"}},
            },
            "404": {
                "description": "User not found",
                "examples": {"application/json": {"message": "使用者不存在"}},
            },
            "500": {
                "description": "Internal Error due to failure in saving the file",
                "examples": {"application/json": {"error": "Unable to create file."}},
            },
        },
    }
)
def upload_csv_file():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 model_Id
    model_id = user_info.get("model_Id")

    # 確認 model_Id 是否存在
    model_exists = TrainedModelRepo.is_model_id_exists(model_id)
    if not model_exists:
        return jsonify({"error": "Model ID not found in database"}), 404

    # 確認 request 中是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # 確認檔案是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 csv
    if file and allowed_file(file.filename, "csv"):
        # 確認目錄是否存在，若不存在則創建目錄

        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        current_file = TrainingFileRepo.find_first_training_file_by_user_and_model_id(
            user_id=user.id, model_id=model_id
        )

        is_renew = False  # 是否是覆蓋舊的
        # 上傳新的覆蓋舊的，把舊的file實體刪除
        if current_file is not None and (current_file.is_trained is False):
            delete_file_path = os.path.join(FILE_DIRECTORY, current_file.filename)
            os.remove(delete_file_path)
            TrainingFileRepo.delete_training_file_by_file_id(current_file.id)
            is_renew = True
        # 儲存檔案
        saved_file = TrainingFileRepo.create_trainingfile(
            user_id=user.id, model_id=model_id, original_file_name=file.filename
        )
        if saved_file is None:
            return (
                jsonify({"error": "Unable to create file."}),
                500,
            )
        file.save(os.path.join(FILE_DIRECTORY, saved_file.filename))
        if is_renew:
            return jsonify({"message": "File update successfully"}), 200
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only CSV files are allowed."}),
            400,
        )


@utils_bp.post("/user/upload_txt_file")
@jwt_required()
@swag_from(
    {
        "tags": ["Utils"],
        "description": """
    此 API 用於上傳 txt file，然後轉為 csv file 儲存。

    Input:
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
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
                "name": "user_info",
                "in": "formData",
                "description": "JSON string containing user_Id and master_name",
                "required": True,
                "type": "string",
                "schema": {
                    "type": "string",
                    "example": '{"model_Id": "1", "master_name": "John"}',
                },
            },
            {
                "name": "file",
                "in": "formData",
                "description": "TXT file to be uploaded",
                "required": True,
                "type": "file",
            },
        ],
        "responses": {
            200: {
                "description": "File uploaded successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "File uploaded successfully",
                        }
                    },
                },
            },
            400: {
                "description": "Bad request",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "example": "model_Id or master_name is missing",
                        }
                    },
                },
            },
            403: {
                "description": "Forbidden: User info is missing",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string", "example": "Forbidden"}},
                },
            },
            404: {
                "description": "File not found",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "example": "File not found: /path/to/file",
                        }
                    },
                },
            },
            500: {
                "description": "Internal server error",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "example": "File processing error: error message",
                        }
                    },
                },
            },
        },
    }
)
def upload_txt_file():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    user_info = request.form.get("user_info")

    if user_info:
        try:
            user_info = json.loads(user_info)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid user_info format"}), 400
    else:
        return jsonify({"error": "Forbidden"}), 403

    model_id = user_info.get("model_Id")
    master_name = user_info.get("master_name")

    if not master_name or not model_id:
        return jsonify({"error": "master_name or model_id is missing"}), 400

    # 確認 request 中是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files.get("file")

    # 確認檔案是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 txt
    if file and allowed_file(file.filename, "txt"):
        # 確認目錄是否存在，若不存在則創建目錄
        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        # 處理 line chat 的文件
        processor = linetxt_to_llama.LineChatProcessor(
            output_name=user.id, master_name=master_name, data_dir=FILE_DIRECTORY
        )
        try:
            csv_file_name = processor.process(file)  # process 方法需要文件來處理
        except Exception as e:
            return jsonify({"error": f"File processing error: {str(e)}"}), 500

        # 確認是否已有未完成的訓練文件，並刪除
        current_file = TrainingFileRepo.find_first_training_file_by_user_and_model_id(
            user_id=user.id, model_id=model_id
        )
        if current_file is not None and not current_file.is_trained:
            try:
                file_path = os.path.join(FILE_DIRECTORY, current_file.filename)

                if os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    return jsonify({"error": f"File not found: {file_path}"}), 404

                TrainingFileRepo.delete_training_file_by_file_id(current_file.id)
            except OSError as e:
                return jsonify({"error": f"Error deleting old file: {str(e)}"}), 500

        # 儲存檔案
        saved_file = TrainingFileRepo.create_trainingfile(
            user_id=user.id,
            model_id=model_id,
            original_file_name=file.filename,
            filename=csv_file_name,
        )
        if saved_file is None:
            return jsonify({"error": "Unable to create file."}), 500

        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only TXT files are allowed."}),
            400,
        )


@utils_bp.get("/user/model_status/<int:model_Id>")
@jwt_required()
@swag_from(
    {
        "tags": ["Utils"],
        "description": "取得指定使用者和模型的訓練狀態和相關信息。",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "JWT Token to authorize the request",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "model_Id",
                "in": "path",
                "required": True,
                "description": "欲查詢的模型ID",
                "schema": {"type": "integer", "example": 1},
            },
        ],
        "responses": {
            200: {
                "description": "訓練模型狀態資料",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer", "description": "使用者ID"},
                                "training_file_id": {
                                    "type": "integer",
                                    "description": "訓練文件ID",
                                },
                                "filename": {
                                    "type": "string",
                                    "description": "保存的文件名稱",
                                },
                                "original_file_name": {
                                    "type": "string",
                                    "description": "原始上傳文件名",
                                },
                                "start_train": {
                                    "type": "boolean",
                                    "description": "是否開始訓練",
                                },
                                "is_trained": {
                                    "type": "boolean",
                                    "description": "是否訓練完成",
                                },
                                "file_upload_time": {
                                    "type": "string",
                                    "format": "date-time",
                                    "description": "文件上傳時間",
                                },
                                "model_id": {"type": "integer", "description": "模型ID"},
                                "model_name": {"type": "string", "description": "模型名稱"},
                                "model_photo": {
                                    "type": "string",
                                    "description": "模型照片路徑",
                                },
                                "model_anticipation": {
                                    "type": "string",
                                    "description": "模型描述",
                                },
                            },
                        }
                    }
                },
            },
            400: {"description": "模型ID為必填項或格式錯誤"},
            404: {"description": "使用者或模型不存在"},
            500: {"description": "伺服器錯誤，無法取得模型狀態"},
        },
    }
)
def get_model_status(model_Id):
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    model_exists = TrainedModelRepo.is_model_id_exists(model_Id)
    if not model_exists:
        return jsonify({"error": "Model ID not found in database"}), 404

    try:
        # 查詢使用者的第一個已訓練模型
        trained_model_status = TrainedModelRepo.find_trainedmodel_by_user_and_model_id(
            user.id, model_Id
        )
        if not trained_model_status:
            return jsonify({"message": "No trained model found for this user."}), 404

        # 查看是否有照片
        if trained_model_status.modelphoto is None:
            photo_path = "avatar.png"
        else:
            photo_path = trained_model_status.modelphoto
        # 查詢相關的訓練檔案
        training_file_status = (
            TrainingFileRepo.find_first_training_file_by_user_and_model_id(
                user.id, model_Id
            )
        )

        if training_file_status is None:
            return jsonify({"message": "No training files found for this user."}), 404

    except Exception as e:
        logging.error(
            f"Error retrieving training files or trained model for user {user}: {e}"
        )
        return (
            jsonify(
                {
                    "message": "An error occurred while fetching training files or trained model."
                }
            ),
            500,
        )

    return (
        jsonify(
            {
                "user_id": training_file_status.user_id,
                "training_file_id": training_file_status.id,
                "filename": training_file_status.filename,
                "original_file_name": training_file_status.original_file_name,
                "start_train": training_file_status.start_train,
                "is_trained": training_file_status.is_trained,
                "file_upload_time": training_file_status.upload_time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "model_id": trained_model_status.id,
                "model_name": trained_model_status.modelname,
                "model_start_time": (
                    trained_model_status.start_time.strftime("%Y-%m-%d %H:%M:%S")
                    if trained_model_status.start_time is not None
                    else "N/A"
                ),
                "model_end_time": (
                    trained_model_status.end_time.strftime("%Y-%m-%d %H:%M:%S")
                    if trained_model_status.end_time is not None
                    else "N/A"
                ),
                "model_photo": f"{BASE_URL}/userinfo/images/{training_file_status.user_id}/{photo_path}",
                "model_anticipation": trained_model_status.anticipation,
            }
        ),
        200,
    )


@utils_bp.get("/user/all_model_info")
@jwt_required()
@swag_from(
    {
        "tags": ["Utils"],
        "description": "拿到指定使用者的所有模型資訊",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "type": "string",
                "required": True,
                "description": "JWT token to authenticate the request.",
                "schema": {"type": "string", "example": "Bearer "},
            }
        ],
        "responses": {
            200: {
                "description": "Successfully retrieved all model information",
                "content": {
                    "application/json": {
                        "example": [
                            {
                                "id": 1,
                                "user_id": 5,
                                "modelname": "d8ff0712-1ffb-4122-aa01-25b0439ee8c9",
                                "model_original_name": "子安",
                                "modelphoto": "avatar.png",
                                "anticipation": "帥氣的人",
                                "is_shared": False,
                            },
                            {
                                "id": 2,
                                "user_id": 3,
                                "modelname": "9c7c9123-2abc-5678-dcba-34f0123fe8b7",
                                "model_original_name": "致愷",
                                "modelphoto": "avatar2.png",
                                "anticipation": "傻子",
                                "is_shared": True,
                            },
                        ]
                    }
                },
            },
            404: {
                "description": "User does not exist",
                "content": {"application/json": {"example": {"message": "使用者不存在"}}},
            },
            500: {
                "description": "Database error",
                "content": {
                    "application/json": {"example": {"message": "資料庫錯誤，請稍後再試"}}
                },
            },
        },
    }
)
def get_all_model_info():
    current_email = get_jwt_identity()
    user = User.get_user_by_email(current_email)

    if user is None:
        return jsonify(message="使用者不存在"), 404

    try:
        trainedmodels = TrainedModelRepo.find_all_trainedmodel_by_user_id(user.id)
        if not trainedmodels:
            return jsonify(message="此使用者沒有任何訓練的模型"), 200

        sharedmodels = SharedModelRepo.find_sharedmodels_by_acquirer_id(user.id)
        # 取得sharemodel的trainedmodel
        sharedmodels_obj = [
            TrainedModelRepo.find_trainedmodel_by_model_id(model.model_id)
            for model in sharedmodels
        ]
    except SQLAlchemyError:
        return jsonify(message="資料庫錯誤，請稍後再試"), 500

    # Convert to list of dictionaries
    trained_model_data = [model_to_dict(model) for model in trainedmodels]

    shared_model_data = [
        model_to_dict(model, is_shared=True) for model in sharedmodels_obj
    ]
    trained_model_data.extend(shared_model_data)
    return jsonify(trained_model_data), 200
