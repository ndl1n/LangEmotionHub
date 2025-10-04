from typing import Dict, List, Optional

from models.shared_model import SharedModel
from extensions import db
from models.trained_model import TrainedModel


class SharedModelRepo:
    @staticmethod
    def create_shared_model(model: TrainedModel) -> Optional[SharedModel]:
        result = SharedModel(model.id)
        db.session.add(result)
        res = SharedModelRepo.save()
        if res:
            return result
        return None

    @staticmethod
    def save() -> bool:
        try:
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def find_trainedmodel_by_modelname_and_acquirer_id(
        modelname, acquirer_id
    ) -> Optional[TrainedModel]:
        return (
            db.session.query(TrainedModel)
            .join(SharedModel, SharedModel.model_id == TrainedModel.id)
            .filter(
                TrainedModel.modelname == modelname,
                SharedModel.acquirer_id == acquirer_id,
            )
            .first()

        )

    @staticmethod
    def obtain_shared_model(link, acquirer_id) -> Dict:
        res = {"res": False, "msg": ""}
        model: Optional[SharedModel] = SharedModel.query.filter_by(link=link).first()
        if model is None:
            res["msg"] = "找不到模型"
            return res
        # if model 被取走了
        if model.acquirer_id is not None:
            res["msg"] = "連結己被使用"
            return res

        model.acquirer_id = acquirer_id
        if SharedModelRepo.save():
            res["res"] = True
            res["msg"] = "成功取得模型"
        else:
            res["msg"] = "Failed to update acquirer_id"
        return res
    
    @staticmethod
    def find_sharedmodels_by_acquirer_id(acquirer_id) -> list[TrainedModel]:
        return SharedModel.query.filter_by(acquirer_id=acquirer_id).all()

