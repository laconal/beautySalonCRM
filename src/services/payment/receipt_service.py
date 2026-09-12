import math
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from src.core.dependencies.context import get_current_tenant_id
from src.core.dependencies.uow import UnitOfWork
from src.exceptions.appointment_exceptions import AppointmentCancelled, AppointmentHasActiveReceipts, AppointmentIsPaid, AppointmentNotFound
from src.exceptions.base import BaseAppException
from src.exceptions.client_exceptions import ClientNotFound, DepositNotEnough
from src.exceptions.employee_exceptions import EmployeeNotFound
from src.exceptions.general_exceptions import ObjectIsArchived, PaymentCancelDueExpired
from src.exceptions.giftCard_exceptions import GiftCardClientConflict, GiftCardInsufficientAmount, GiftCardNotFound, GiftCardUnusable
from src.exceptions.material_exceptions import MaterialAmountInsufficient, MaterialNotFound
from src.exceptions.receipt_exceptions import ReceiptHasNotClient, ReceiptIsCancelled, ReceiptIsPaid, ReceiptNotFound, ReceiptWithEmptyAppointmentRecords
from src.repository.appointment.appointment_model import AppointmentServices, AppointmentStatus
from src.repository.client.client_model import Client
from src.repository.giftCard.giftCard_model import GiftCardStatus
from src.repository.promotion.promotion_model import PromotionType
from src.repository.receipt.receipt_model import Receipt, ReceiptItem, ReceiptStatus, ReceiptType
from src.repository.payroll.payroll_model import Payroll, PayrollStatus, PayrollType
from src.repository.transaction.transaction_model import Transaction, TransactionCategory, TransactionMethod, TransactionType
from src.schemas.analytics.receiptResponse import ReceiptAnalyticsResponse
from src.schemas.analytics.request import GetReportWithFilters
from src.schemas.base import RequestAllObject
from src.schemas.payment.create import ReceiptCreateSchema, ReceiptPaymentCreateSchema
from src.schemas.tenant.base import TenantPreferencesSchema
from src.services.system.tenantPreferences_service import TenantPreferencesService
from src.core.utils.common import as_utc, check_branch_belong_to_tenant

