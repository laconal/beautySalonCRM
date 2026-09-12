import math
from sqlalchemy import select
from sqlalchemy.orm import raiseload
from src.core.dependencies.uow import UnitOfWork
from src.exceptions.appointment_exceptions import AppointmentCancelled, AppointmentHasActiveReceipts, AppointmentIsPaid, AppointmentNotFound, AppointmentRecordNotFound, AppointmentServiceHasToContainOnlyOne, AppointmentServiceNotFound
from src.exceptions.employee_exceptions import EmployeeNotFound, EmployeeDoesNotProvideService
from src.exceptions.general_exceptions import PriceChangedReasonEmpty
from src.exceptions.material_exceptions import MaterialNotFound, MaterialArchived
from src.exceptions.service_exceptions import ServiceIsArchived, ServiceNotFound
from src.repository.appointment.appointment_model import Appointment, AppointmentServices, AppointmentStatus
from src.repository.material.material_model import Material
from src.repository.promotion.promotion_model import PromotionType
from src.repository.receipt.receipt_model import Receipt, ReceiptStatus
from src.repository.service.service_model import Service
from src.schemas.appointment.create import AppointmentServicesCreateSchema
from src.schemas.appointment.update import AppointmentServiceUpdateSchema
from src.schemas.base import RequestAllObject

