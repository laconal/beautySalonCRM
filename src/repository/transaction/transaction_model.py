from __future__ import annotations
from enum import StrEnum
from typing import TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from src.database.base import BaseFields

if TYPE_CHECKING: 
    from src.repository.payroll.payroll_model import Payout
    from src.repository.receipt.receipt_model import Receipt
    from src.repository.giftCard.giftCard_model import GiftCard

class TransactionType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    
class TransactionCategory(StrEnum):
    RECEIPT = "receipt"
    EMPLOYEE_PAYMENT = "employee payment"
    CHANGE = "change"
    DEPOSIT_FULLFILLMENT = "deposit fullfillment"
    GIFT_CARD = "gift card"
    UTILITY = "utility"
    INTERNET = "internet"
    TELEPHONE = "telephone"
    OTHER = "other"

class TransactionMethod(StrEnum):
    CARD = "card"
    CASH = "cash"
    BANK_TRANSFER = "bank transfer"
    DEPOSIT = "deposit"
    GIFT_CARD = "gift card"

class Transaction(BaseFields):
    __tablename__ = "transactions"

    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(50))
    method: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50))
    
    notes: Mapped[str | None] = mapped_column(Text, nullable = True)
    cancelled: Mapped[bool] = mapped_column(Boolean, default = False, server_default = "false")
    auto_generated: Mapped[bool] = mapped_column(Boolean, default = False, server_default = "false")

    receipt_id: Mapped[int | None] = mapped_column(Integer, nullable = True)
    receipt: Mapped["Receipt"] = relationship(
        back_populates = "transactions",
        primaryjoin = "and_(Receipt.id == Transaction.receipt_id, Receipt.tenant_id == Transaction.tenant_id)",
        foreign_keys = [receipt_id]
    )

    payout_id: Mapped[int | None] = mapped_column(Integer, nullable = True)
    payout: Mapped["Payout"] = relationship(
        back_populates = "transactions",
        primaryjoin = "and_(Transaction.payout_id == Payout.id, Transaction.tenant_id == Payout.tenant_id)",
        foreign_keys = [payout_id])

    giftCard_id: Mapped[int | None] = mapped_column(Integer, nullable = True)
    giftCard: Mapped["GiftCard"] = relationship(
        primaryjoin = "and_(Transaction.giftCard_id == GiftCard.id, Transaction.tenant_id == GiftCard.tenant_id)",
        foreign_keys = [giftCard_id]
    )
    
    gateway: Mapped[str | None] = mapped_column(String(50), nullable = True, default = "manual")
    gateway_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable = True)
    gateway_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable = True)

    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name = "uq_transaction_tenant"),
        ForeignKeyConstraint(
            ["receipt_id", "tenant_id"],
            ["receipts.id", "receipts.tenant_id"],
            ondelete = "SET NULL (receipt_id)",
            name = "fk_transcation_receipt"
        ),
        ForeignKeyConstraint(
            ["payout_id", "tenant_id"],
            ["payouts.id", "payouts.tenant_id"],
            ondelete = "SET NULL (payout_id)",
            name = "fk_transcation_payout"
        ),
        ForeignKeyConstraint(
            ["giftCard_id", "tenant_id"],
            ["gift_cards.id", "gift_cards.tenant_id"],
            ondelete = 'SET NULL ("giftCard_id")',
            name = "fk_transaction_giftCard"
        ),
        ForeignKeyConstraint(
            ["created_by_actor_id", "tenant_id"],
            ["actors.id", "actors.tenant_id"],
            ondelete = "SET NULL (created_by_actor_id)",
            name = "fk_transactions_created_by_tenant"
        ),
    )
 
    ALLOWED_FILTERS = {"amount", "type", "method", "category", "cancelled", "auto_generated", "archived"}