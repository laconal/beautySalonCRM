from fastapi import Depends
from src.database.session import get_repository_db, transaction_scope
from src.repository.appointment.appointmentRecords_repository import AppointmentRecordsRepository
from src.repository.appointment.appointment_repository import AppointmentRepository
from src.repository.appointment.appointmentServices_repository import AppointmentServicesRepository
from src.repository.audit.auditLog_repository import AuditLogsRepository
from src.repository.client.client_repository import ClientRepository
from src.repository.employee.absence_repository import EmployeeAbsenceRepository
from src.repository.employee.employee_repository import EmployeeRepository
from src.repository.employee.specialization_repository import SpecializationRepository
from src.repository.employee.workSchedule_repository import WorkScheduleRepository
from src.repository.giftCard.giftCard_repository import GiftCardRepository
from src.repository.material.material_repository import MaterialRepository
from src.repository.service.serviceCategory_repository import ServiceCategoryRepository
from src.repository.service.service_repository import ServiceRepository
from src.repository.staff.role_repository import RoleRepository
from src.repository.staff.staff_repository import StaffRepository
from src.repository.payroll.payroll_repository import PayrollRepository
from src.repository.payroll.payout_repository import PayoutRepository
from src.repository.receipt.receipt_repository import ReceiptRepository
from src.repository.tenant.tenantIntergrations_repository import TenantIntegrationsRepository
from src.repository.tenant.tenant_repository import TenantRepository
from src.repository.transaction.transaction_repository import TransactionRepository
from src.repository.notification.notification_repository import NotificationRepository
from src.repository.promotion.promotion_repository import PromotionRepository
from typing import AsyncGenerator, TypeVar, Type, Callable
from src.repository.staff.staffAuthAttempts_repository import StaffAuthAttemptsRepository

T = TypeVar("T")

class UnitOfWork:
    def __init__(self):
        self.staffs = StaffRepository()
        self.staffAuthAttempts = StaffAuthAttemptsRepository()
        self.auditLogs = AuditLogsRepository()

        self.employees = EmployeeRepository()
        self.serviceCategory = ServiceCategoryRepository()
        self.services = ServiceRepository()
        self.specializations = SpecializationRepository()
        self.work_schedules = WorkScheduleRepository()
        self.absences = EmployeeAbsenceRepository()
        self.clients = ClientRepository()
        self.materials = MaterialRepository()
        self.roles = RoleRepository()

        self.appointments = AppointmentRepository()
        self.appointmentRecords = AppointmentRecordsRepository()
        self.appointmentServices = AppointmentServicesRepository()

        self.payrolls = PayrollRepository()
        self.payouts = PayoutRepository()
        self.receipts = ReceiptRepository()
        self.transactions = TransactionRepository()
        self.promotions = PromotionRepository()
        self.giftCards = GiftCardRepository()
        
        self.notifications = NotificationRepository()

        self.tenants = TenantRepository()
        self.tenantIntegrations = TenantIntegrationsRepository()
    @property
    def db(self):
        return get_repository_db()

async def get_uow_with_context():
    """Single dependency that provides both session context AND uow."""
    yield UnitOfWork()

async def get_request_uow() -> AsyncGenerator[UnitOfWork, None]:
    """
    Single per-request UnitOfWork/transaction, shared by every dependency that
    depends on this exact callable (FastAPI caches it within the request) -
    e.g. permission checks and the endpoint's service both see the same session.
    """
    async with transaction_scope():
        yield UnitOfWork()

T = TypeVar("T")

def make_service_dependency(service_cls: Type[T]) -> Callable[..., AsyncGenerator[T, None]]:
    async def dependency(uow: UnitOfWork = Depends(get_request_uow)) -> AsyncGenerator[T, None]:
        yield service_cls(uow=uow)

    return dependency
