from __future__ import annotations
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.repository.staff.staff_model import Staff

class PermissionCode(IntEnum):
    MATERIAL_CREATE = 1001
    MATERIAL_UPDATE = 1002
    MATERIAL_READ = 1003
    MATERIAL_UPDATE_QUANTITY = 1004
    MATERIAL_MANAGE = 1999

    APPOINTMENT_CREATE = 2001
    APPOINTMENT_UPDATE = 2002
    APPOINTMENT_READ = 2003
    APPOINTMENT_CANCEL = 2004
    APPOINTMENT_MANAGE = 2005
    APPOINTMENT_RECORDS_CREATE = 2011
    APPOINTMENT_RECORDS_DELETE = 2012
    APPOINTMENT_RECORDS_MANAGE = 2013
    APPOINTMENT_SERVICES_CREATE = 2021
    APPOINTMENT_SERVICES_UPDATE = 2022
    APPOINTMENT_SERVICES_DELETE = 2023
    APPOINTMENT_SERVICES_MANAGE = 2999

    CLIENT_CREATE = 3001
    CLIENT_UPDATE = 3002
    CLIENT_READ = 3003
    CLIENT_UPDATE_DEPOSIT = 3004
    CLIENT_FINANCE_REPORT = 3005
    CLIENT_MANAGE = 3006
    SEGMENTATION_CREATE = 3999

    EMPLOYEE_CREATE = 4001
    EMPLOYEE_UPDATE = 4002
    EMPLOYEE_READ = 4003
    EMPLOYEE_EXPORT = 4004
    EMPLOYEE_MANAGE = 4999

    SERVICE_CREATE = 5001
    SERVICE_UPDATE = 5002
    SERVICE_READ = 5003
    SERVICE_IMPORT = 5004
    SERVICE_MANAGE = 5005
    SERVICE_CATEGORY_CREATE = 5011
    SERVICE_CATEGORY_UPDATE = 5012
    SERVICE_CATEGORY_READ = 5013
    SERVICE_CATEGORY_MANAGE = 5999

    SPECIALIZATION_CREATE = 6001
    SPECIALIZATION_UPDATE = 6002
    SPECIALIZATION_READ = 6003
    SPECIALIZATION_DELETE = 6004
    SPECIALIZATION_MANAGE = 6999

    WORK_SCHEDULE_CREATE = 7001
    WORK_SCHEDULE_UPDATE = 7002
    WORK_SCHEDULE_READ = 7003
    WORK_SCHEDULE_DELETE = 7004
    WORK_SCHEDULE_MANAGE = 7005
    ABSENCE_CREATE = 7011
    ABSENCE_UPDATE = 7012
    ABSENCE_READ = 7013
    ABSENCE_DELETE = 7014
    ABSENCE_MANAGE = 7999

    PAYROLL_CREATE = 8001
    PAYROLL_UPDATE = 8002
    PAYROLL_READ = 8003
    PAYROLL_DELETE = 8004
    PAYROLL_CANCEL = 8005
    PAYROLL_MANAGE = 8006
    PAYOUT_CREATE = 8011
    PAYOUT_READ = 8012
    PAYOUT_MANAGE = 8999

    RECEIPT_CREATE = 9001
    RECEIPT_READ = 9002
    RECEIPT_MAKE_PAYMENT = 9003
    RECEIPT_CANCEL = 9004
    RECEIPT_MANAGE = 9005
    TRANSACTION_CREATE = 9011
    TRANSACTION_READ = 9012
    TRANSACTION_CANCEL = 9013
    TRANSACTION_MANAGE = 9999

    NOTIFICATION_CREATE = 10001
    NOTIFICATION_READ = 10002
    NOTIFICATION_ARCHIVE = 10003
    NOTIFICATION_CANCEL = 10004
    NOTIFICATION_MANAGE = 10999

    AUDIT_LOGS_READ = 11001

    TENANT_INTEGRATIONS_READ = 12001
    TENANT_PREFERENCES_READ = 12002
    TENANT_PREFERENCES_UPDATE = 12003
    TENANT_GET_REPORT = 12004
    TENANT_MANAGE = 12005

    TENANT_BRANCH_CREATE = 12011
    TENANT_BRANCH_READ = 12012
    TENANT_BRANCH_UDPATE = 12013
    TENANT_BRANCH_CREATE_ADMIN = 12014
    TENANT_BRANCH_UPDATE_ADMIN = 12015
    TENANT_BRANCH_RESET_ADMIN_PASSWORD = 12016
    TENANT_BRANCH_GET_REPORT = 12017
    TENANT_BRANCH_MANAGE = 12999

    PROMOTION_CREATE = 13001
    PROMOTION_GET = 13002
    PROMOTION_UPDATE = 13003
    PROMOTION_MANAGE = 13999

    GIFT_CARD_CREATE = 14001
    GIFT_CARD_UPDATE = 14002
    GIFT_CARD_GET = 14003
    GIFT_CARD_MANAGE = 14999

    ANALYTICS_EMPLOYEE = 20000
    ANALYTICS_SERVICE = 20100
    ANALYTICS_RECEIPT = 20200
    ANALYTICS_APPOINTMENT = 20300
    ANALYTICS_TRANSACTION = 20400
    ANALYTICS_MANAGE = 29999