class AppointmentServicesService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
    
    async def create(self, data: AppointmentServicesCreateSchema) -> Appointment:
        appointmentRecord = await self.uow.appointmentRecords.get(data.appointment_record_id)
        if appointmentRecord is None: raise AppointmentRecordNotFound(data.appointment_record_id)
        appointmentID = appointmentRecord.appointment_id

        material: Material | None = None
        if data.material_id: 
            material = await self.uow.materials.get(data.material_id)
            if material is None: raise MaterialNotFound(data.material_id)
            if material.archived: raise MaterialArchived(material.id, material.name)

        service: Service | None = None
        if data.service_id:
            service = await self.uow.services.get(data.service_id)
            if service is None: raise ServiceNotFound(data.service_id)
            if service.archived: raise ServiceIsArchived(service.id, service.name)

        receipts = await self.uow.db.scalars(
            select(Receipt)
            .options(raiseload("*"))
            .where(Receipt.appointment_id == appointmentRecord.appointment_id)
        )
        if any(receipt.status != ReceiptStatus.CANCELLED for receipt in receipts):
            raise AppointmentHasActiveReceipts(appointmentRecord.appointment_id)

        employee = await self.uow.employees.get(appointmentRecord.employee_id)
        if employee is None: raise EmployeeNotFound(appointmentRecord.employee_id)

        info = {"base_price": 0, "final_price": 0, "promotion_id": None}

        if service is not None:
            employeeAllowedServices = {i.id for i in employee.services}
            if data.service_id not in employeeAllowedServices:
                raise EmployeeDoesNotProvideService(employee.id, employee.firstname, service.id, service.name)
            if data.price is None: data.price = service.price
            if data.price != service.price and (data.price_changed_reason is None or len(data.price_changed_reason.strip()) == 0):
                raise PriceChangedReasonEmpty()

            info["base_price"] = data.price
            info["final_price"] = data.price

            hasPromotion = await self.uow.promotions.get_by_object(service.id, "service")
            if hasPromotion is not None:
                info["promotion_id"] = hasPromotion.id
                if hasPromotion.promo_type == PromotionType.FIXED_AMOUNT and hasPromotion.discount_value:
                    discount = info["base_price"] - hasPromotion.discount_value
                    info["final_price"] = discount if discount >= 0 else 0
                elif hasPromotion.promo_type == PromotionType.PERCENTAGE and hasPromotion.discount_value:
                    discount = info["base_price"] * (hasPromotion.discount_value / 100)
                    info["final_price"] = info["base_price"] - discount

        if material is not None:
            if data.price is None: data.price = material.sell_price
            if data.price != material.sell_price and (data.price_changed_reason is None or len(data.price_changed_reason.strip()) == 0):
                raise PriceChangedReasonEmpty()

            info["base_price"] = data.price
            info["final_price"] = data.price

            hasPromotion = await self.uow.promotions.get_by_object(material.id, "material")
            if hasPromotion is not None:
                info["promotion_id"] = hasPromotion.id
                if hasPromotion.promo_type == PromotionType.FIXED_AMOUNT and hasPromotion.discount_value:
                    discount = info["base_price"] - hasPromotion.discount_value
                    info["final_price"] = discount if discount >= 0 else 0
                elif hasPromotion.promo_type == PromotionType.PERCENTAGE and hasPromotion.discount_value:
                    discount = info["base_price"] * (hasPromotion.discount_value / 100)
                    info["final_price"] = info["base_price"] - discount

        newObject = AppointmentServices(
            appointment_record_id = data.appointment_record_id,
            service_id = data.service_id,
            material_id = data.material_id,
            quantity = data.quantity,
            base_price = info["base_price"],
            final_price = info["final_price"],
            promotion_id = info["promotion_id"],
            price_changed_reason = data.price_changed_reason,
            notes = data.notes
        )
        await self.uow.appointmentServices.create(newObject)
        return await self.uow.appointments.get(appointmentID)
    
    async def update(self, data: AppointmentServiceUpdateSchema) -> Appointment:
        appointmentService = await self.uow.appointmentServices.get(data.id)
        if appointmentService is None: raise AppointmentRecordNotFound(data.id)

        if (appointmentService.service_id and data.material_id) or (appointmentService.material_id and data.service_id): 
            raise AppointmentServiceHasToContainOnlyOne()
        
        appointmentRecord = appointmentService.appointment_record
        appointmentID = appointmentRecord.appointment_id

        appointment = await self.uow.appointments.get(appointmentID)
        if appointment is None: raise AppointmentNotFound(appointmentID)
        if appointment.paid: raise AppointmentIsPaid(appointmentID)
        if appointment.status == AppointmentStatus.CANCELLED: raise AppointmentCancelled(appointmentID)

        receipts = await self.uow.db.scalars(
            select(Receipt)
            .options(raiseload("*"))
            .where(Receipt.appointment_id == appointmentID)
        )
        if any(receipt.status != ReceiptStatus.CANCELLED for receipt in receipts):
            raise AppointmentHasActiveReceipts(appointment.id)
        
        material: Material | None = None
        if data.material_id:
            material = await self.uow.materials.get(data.material_id)
            if material is None: raise MaterialNotFound(data.material_id)
            if material.archived: raise MaterialArchived(material.id, material.name)
        elif appointmentService.material_id and data.price is not None:
            material = await self.uow.materials.get(appointmentService.material_id)

        service: Service | None = None
        if data.service_id:
            service = await self.uow.services.get(data.service_id)
            if service is None: raise ServiceNotFound(data.service_id)
            if service.archived: raise ServiceIsArchived(service.id, service.name)
        elif appointmentService.service_id and data.price is not None:
            service = await self.uow.services.get(appointmentService.service_id)

        employee = await self.uow.employees.get(appointmentRecord.employee_id)
        if not employee: raise EmployeeNotFound(appointmentRecord.employee_id)

        info = {"base_price": 0, "final_price": 0, "promotion_id": None}

        if service is not None:
            if data.service_id:
                employeeAllowedServices = {i.id for i in employee.services}
                if data.service_id not in employeeAllowedServices:
                    raise EmployeeDoesNotProvideService(employee.id, employee.firstname, service.id, service.name)
            if data.price is None: data.price = service.price
            if data.price != service.price and (data.price_changed_reason is None or len(data.price_changed_reason.strip()) == 0):
                raise PriceChangedReasonEmpty()

            info["base_price"] = data.price
            info["final_price"] = data.price

            hasPromotion = await self.uow.promotions.get_by_object(service.id, "service")
            if hasPromotion is not None:
                info["promotion_id"] = hasPromotion.id
                if hasPromotion.promo_type == PromotionType.FIXED_AMOUNT and hasPromotion.discount_value:
                    discount = info["base_price"] - hasPromotion.discount_value
                    info["final_price"] = discount if discount >= 0 else 0
                elif hasPromotion.promo_type == PromotionType.PERCENTAGE and hasPromotion.discount_value:
                    discount = info["base_price"] * (hasPromotion.discount_value / 100)
                    info["final_price"] = info["base_price"] - discount

        if material is not None:
            if data.price is None: data.price = material.sell_price
            if data.price != material.sell_price and (data.price_changed_reason is None or len(data.price_changed_reason.strip()) == 0):
                raise PriceChangedReasonEmpty()

            info["base_price"] = data.price
            info["final_price"] = data.price

            hasPromotion = await self.uow.promotions.get_by_object(material.id, "material")
            if hasPromotion is not None:
                info["promotion_id"] = hasPromotion.id
                if hasPromotion.promo_type == PromotionType.FIXED_AMOUNT and hasPromotion.discount_value:
                    discount = info["base_price"] - hasPromotion.discount_value
                    info["final_price"] = discount if discount >= 0 else 0
                elif hasPromotion.promo_type == PromotionType.PERCENTAGE and hasPromotion.discount_value:
                    discount = info["base_price"] * (hasPromotion.discount_value / 100)
                    info["final_price"] = info["base_price"] - discount

        dataDict = data.model_dump(exclude={"id", "price"}, exclude_unset=True)
        if service is not None or material is not None:
            dataDict["base_price"] = info["base_price"]
            dataDict["final_price"] = info["final_price"]
            dataDict["promotion_id"] = info["promotion_id"]

        await self.uow.appointmentServices.update(data.id, **dataDict)
        return await self.uow.appointments.get(appointmentRecord.appointment_id)
    
    async def get(self, id: int) -> AppointmentServices:
        result = await self.uow.appointmentServices.get(id)
        if result is None: raise AppointmentServiceNotFound(id)
        return result
    
    async def get_many(self, ids: list[int]) -> list[AppointmentServices]:
        return await self.uow.appointmentsServices.get_by_ids(ids)
    
    async def get_all(self, data: RequestAllObject) -> dict:
        items, total_items = await self.uow.appointmentsServices.get_all(data)

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }
    
    async def delete(self, id: int) -> Appointment:
        appointmentService = await self.uow.appointmentServices.get(id)
        if appointmentService is None: raise AppointmentServiceNotFound(id)

        appointmentID = appointmentService.appointment_record.appointment_id
        appointment = await self.uow.appointments.get(appointmentID)
        if appointment is None: raise AppointmentNotFound(appointmentID)
        if appointment.paid: raise AppointmentIsPaid(appointmentID)
        if appointment.status == AppointmentStatus.CANCELLED: raise AppointmentCancelled(appointmentID)

        receipts = await self.uow.db.scalars(
            select(Receipt)
            .options(raiseload("*"))
            .where(Receipt.appointment_id == appointmentID)
        )
        if any(receipt.status != ReceiptStatus.CANCELLED for receipt in receipts):
            raise AppointmentHasActiveReceipts(appointmentID)

        
        await self.uow.appointmentServices.delete(id)
        return await self.uow.appointments.get(appointmentID)