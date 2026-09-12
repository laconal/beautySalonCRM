import math
import secrets
from sqlalchemy.exc import IntegrityError
from src.core.dependencies.uow import UnitOfWork
from src.exceptions.client_exceptions import ClientNotFound
from src.exceptions.general_exceptions import CannotUpdate, ObjectIsArchived
from src.exceptions.giftCard_exceptions import GiftCardCancelled, GiftCardCharged, GiftCardNotFound
from src.repository.giftCard.giftCard_model import GiftCard, GiftCardStatus
from src.repository.receipt.receipt_model import Receipt, ReceiptItem, ReceiptStatus, ReceiptType
from src.repository.transaction.transaction_model import Transaction, TransactionCategory, TransactionMethod, TransactionType
from src.schemas.base import RequestAllObject
from src.schemas.giftCard.create import GiftCardCreateSchema
from src.schemas.giftCard.update import GiftCardUpdateSchema
from src.schemas.giftCard.request import GiftCardCancelSchema

ALLOWED_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
MAX_CODE_GENERATION_ATTEMPTS = 5

class GiftCardService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    @staticmethod
    def _generate_gift_card_code() -> str:
        """
        Generates a human-readable code like: XK-8X4N-92KP
        Excludes ambiguous characters (0, O, 1, I, L).
        """
        prefix = "".join(secrets.choice(ALLOWED_CHARS) for _ in range(2))
        chunk1 = "".join(secrets.choice(ALLOWED_CHARS) for _ in range(4))
        chunk2 = "".join(secrets.choice(ALLOWED_CHARS) for _ in range(4))
        return f"{prefix}-{chunk1}-{chunk2}"

    async def _create_gift_card_with_unique_code(self, newObject: GiftCard) -> GiftCard:
        """
        Inserts newObject inside a SAVEPOINT, retrying with a freshly generated
        code if it collides with an existing one (uq_gift_card_code), without
        aborting the rest of the request's transaction (receipt/transaction creation).
        """
        self.uow.db.add(newObject)

        for attempt in range(1, MAX_CODE_GENERATION_ATTEMPTS + 1):
            newObject.code = self._generate_gift_card_code()
            try:
                async with self.uow.db.begin_nested():
                    await self.uow.db.flush()
                break
            except IntegrityError as exc:
                constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                if constraint_name != "uq_gift_card_code" or attempt == MAX_CODE_GENERATION_ATTEMPTS:
                    raise

        await self.uow.db.refresh(newObject)
        return newObject

    async def create(self, data: GiftCardCreateSchema) -> GiftCard:
        if data.client_id is not None:
            checkClient = await self.uow.clients.get(data.client_id)
            if checkClient is None: raise ClientNotFound(data.client_id)
            if checkClient.archived: raise ObjectIsArchived(data.client_id, "clients")

        giftCardData = data.model_dump(exclude = {"payment_method"}, exclude_unset = True)
        newObject = GiftCard(**giftCardData)
        newObject.remain_amount = data.initial_amount

        receiptData = Receipt(
            receipt_type = ReceiptType.DIRECT_SALE,
            client_id = data.client_id,
            subtotal_amount = data.initial_amount,
            total_amount = data.initial_amount,
            status = ReceiptStatus.PAID
        )
        receipt = await self.uow.receipts.create(receiptData)

        newObject.receipt_id = receipt.id
        giftCard = await self._create_gift_card_with_unique_code(newObject)

        receiptItem = ReceiptItem(
            receipt_id = receipt.id,
            giftCard_id = giftCard.id,
            base_price = data.initial_amount,
            final_price = data.initial_amount,
            quantity = 1
        )
        receipt.items.append(receiptItem)

        await self.uow.transactions.create(Transaction(
            receipt_id = receipt.id,
            amount = data.initial_amount,
            type = TransactionType.INCOME,
            method = TransactionMethod(data.payment_method),
            category = TransactionCategory.GIFT_CARD,
            auto_generated = True
        ))

        return giftCard

    async def update(self, data: GiftCardUpdateSchema) -> GiftCard:
        promotion = await self.uow.giftCards.get(data.id)
        if promotion is None: raise GiftCardNotFound(data.id)
        if promotion.archived: raise ObjectIsArchived(data.id, "gift_cards")

        dataDict = data.model_dump(exclude = {"id"}, exclude_unset = True)
        result = await self.uow.giftCards.update(data.id, **dataDict)
        if result is None: raise CannotUpdate(data.id, "gift_cards")
        return result

    async def get(self, id: int) -> GiftCard:
        giftCard = await self.uow.giftCards.get(id)
        if giftCard is None: raise GiftCardNotFound(id)
        return giftCard

    async def get_all(self, data: RequestAllObject) -> dict:
        items, total_items = await self.uow.giftCards.get_all(data)

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }

    async def cancel(self, data: GiftCardCancelSchema) -> GiftCard:
        giftCard = await self.uow.giftCards.get(data.id)
        if giftCard is None: raise GiftCardNotFound(data.id)
        if giftCard.status == GiftCardStatus.CANCELLED: raise GiftCardCancelled(data.id)
        if giftCard.initial_amount != giftCard.remain_amount:
            raise GiftCardCharged(data.id)

        result = await self.uow.giftCards.update(data.id, status = GiftCardStatus.CANCELLED)

        transactions = await self.uow.transactions.get_by_receipt(result.receipt_id)
        for transaction in transactions: await self.uow.transactions.update(
            transaction.id,
            cancelled = True)

        return result