PERMISSIONS: dict[int, dict[str, str]] = {
    PermissionCode.ANALYTICS_APPOINTMENT: {"resource": "analytics_appointment", "name": "Appointment analytics"},
    PermissionCode.ANALYTICS_EMPLOYEE: {"resource": "analytics_employee", "name": "Employee analytics"},
    PermissionCode.ANALYTICS_SERVICE: {"resource": "analytics_service", "name": "Service analytics"},
    PermissionCode.ANALYTICS_RECEIPT: {"resource": "analytics_receipt", "name": "Receipt analytics"},
    PermissionCode.ANALYTICS_TRANSACTION: {"resource": "analytics_transaction", "name": "Transaction analytics"},

    PermissionCode.MATERIAL_CREATE: {"resource": "material", "name": "Create material"},
    PermissionCode.MATERIAL_UPDATE: {"resource": "material", "name": "Update material"},
    PermissionCode.MATERIAL_READ: {"resource": "material", "name": "View material"},
    PermissionCode.MATERIAL_UPDATE_QUANTITY: {"resource": "material", "name": "Update material quantity"},
    PermissionCode.MATERIAL_MANAGE: {"resource": "material", "name": "Full access to materials"},

    PermissionCode.APPOINTMENT_CREATE: {"resource": "appointment", "name": "Create appointment"},
    PermissionCode.APPOINTMENT_UPDATE: {"resource": "appointment", "name": "Update appointment"},
    PermissionCode.APPOINTMENT_READ: {"resource": "appointment", "name": "View appointment"},
    PermissionCode.APPOINTMENT_CANCEL: {"resource": "appointment", "name": "Cancel appointment"},
    PermissionCode.APPOINTMENT_MANAGE: {"resource": "appointment", "name": "Full access to appointments"},
    PermissionCode.APPOINTMENT_RECORDS_CREATE: {"resource": "record within appointment", "name": "Create record within appointment"},
    PermissionCode.APPOINTMENT_RECORDS_DELETE: {"resource": "record within appointment", "name": "Delete record within appointment"},
    PermissionCode.APPOINTMENT_RECORDS_MANAGE: {"resource": "record within appointment", "name": "Full access to records within appointment"},
    PermissionCode.APPOINTMENT_SERVICES_CREATE: {"resource": "service in record", "name": "Add service to record"},
    PermissionCode.APPOINTMENT_SERVICES_UPDATE: {"resource": "service in record", "name": "Update service in record"},
    PermissionCode.APPOINTMENT_SERVICES_DELETE: {"resource": "service in record", "name": "Remove service from record"},
    PermissionCode.APPOINTMENT_SERVICES_MANAGE: {"resource": "service in record", "name": "Full access to services in record"},

    PermissionCode.CLIENT_CREATE: {"resource": "client", "name": "Create client"},
    PermissionCode.CLIENT_UPDATE: {"resource": "client", "name": "Update client"},
    PermissionCode.CLIENT_READ: {"resource": "client", "name": "View client"},
    PermissionCode.CLIENT_UPDATE_DEPOSIT: {"resource": "client", "name": "Update client deposit"},
    PermissionCode.CLIENT_FINANCE_REPORT: {"resource": "client", "name": "View client financial report"},
    PermissionCode.SEGMENTATION_CREATE: {"resource": "segmentation", "name": "Create segmentation"},
    PermissionCode.CLIENT_MANAGE: {"resource": "client", "name": "Full access to clients"},

    PermissionCode.EMPLOYEE_CREATE: {"resource": "employee", "name": "Create employee"},
    PermissionCode.EMPLOYEE_UPDATE: {"resource": "employee", "name": "Update employee"},
    PermissionCode.EMPLOYEE_READ: {"resource": "employee", "name": "View employee"},
    PermissionCode.EMPLOYEE_EXPOR: {"resource": "employee", "name": "Export employee"},
    PermissionCode.EMPLOYEE_MANAGE: {"resource": "employee", "name": "Full access to employees"},

    PermissionCode.SERVICE_CREATE: {"resource": "service", "name": "Create service"},
    PermissionCode.SERVICE_UPDATE: {"resource": "service", "name": "Update service"},
    PermissionCode.SERVICE_READ: {"resource": "service", "name": "View service"},
    PermissionCode.SERVICE_IMPORT: {"resource": "service", "name": "Import services from Excel"},
    PermissionCode.SERVICE_MANAGE: {"resource": "service", "name": "Full access to services"},
    PermissionCode.SERVICE_CATEGORY_CREATE: {"resource": "service category", "name": "Create service category"},
    PermissionCode.SERVICE_CATEGORY_UPDATE: {"resource": "service category", "name": "Update service category"},
    PermissionCode.SERVICE_CATEGORY_READ: {"resource": "service category", "name": "View service category"},
    PermissionCode.SERVICE_CATEGORY_MANAGE: {"resource": "service category", "name": "Full access to service categories"},

    PermissionCode.PROMOTION_CREATE: {"resource": "promotion", "name": "Create promotion"},
    PermissionCode.PROMOTION_GET: {"resource": "promotion", "name": "Get promotion(s)"},
    PermissionCode.PROMOTION_UPDATE: {"resource": "promotion", "name": "Update promotion"},
    PermissionCode.PROMOTION_MANAGE: {"resource": "promotion", "name": "Manage promotions"},

    PermissionCode.GIFT_CARD_CREATE: {"resource": "gift_cards", "name": "Create gift card"},
    PermissionCode.GIFT_CARD_UPDATE: {"resource": "gift_cards", "name": "Update gift card"},
    PermissionCode.GIFT_CARD_GET: {"resource": "gift_cards", "name": "Get gift card"},
    PermissionCode.GIFT_CARD_MANAGE: {"resource": "gift_cards", "name": "Manage gift cards"},

    PermissionCode.SPECIALIZATION_CREATE: {"resource": "specialization", "name": "Create specialization"},
    PermissionCode.SPECIALIZATION_UPDATE: {"resource": "specialization", "name": "Update specialization"},
    PermissionCode.SPECIALIZATION_READ: {"resource": "specialization", "name": "View specialization"},
    PermissionCode.SPECIALIZATION_DELETE: {"resource": "specialization", "name": "Delete specialization"},
    PermissionCode.SPECIALIZATION_MANAGE: {"resource": "specialization", "name": "Full access to specializations"},

    PermissionCode.WORK_SCHEDULE_CREATE: {"resource": "work schedule", "name": "Create work schedule"},
    PermissionCode.WORK_SCHEDULE_UPDATE: {"resource": "work schedule", "name": "Update work schedule"},
    PermissionCode.WORK_SCHEDULE_READ: {"resource": "work schedule", "name": "View work schedule"},
    PermissionCode.WORK_SCHEDULE_DELETE: {"resource": "work schedule", "name": "Delete work schedule"},
    PermissionCode.WORK_SCHEDULE_MANAGE: {"resource": "work schedule", "name": "Full access to work schedules"},
    PermissionCode.ABSENCE_CREATE: {"resource": "absence", "name": "Create absence"},
    PermissionCode.ABSENCE_UPDATE: {"resource": "absence", "name": "Update absence"},
    PermissionCode.ABSENCE_READ: {"resource": "absence", "name": "View absence"},
    PermissionCode.ABSENCE_DELETE: {"resource": "absence", "name": "Delete absence"},
    PermissionCode.ABSENCE_MANAGE: {"resource": "absence", "name": "Full access to absences"},

    PermissionCode.PAYROLL_CREATE: {"resource": "payroll", "name": "Create payroll"},
    PermissionCode.PAYROLL_UPDATE: {"resource": "payroll", "name": "Update payroll"},
    PermissionCode.PAYROLL_READ: {"resource": "payroll", "name": "View payroll"},
    PermissionCode.PAYROLL_DELETE: {"resource": "payroll", "name": "Delete payroll"},
    PermissionCode.PAYROLL_CANCEL: {"resource": "payroll", "name": "Cancel payroll"},
    PermissionCode.PAYROLL_MANAGE: {"resource": "payroll", "name": "Full access to payroll"},
    PermissionCode.PAYOUT_CREATE: {"resource": "payout", "name": "Create payout"},
    PermissionCode.PAYOUT_READ: {"resource": "payout", "name": "View payout"},
    PermissionCode.PAYOUT_MANAGE: {"resource": "payout", "name": "Full access to payouts"},

    PermissionCode.RECEIPT_CREATE: {"resource": "receipt", "name": "Create receipt"},
    PermissionCode.RECEIPT_READ: {"resource": "receipt", "name": "View receipt"},
    PermissionCode.RECEIPT_MAKE_PAYMENT: {"resource": "receipt", "name": "Make payment on receipt"},
    PermissionCode.RECEIPT_CANCEL: {"resource": "receipt", "name": "Cancel receipt"},
    PermissionCode.RECEIPT_MANAGE: {"resource": "receipt", "name": "Full access to receipts"},
    PermissionCode.TRANSACTION_CREATE: {"resource": "transaction", "name": "Create transaction"},
    PermissionCode.TRANSACTION_READ: {"resource": "transaction", "name": "View transaction"},
    PermissionCode.TRANSACTION_CANCEL: {"resource": "transaction", "name": "Cancel transaction"},
    PermissionCode.TRANSACTION_MANAGE: {"resource": "transaction", "name": "Full access to transactions"},

    PermissionCode.NOTIFICATION_CREATE: {"resource": "notification", "name": "Create notification"},
    PermissionCode.NOTIFICATION_READ: {"resource": "notification", "name": "View notification"},
    PermissionCode.NOTIFICATION_ARCHIVE: {"resource": "notification", "name": "Archive notification"},
    PermissionCode.NOTIFICATION_MANAGE: {"resource": "notification", "name": "Full access to notifications"},

    PermissionCode.AUDIT_LOGS_READ: {"resource": "audit log", "name": "View audit log"},

    PermissionCode.TENANT_INTEGRATIONS_READ: {"resource": "organization integrations", "name": "View organization integrations"},
    PermissionCode.TENANT_PREFERENCES_READ: {"resource": "organization settings", "name": "View organization settings"},
    PermissionCode.TENANT_PREFERENCES_UPDATE: {"resource": "organization settings", "name": "Update organization settings"},
    PermissionCode.TENANT_GET_REPORT: {"resource": "organization settings", "name": "Access to reports"},
    PermissionCode.TENANT_MANAGE: {"resource": "organization settings", "name": "Full access to organization settings / integrations"},

    PermissionCode.TENANT_BRANCH_CREATE: {"resource": "organization branch", "name": "Create branch organization"},
    PermissionCode.TENANT_BRANCH_READ: {"resource": "organization branch", "name": "View branch organizations"},
    PermissionCode.TENANT_BRANCH_UDPATE: {"resource": "organization branch", "name": "Update branch"},
    PermissionCode.TENANT_BRANCH_CREATE_ADMIN: {"resource": "organization branch", "name": "Create branch's admin"},
    PermissionCode.TENANT_BRANCH_UPDATE_ADMIN: {"resource": "organization branch", "name": "Update branch's admin info"},
    PermissionCode.TENANT_BRANCH_RESET_ADMIN_PASSWORD: {"resource": "organization branch", "name": "Reset branch's admin password"},
    PermissionCode.TENANT_BRANCH_GET_REPORT: {"resource": "organization branch", "name": "Report access to self and branches' reports"},
    PermissionCode.TENANT_BRANCH_MANAGE: {"resource": "organization branch", "name": "Full access to branch organizations"},
}

