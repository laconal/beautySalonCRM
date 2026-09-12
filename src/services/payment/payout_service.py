import math
from src.core.decorators.requireID import require_exists
from src.core.dependencies.uow import UnitOfWork
from src.exceptions.employee_exceptions import EmployeeDoesNotHavePayrolls
from src.exceptions.general_exceptions import ObjectIsArchived
from src.exceptions.payout_exception import PayoutIsCancelled, PayoutNotFound
from src.exceptions.payroll_exceptions import PayrollIsCancelled, PayrollIsPaid, PayrollNotAttachedToEmployee, PayrollOneOrMoreNotFound
from src.repository.payroll.payroll_model import Payout, PayrollStatus
from src.repository.transaction.transaction_model import Transaction, TransactionCategory, TransactionMethod, TransactionType
from src.schemas.base import RequestAllObject
from src.schemas.payout.create import PayoutCreateSchema

class PayoutService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
    
    @require_exists("employees", target_param = "employee_id")
    async def create(self, data: PayoutCreateSchema) -> Payout:
        payoutData = data.model_dump(exclude = {"payrolls", "start_date", "end_date"})
        payrollsIDs = data.payrolls or []

        validPayrolls = []

        if payrollsIDs:
            validPayrolls = await self.uow.payrolls.get_by_ids(payrollsIDs, lock = True)
            if len(validPayrolls) != len(payrollsIDs):
                raise PayrollOneOrMoreNotFound()

            for payroll in validPayrolls:
                if payroll.employee_id != data.employee_id: raise PayrollNotAttachedToEmployee(payroll.id, data.employee_id)
                if payroll.status == PayrollStatus.PAID: raise PayrollIsPaid(payroll.id)
                if payroll.status == PayrollStatus.CANCELLED: raise PayrollIsCancelled(payroll.id)

        elif data.start_date and data.end_date:
            validPayrolls = await self.uow.payrolls.get_pendings(data.employee_id, data.start_date, data.end_date, lock = True)
            if not validPayrolls: raise EmployeeDoesNotHavePayrolls(data.employee_id)
        else:
            validPayrolls = await self.uow.payrolls.get_pendings(data.employee_id, lock = True)
            if not validPayrolls: raise EmployeeDoesNotHavePayrolls(data.employee_id)

        for payroll in validPayrolls:
            payroll.status = PayrollStatus.PAID

        newPayout = Payout(**payoutData)
        newPayout.payrolls = validPayrolls
        await self.uow.payouts.create(newPayout)
        result = await self.uow.payouts.get(newPayout.id)

        await self.uow.transactions.create(Transaction(
            amount = result.total_amount,
            type = TransactionType.EXPENSE,
            method = TransactionMethod(newPayout.method),
            category = TransactionCategory.EMPLOYEE_PAYMENT,
            payout_id = result.id,
            auto_generated = True
        ))

        return result
    
    async def get(self, id: int) -> Payout:
        result = await self.uow.payouts.get(id)
        if not result: raise PayoutNotFound(id)
        return result
    
    async def get_many(self, ids: list[int]) -> list[Payout]:
        return await self.uow.payoutss.get_by_ids(ids)
    
    async def get_all(self, data: RequestAllObject) -> dict:
        items, total_items = await self.uow.payouts.get_all(data)

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }
    
    async def cancel(self, id: int) -> Payout:
        payout = await self.uow.payouts.get(id)
        if payout is None: raise PayoutNotFound(id)

        if payout.cancelled: raise PayoutIsCancelled(id)
        if payout.archived: raise ObjectIsArchived(id, "payouts")

        # cancel transactions
        for transaction in payout.transactions:
            await self.uow.transactions.update(transaction.id, cancelled = True)

        # set payout_id in payrolls to null
        for payroll in payout.payrolls:
            await self.uow.payrolls.update(payroll.id, 
                                           status = PayrollStatus.PENDING, payout_id = None)
        
        return await self.uow.payouts.update(id, cancelled = True)
        