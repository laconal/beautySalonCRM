import math
from typing import Literal

from src.core.decorators.requireID import require_exists
from src.core.dependencies.uow import UnitOfWork
from src.exceptions.general_exceptions import CannotUpdate, ObjectIsArchived
from src.exceptions.material_exceptions import MaterialNotFound
from src.exceptions.promotion_exceptions import PromotionDiscountPercentageExceed, PromotionInactive, PromotionNotFound, PromotionPromoTypeConditionConflict, PromotionTargetConflict
from src.exceptions.service_exceptions import ServiceNotFound
from src.repository.promotion.promotion_model import Promotion, PromotionType
from src.schemas.base import RequestAllObject
from src.schemas.promotion.create import PromotionCreateSchema
from src.schemas.promotion.update import PromotionUpdateSchema

class PromotionService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _unusable_object(self, id: int, table: Literal["services", "materials"]):
        if table == "services":
            service = await self.uow.services.get(id)
            if service is None: raise ServiceNotFound(id)
            if service.archived: raise ObjectIsArchived(id, "services")
        else:
            material = await self.uow.materials.get(id)
            if material is None: raise MaterialNotFound(id)
            if material.archived: raise ObjectIsArchived(id, "materials")

    async def _check_if_using(self, objectID: int, 
                              table: Literal["service", "material"]):
        checkIfUsing = await self.uow.promotions.get_by_object(objectID, table)
        if checkIfUsing is not None and checkIfUsing.is_active:
            raise PromotionTargetConflict(table, objectID, checkIfUsing.id, checkIfUsing.name)

    async def create(self, data: PromotionCreateSchema) -> Promotion:
        await self._unusable_object(
            data.service_id if data.service_id else data.material_id,
            "services" if data.service_id else "materials")

        await self._check_if_using(
            data.service_id if data.service_id else data.material_id,
            "service" if data.service_id else "material")
        
        promotionData = data.model_dump()
        newObject = Promotion(**promotionData)
        return await self.uow.promotions.create(newObject)

    async def update(self, data: PromotionUpdateSchema) -> Promotion:
        promotion = await self.uow.promotions.get(data.id)
        if promotion is None: raise PromotionNotFound(data.id)
        if promotion.archived: raise ObjectIsArchived(data.id, "promotions")

        effective_promo_type = data.promo_type if data.promo_type is not None else promotion.promo_type

        if effective_promo_type == PromotionType.PERCENTAGE and data.discount_value is None:
            if promotion.discount_value > 100 or promotion.discount_value < 0:
                raise PromotionDiscountPercentageExceed(promotion.discount_value)
        if effective_promo_type == PromotionType.PERCENTAGE and data.discount_value is not None and (
            data.discount_value > 100 or data.discount_value < 0
        ):
            raise PromotionDiscountPercentageExceed(data.discount_value)

        await self._unusable_object(
            data.service_id if data.service_id else data.material_id,
            "services" if data.service_id else "materials")
        
        await self._check_if_using(
            data.service_id if data.service_id else data.material_id,
            "service" if data.service_id else "material")
            

        data.promo_type = effective_promo_type
        dataDict = data.model_dump(exclude = {"id"}, exclude_unset = True)
        result = await self.uow.promotions.update(data.id, **dataDict)
        if result is None: raise CannotUpdate(data.id, "promotions")
        return result

    async def get(self, id: int) -> Promotion:
        promotion = await self.uow.promotions.get(id)
        if promotion is None: raise PromotionNotFound(id)
        return promotion

    async def get_all(self, data: RequestAllObject) -> dict:
        items, total_items = await self.uow.promotions.get_all(data)

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }