"""Mock payments API."""

from dataclasses import dataclass

from tennis import StrEnum, log


@dataclass
class Card:
    """Credit card details."""

    number: int
    name: str
    cvv: int
    exp_month: int
    exp_year: int


class PaymentResult(StrEnum):
    """Payment result enumeration."""

    Ok = 'OK'
    Declined = 'Declined'

    def __bool__(self) -> bool:
        """Return boolean representation of this enum."""
        return self == self.Ok


@dataclass
class Payment:
    """Payment class."""

    amount: float
    card: Card

    def authorize(self) -> PaymentResult:
        """Authorize payment."""
        log.info(f'Charged amount ${self.amount:.2f} to card {self.card}')
        return PaymentResult.Ok
