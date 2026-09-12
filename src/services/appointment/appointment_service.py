import math
from src.core.decorators.requireID import require_exists
from src.core.dependencies.context import get_current_tenant_id
from src.core.dependencies.uow import UnitOfWork
from src.core.utils.common import check_branch_belong_to_tenant
from src.exceptions.appointment_exceptions import AppointmentCancelled, AppointmentHasActiveReceipts, AppointmentIsPaid, AppointmentNotFound, ClientAppointmentConflict, EmployeeAppointmentConflict
from src.exceptions.employee_exceptions import EmployeeDoesNotProvideService, EmployeeDoesNotWork, EmployeeInactive, EmployeeIsArchived, EmployeeNotFound
from src.exceptions.general_exceptions import CannotUpdate, ObjectIsArchived, PriceChangedReasonEmpty
from src.exceptions.material_exceptions import MaterialAmountInsufficient, MaterialArchived, MaterialNotFound
from src.exceptions.service_exceptions import ServiceIsArchived, ServiceNotFound
from src.repository.appointment.appointment_model import Appointment, AppointmentCancelledReason, AppointmentStatus
from src.repository.promotion.promotion_model import PromotionType
from src.repository.receipt.receipt_model import Receipt
from src.schemas.analytics.appointmentResponse import ApppointmentAnalyticsResponse
from src.schemas.analytics.request import GetReportWithFilters
from src.schemas.appointment.create import AppointmentCreateSchema
from src.schemas.appointment.update import AppointmentCancelSchema, AppointmentUpdateSchema
from src.schemas.base import RequestAllObject