class ReceiptService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create(self, data: ReceiptCreateSchema) -> Receipt:
        if data.appointment_id:
            active_stmt = (
                select(Receipt)
                    .where(
                        Receipt.appointment_id == data.appointment_id,
                        Receipt.status.in_([ReceiptStatus.PENDING, ReceiptStatus.PAID])
                    )
            )
            active_result = await self.uow.db.execute(active_stmt)
            existing_active_receipt = active_result.scalar_one_or_none()
            
            if existing_active_receipt: raise AppointmentHasActiveReceipts(data.appointment_id)

        newReceipt = Receipt(
            receipt_type = data.receipt_type,
            client_id = data.client_id
        )

        if data.receipt_type == ReceiptType.APPOINTMENT:
            appointment = await self.uow.appointments.get(data.appointment_id)
            if appointment is None: raise AppointmentNotFound(data.appointment_id)
            if appointment.status == AppointmentStatus.CANCELLED: raise AppointmentCancelled(data.appointment_id)
            if appointment.archived: raise ObjectIsArchived(data.appointment_id, "appointments")
            if appointment.paid: raise AppointmentIsPaid(data.appointment_id)
            if len(appointment.records) == 0: raise ReceiptWithEmptyAppointmentRecords(data.appointment_id)

            newReceipt.appointment_id = appointment.id
            runningSubTotal = 0
            runningTotal = 0 

            for record in appointment.records:
                for service in record.services:
                    item = ReceiptItem(
                        receipt_id = newReceipt.id,
                        appointment_service_id = service.id,
                        base_price = service.base_price,
                        final_price = service.final_price,
                        quantity = service.quantity
                    )
                    runningSubTotal += (service.base_price * service.quantity)
                    runningTotal += (service.final_price * service.quantity)
                    newReceipt.items.append(item)
            
            newReceipt.subtotal_amount = runningSubTotal
            newReceipt.total_amount = runningTotal
        else:
            runningSubTotal = 0
            runningTotal = 0
            
            for item_data in data.receipt_items:
                material = await self.uow.materials.get(item_data.material_id)
                if material is None: raise MaterialNotFound(item_data.material_id)
                if material.archived: raise ObjectIsArchived(material.id, "materials")
                if material.quantity < item_data.quantity: raise MaterialAmountInsufficient(material.id, material.name, item_data.quantity, material.quantity)
                finalPrice: int = material.sell_price

                hasPromotion = await self.uow.promotions.get_by_object(item_data.material_id, "material")
                if hasPromotion is not None:
                    if hasPromotion.promo_type == PromotionType.FIXED_AMOUNT and hasPromotion.discount_value:
                        discount = material.sell_price - hasPromotion.discount_value
                        finalPrice = discount if discount >= 0 else 0
                    elif hasPromotion.promo_type == PromotionType.PERCENTAGE and hasPromotion.discount_value:
                        discount = material.sell_price * (hasPromotion.discount_value / 100)
                        finalPrice = material.sell_price - discount
                
                newQuantity = material.quantity - item_data.quantity
                await self.uow.materials.update(material.id, quantity = newQuantity)

                runningSubTotal += material.sell_price * item_data.quantity
                runningTotal += finalPrice * item_data.quantity
                
                receipt_item = ReceiptItem(
                    receipt_id = newReceipt.id,
                    material_id = material.id,
                    base_price = material.sell_price,
                    final_price = finalPrice,
                    quantity = item_data.quantity
                )
                
                newReceipt.items.append(receipt_item)

            newReceipt.subtotal_amount = runningSubTotal
            newReceipt.total_amount = runningTotal

        try:
            return await self.uow.receipts.create(newReceipt)
        except IntegrityError as exc:
            error_msg = str(exc.orig)
            
            # Check if our specific unique index name is in the Postgres error string
            if "idx_unique_active_receipt_per_appointment" in error_msg:
                raise BaseAppException(
                    detail = "Conflict, for this appointment active receipt was created in parallel",
                    errorCode = "RECEIPT_CREATION_CONFLICT",
                    statusCode = 500
                )

            # If it's a different database error (like a bad check constraint), bubble up the real truth
            raise BaseAppException(
                detail = f"Database integrity violance: {error_msg}",
                errorCode = "DATABASE_INTEGRITY_VIOLANCE",
                statusCode = 500,
                error = error_msg
            )
    
    async def make_payment(self, data: ReceiptPaymentCreateSchema) -> Receipt:        
        stmt = await self.uow.db.execute(select(Receipt)
            .where(Receipt.id == data.receipt_id)
            .options(
                selectinload(Receipt.transactions),
                selectinload(Receipt.appointment),
                selectinload(Receipt.items)
                    .selectinload(ReceiptItem.appointment_service)
                    .selectinload(AppointmentServices.appointment_record)
            ))
        
        # get receipt info
        receipt = stmt.scalar_one_or_none()
        if receipt is None: raise ReceiptNotFound(data.receipt_id)
        if receipt.status == ReceiptStatus.CANCELLED: raise ReceiptIsCancelled(data.receipt_id)
        if receipt.archived: raise ObjectIsArchived(data.receipt_id, "receipts")
        if receipt.remaining_amount == 0: raise ReceiptIsPaid(data.receipt_id)

        client: Client | None = None
        
        # create temp deposit adjustment to substract payment sum in case if payment method is deposit
        depositAdjustment = 0
        if data.method == TransactionMethod.DEPOSIT:
            if receipt.client_id is None: raise ReceiptHasNotClient(data.receipt_id)
            client = await self.uow.clients.get(receipt.client_id)
            if client is None: raise ClientNotFound(receipt.client_id)

            depositAdjustment -= data.amount
            if data.amount > client.deposit:
                raise DepositNotEnough(client.id, client.firstname, data.amount, client.deposit)

        if data.method == TransactionMethod.GIFT_CARD:
            giftCard = await self.uow.giftCards.get(data.giftCard_id)
            if giftCard is None: raise GiftCardNotFound(data.giftCard_id)
            if giftCard.status != GiftCardStatus.ACTIVE: raise GiftCardUnusable(data.giftCard_id, giftCard.status)
            if giftCard.client_id is not None and giftCard.client_id != receipt.client_id: 
                raise GiftCardClientConflict(data.giftCard_id, giftCard.client_id)
            if data.amount > giftCard.remain_amount: raise GiftCardInsufficientAmount(data.giftCard_id, data.amount, giftCard.remain_amount)
            if giftCard.expiration_date is not None and giftCard.expiration_date < datetime.now(timezone.utc):
                raise GiftCardUnusable(data.giftCard_id, GiftCardStatus.EXPIRED)
            
        # add overpaid sum to client's deposit
        if receipt.paid_amount + data.amount >= receipt.total_amount:
            overpayment = (receipt.paid_amount + data.amount) - receipt.total_amount
            applied_amount = data.amount - overpayment
            if data.method == TransactionMethod.GIFT_CARD:
                giftCard.remain_amount -= applied_amount

            if overpayment > 0:
            # if payment method not gift_card - consider overpayment to add client's deposit
                if client is None and receipt.client_id is not None:
                    if receipt.client_id is None: raise ReceiptHasNotClient(data.receipt_id)
                    client = await self.uow.clients.get(receipt.client_id)
                    if client is None: raise ClientNotFound(receipt.client_id)
                receipt.change_amount = overpayment
                receipt.change_to_deposit = data.add_change_to_deposit
                depositAdjustment += overpayment

                await self.uow.transactions.create(Transaction(
                    receipt_id = receipt.id,
                    amount = overpayment,
                    type = (TransactionType.EXPENSE
                            if not data.add_change_to_deposit
                            else TransactionType.INCOME),
                    method = TransactionMethod(data.method),
                    category = (TransactionCategory.CHANGE
                                if not data.add_change_to_deposit
                                else TransactionCategory.DEPOSIT_FULLFILLMENT),
                    auto_generated = True
                ))

            # create new transcation for income from receipt payment
            await self.uow.transactions.create(Transaction(
                receipt_id = receipt.id,
                giftCard_id = data.giftCard_id,
                amount = applied_amount,
                type = TransactionType.INCOME if data.method in [TransactionMethod.CARD,
                    TransactionMethod.CASH,
                    TransactionMethod.BANK_TRANSFER,
                    TransactionMethod.GIFT_CARD] else TransactionType.EXPENSE,
                method = TransactionMethod(data.method),
                category = TransactionCategory.RECEIPT,
                auto_generated = True
            ))

            # add commission to employees
            if receipt.receipt_type == ReceiptType.APPOINTMENT:
                receipt.appointment.paid = True 
                for item in receipt.items:
                    if not item.appointment_service_id:
                        continue
                        
                    appointment_service = item.appointment_service
                    appointment_record = appointment_service.appointment_record
                    employee_id = appointment_record.employee_id
                    
                    employee = await self.uow.employees.get(employee_id)
                    if employee is None: raise EmployeeNotFound(employee_id)
                    
                    if employee and employee.percent_from_services > 0:
                        commission_earned = int(item.total_price * (employee.percent_from_services / 100))
                        if commission_earned > 0:
                            payroll_record = Payroll(
                                employee_id = employee.id,
                                appointment_id = appointment_record.appointment_id,
                                type = PayrollType.COMMISSION,
                                amount = commission_earned,
                                auto_generated = True
                            )
                            await self.uow.payrolls.create(payroll_record)

            receipt.status = ReceiptStatus.PAID
        else:
            receipt.change_amount = 0
            receipt.change_to_deposit = False

            if data.method == TransactionMethod.GIFT_CARD:
                giftCard.remain_amount -= data.amount

            await self.uow.transactions.create(Transaction(
                receipt_id = receipt.id,
                giftCard_id = data.giftCard_id,
                amount = data.amount,
                type = TransactionType.INCOME if data.method in [TransactionMethod.CARD,
                    TransactionMethod.CASH,
                    TransactionMethod.BANK_TRANSFER] else TransactionType.EXPENSE,
                method = TransactionMethod(data.method),
                category = TransactionCategory.RECEIPT,
                auto_generated = True
            ))

        # substract payment sum from client's deposit
        if depositAdjustment != 0 and client is not None:
            final_deposit_balance = client.deposit + depositAdjustment
            await self.uow.clients.update(client.id, deposit = final_deposit_balance)

        return await self.uow.receipts.get(receipt.id)

    async def cancel(self, id: int) -> Receipt:
        receipt = await self.uow.receipts.get(id)
        if receipt is None: raise ReceiptNotFound(id)
        if receipt.status == ReceiptStatus.CANCELLED:
            raise ReceiptIsCancelled(id)

        await self.ensure_receipt_payments_can_be_cancelled(receipt)
        
        deposit_to_refund = 0
        for transaction in receipt.transactions: 
            if transaction.method == TransactionMethod.DEPOSIT: 
                deposit_to_refund += transaction.amount

        if receipt.change_to_deposit and receipt.change_amount > 0:
            deposit_to_refund -= receipt.change_amount

        if deposit_to_refund != 0:
            client_id = (
                receipt.appointment.client_id if receipt.receipt_type == ReceiptType.APPOINTMENT
                else receipt.client_id)
            client = await self.uow.clients.get(client_id)
            if client is None: raise ClientNotFound(client_id)
            if client:
                new_deposit_balance = client.deposit + deposit_to_refund
                await self.uow.clients.update(client.id, deposit = new_deposit_balance)

        # cancel payments and payrolls
        if receipt.receipt_type == ReceiptType.APPOINTMENT:
            stmt = await self.uow.db.execute(
                select(Payroll)
                .where( 
                    Payroll.appointment_id == receipt.appointment_id,
                    Payroll.type == PayrollType.COMMISSION
                )
            )
            payrolls = stmt.scalars().all()
            # cancel payrolls
            payoutsToCancel: set = {}
            for payroll in payrolls:
                payroll.status = PayrollStatus.CANCELLED
                if payroll.payout_id is not None: payoutsToCancel.add(payroll.payout_id)

            if payoutsToCancel:
                payouts = await self.uow.payouts.get_by_ids(list(payoutsToCancel))
                for p in payouts: 
                    p.cancelled = True
                    for t in p.transactions or []: t.cancelled = True

        # return used materials to stock
        if receipt.receipt_type == ReceiptType.DIRECT_SALE:
            for receiptItem in receipt.items:
                material = await self.uow.materials.get(receiptItem.material_id)
                if not material: continue
                newQuantity = material.quantity + receiptItem.quantity
                await self.uow.materials.update(material.id, quantity = newQuantity)

        receipt.status = ReceiptStatus.CANCELLED
        if receipt.appointment: receipt.appointment.paid = False

        receipt.change_amount = 0
        receipt.change_to_deposit = False

        for transaction in receipt.transactions: 
            if transaction.giftCard_id is not None:
                giftCard = await self.uow.giftCards.get(transaction.giftCard_id)
                if giftCard is not None: await self.uow.giftCards.update(
                    giftCard.id, remain_amount = min(giftCard.initial_amount, transaction.amount + giftCard.remain_amount))
            transaction.cancelled = True
            
        return await self.uow.receipts.get(id)

    async def ensure_receipt_payments_can_be_cancelled(self, receipt: Receipt) -> None:
        if not receipt.transactions:
            return

        tenant = await TenantPreferencesService.get_tenant_or_raise(self)
        preferences = TenantPreferencesSchema(**tenant.preferences).model_dump()
        cancel_payment_due = preferences["cancel_payment_due"]

        expired_payment = next(
            (
                transaction
                for transaction in receipt.transactions
                if self.is_payment_cancel_expired(transaction, cancel_payment_due)
            ),
            None,
        )
        if expired_payment is None:
            return

        raise PaymentCancelDueExpired(cancel_payment_due)

    def is_payment_cancel_expired(self, payment: Transaction, cancel_payment_due: int) -> bool:
        cancel_deadline = as_utc(payment.created_at) + timedelta(hours=cancel_payment_due)
        return datetime.now(timezone.utc) > cancel_deadline

    async def get(self, id: int) -> Receipt:
        result = await self.uow.receipts.get(id)
        if result is None: raise ReceiptNotFound(id)
        return result

    async def get_many(self, ids: list[int]) -> list[Receipt]:
        return await self.uow.receipts.get_by_ids(ids)
    
    async def get_all(self, data: RequestAllObject) -> dict:
        items, total_items = await self.uow.receipts.get_all(data)

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }

    async def get_analytics(self, data: GetReportWithFilters) -> ReceiptAnalyticsResponse:
        branchID: int
        if data.branch_id is not None:
            await check_branch_belong_to_tenant(self.uow, data.branch_id)
            branchID = data.branch_id
        else: branchID = get_current_tenant_id()

        data.branch_id = branchID
        row = await self.uow.receipts.get_analytics(data)
        return ReceiptAnalyticsResponse(
            amount = row.amount or 0,
            paid = row.paid or 0,
            unpaid = row.unpaid or 0,
            cancelled = row.cancelled or 0,
            average_receipt_sum = row.average or 0,
            total_paid_sum = row.total_paid_sum or 0
        )
        