def compute_effective_permissions(staff: "Staff") -> list[int]:
    """Union of a staff's direct permission overrides and every role they hold. Assumes staff.roles is already loaded."""
    effective = set(staff.permissions or [])
    for role in staff.roles:
        effective.update(role.permissions or [])
    return sorted(effective)

def _build_domain_manage_map() -> dict[PermissionCode, PermissionCode]:
    """Maps each non-MANAGE code to the *_MANAGE code of its domain, matched by longest
    common name prefix (e.g. APPOINTMENT_RECORDS_CREATE -> APPOINTMENT_RECORDS_MANAGE,
    not the broader APPOINTMENT_MANAGE). Codes with no matching *_MANAGE sibling are omitted."""
    manage_codes = [code for code in PermissionCode if code.name.endswith("_MANAGE")]
    domain_map: dict[PermissionCode, PermissionCode] = {}

    for code in PermissionCode:
        if code in manage_codes:
            continue

        code_parts = code.name.split("_")
        best_match: PermissionCode | None = None
        best_match_len = 0

        for manage_code in manage_codes:
            manage_parts = manage_code.name.removesuffix("_MANAGE").split("_")
            if len(manage_parts) > best_match_len and code_parts[:len(manage_parts)] == manage_parts:
                best_match = manage_code
                best_match_len = len(manage_parts)

        if best_match is not None:
            domain_map[code] = best_match

    return domain_map

PERMISSION_DOMAIN_MANAGE: dict[PermissionCode, PermissionCode] = _build_domain_manage_map()