class AppointmentService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        
    @require_exists("clients", target_param = "client_id")
    async def create(self, data: AppointmentCreateSchema) -> Appointment:
        existing = await self.uow.appointments.client_has_overlap(
            data.client_id, data.start_time_est, data.end_time_est)
        
        if existing: raise ClientAppointmentConflict()

        employee_ids = {record.employee_id for record in (data.records or [])}
        if employee_ids:
            temp = await self.uow.employees.lock_for_update(employee_ids)
            for i in temp:
                if i.id not in employee_ids: raise EmployeeNotFound(i.id)

        price_info: list[list[dict]] = []

        for record in (data.records or []):
            employee = await self.uow.employees.get(record.employee_id)
            if employee is None: raise EmployeeNotFound(record.employee_id)
            if not employee.active: raise EmployeeInactive(employee.id, employee.firstname)
            if employee.archived: raise ObjectIsArchived(employee.id, "employees")

            isWorking = await self.uow.work_schedules.is_employee_working(employee.id, data.start_time_est, data.end_time_est)
            if not isWorking: raise EmployeeDoesNotWork(employee.id, employee.firstname)

            has_conflict = await self.uow.appointmentRecords.employee_has_overlap(
                employee.id, data.start_time_est, data.end_time_est, True
            )
            if has_conflict: raise EmployeeAppointmentConflict(employee.id, employee.firstname)

            employeeAllowedServices = {i.id for i in employee.services}
            record_price_info: list[dict] = []
            for service in record.services:
                info = {"base_price": 0, "final_price": 0, "promotion_id": None}

                if service.service_id:
                    serviceObj = await self.uow.services.get(service.service_id)
                    if serviceObj is None: raise ServiceNotFound(service.service_id)
                    if serviceObj.archived: raise ServiceIsArchived(serviceObj.id, serviceObj.name)
                    if serviceObj.id not in employeeAllowedServices: raise EmployeeDoesNotProvideService(employee.id, employee.firstname, serviceObj.id, serviceObj.name)
                    if (service.price != serviceObj.price and service.price is not None) and (service.price_changed_reason is None or len(service.price_changed_reason.strip()) == 0):
                        raise PriceChangedReasonEmpty()

                    info["base_price"] = serviceObj.price if service.price is None else service.price
                    info["final_price"] = info["base_price"]

                    hasPromotion = await self.uow.promotions.get_by_object(serviceObj.id, "service")
                    if hasPromotion is not None:
                        info["promotion_id"] = hasPromotion.id
                        if hasPromotion.promo_type == PromotionType.FIXED_AMOUNT and hasPromotion.discount_value:
                            discount = info["base_price"] - hasPromotion.discount_value
                            info["final_price"] = discount if discount >= 0 else 0
                        elif hasPromotion.promo_type == PromotionType.PERCENTAGE and hasPromotion.discount_value:
                            discount = info["base_price"] * (hasPromotion.discount_value / 100)
                            info["final_price"] = info["base_price"] - discount

                if service.material_id is not None:
                    materialObj = await self.uow.materials.get(service.material_id)
                    if materialObj is None: raise MaterialNotFound(service.material_id)
                    if materialObj.archived: raise MaterialArchived(materialObj.id, materialObj.name)
                    if service.quantity > materialObj.quantity:
                        raise MaterialAmountInsufficient(materialObj.id, materialObj.name, service.quantity, materialObj.quantity)
                    if (service.price != materialObj.sell_price and service.price is not None) and (service.price_changed_reason is None or len(service.price_changed_reason.strip()) == 0):
                        raise PriceChangedReasonEmpty()

                    info["base_price"] = materialObj.sell_price if service.price is None else service.price
                    info["final_price"] = info["base_price"]

                    hasPromotion = await self.uow.promotions.get_by_object(materialObj.id, "material")
                    if hasPromotion is not None:
                        info["promotion_id"] = hasPromotion.id
                        if hasPromotion.promo_type == PromotionType.FIXED_AMOUNT and hasPromotion.discount_value:
                            discount = info["base_price"] - hasPromotion.discount_value
                            info["final_price"] = discount if discount >= 0 else 0
                        elif hasPromotion.promo_type == PromotionType.PERCENTAGE and hasPromotion.discount_value:
                            discount = info["base_price"] * (hasPromotion.discount_value / 100)
                            info["final_price"] = info["base_price"] - discount

                record_price_info.append(info)
            price_info.append(record_price_info)

        return await self.uow.appointments.create(data, price_info)
    
    async def update(self, data: AppointmentUpdateSchema) -> Appointment:
        checkIfExists = await self.uow.appointments.get(data.id)
        if checkIfExists is None: raise AppointmentNotFound(data.id)

        dataDict = data.model_dump(exclude={"id"}, exclude_unset=True)
        appointment = await self.uow.appointments.get(data.id)
        if not appointment: raise AppointmentNotFound(data.id)
        
        if dataDict.get("archived"):
            receipts = await self.uow.receipts.get_by_appointment(data.id, True)
            if len(receipts) >= 1: raise AppointmentHasActiveReceipts(data.id)
            if appointment.paid: raise AppointmentIsPaid(data.id)
            
        result = await self.uow.appointments.update(data.id, **dataDict)
        if result is None: raise CannotUpdate(data.id, "appointments")
        return result

    async def get(self, id: int) -> Appointment:
        appointment = await self.uow.appointments.get(id)
        if appointment is None: raise AppointmentNotFound(id)
        return appointment
    
    async def get_many(self, ids: list[int]) -> list[Appointment]:
        return await self.uow.appointments.get_by_ids(ids)
    
    async def get_all(self, data: RequestAllObject) -> dict:
        items, total_items = await self.uow.appointments.get_all(data)
        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }
    
    async def cancel(self, data: AppointmentCancelSchema) -> Appointment:
        appointment = await self.uow.appointments.get(data.id)
        if appointment is None: raise AppointmentNotFound(data.id)

        if appointment.status == AppointmentStatus.CANCELLED: raise AppointmentCancelled(data.id)
        
        receipts = await self.uow.receipts.get_by_appointment(data.id, True)
        if len(receipts) >= 1: raise AppointmentHasActiveReceipts(data.id)
        
        if appointment.paid: raise AppointmentIsPaid(data.id)
        
        return await self.uow.appointments.update(data.id, status = AppointmentStatus.CANCELLED, cancelled_reason = data.reason)
    
    @require_exists("appointments")
    async def get_receipts(self, id: int) -> list[Receipt]:
        return await self.uow.receipts.get_by_appointment(id)

    async def get_analytics(self, data: GetReportWithFilters) -> ApppointmentAnalyticsResponse:
        branchID: int
        if data.branch_id is not None:
            await check_branch_belong_to_tenant(self.uow, data.branch_id)
            branchID = data.branch_id
        else: branchID = get_current_tenant_id()

        data.branch_id = branchID
        appointments = await self.uow.appointments.get_analytics(data)
        return ApppointmentAnalyticsResponse(
            amount = appointments.amount or 0,
            finished = appointments.finished or 0,
            cancelled = appointments.cancelled or 0,
            absent = appointments.absent or 0
        )