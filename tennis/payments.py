"""Mock payments API."""

from dataclasses import dataclass, field
from enum import Enum

from tennis import log


class PaymentResult(str, Enum):
    Ok = "OK"
    Declined = "Declined"

    def __bool__(self) -> bool:
        return self == self.Ok


@dataclass
class Card:
    number: int
    name: str
    cvv: int
    exp_month: int
    exp_year: int

    balance: float = field(default=0.0)
    limit: float = field(default=1_000.0)

    def authorize_payment(self, amount: float) -> PaymentResult:
        if self.balance + amount <= self.limit:
            log.info(f"Charged amount ${amount:.2f}")
            self.balance += amount
            return PaymentResult.Ok
        log.info("Card declined; insufficient funds.")
        return PaymentResult.Declined
