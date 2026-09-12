from .base import BaseAppException

class ReceiptNotFound(BaseAppException):
    statusCode = 404
    errorCode = "RECEIPT_NOT_FOUND"
    def __init__(self, id: int):
        super().__init__(
            detail = f"Receipt ID {id} not found",
            errorCode = self.errorCode,
            id = id
        )

class ReceiptWithEmptyAppointmentRecords(BaseAppException):
    statusCode = 409
    errorCode = "RECEIPT_CANNOT_BE_CREATED_FOR_APPOINTMENT_EMPTY_RECORDS"
    def __init__(self, id: int):
        super().__init__(
            detail = "Receipt cannot be created for appointment which does not have records",
            errorCode = self.errorCode,
            appointment_id = id
        )

class ReceiptIsPaid(BaseAppException):
    statusCode = 409
    errorCode = "RECEIPT_IS_PAID"
    def __init__(self, id: int):
        super().__init__(
            detail = f"Receipt ID {id} has paid",
            errorCode = self.errorCode,
            id = id
        )

class ReceiptIsCancelled(BaseAppException):
    statusCode = 409
    errorCode = "RECEIPT_IS_CANCELLED"
    def __init__(self, id: int):
        super().__init__(
            detail = f"Receipt (ID {id}) is cancelled",
            errorCode = self.errorCode
        )

class ReceiptHasNotClient(BaseAppException):
    statusCode = 409
    errorCode = "RECEIPT_HAS_NO_CLIENT"
    def __init__(self, id: int):
        super().__init__(
            detail = f"Receipt ID {id} has no client",
            id = id
        )