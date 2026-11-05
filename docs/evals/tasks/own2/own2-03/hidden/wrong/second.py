"""Second wrong fix: Decimal everywhere, but the fee is quantized with the default (half-even) rounding."""
from decimal import Decimal


class Ledger:
    def __init__(self):
        self._bal: dict[str, Decimal] = {}

    def balance(self, account: str) -> str:
        return f"{self._bal.get(account, Decimal('0')):.2f}"

    def deposit(self, account: str, amount) -> None:
        self._bal[account] = self._bal.get(account, Decimal("0")) + Decimal(str(amount))

    def withdraw(self, account: str, amount) -> None:
        new = self._bal.get(account, Decimal("0")) - Decimal(str(amount))
        if new < 0:
            raise ValueError("insufficient funds")
        self._bal[account] = new

    def transfer(self, src: str, dst: str, amount, fee_rate: float = 0.0) -> None:
        amt = Decimal(str(amount))
        fee = (amt * Decimal(str(fee_rate))).quantize(Decimal("0.01"))
        if self._bal.get(src, Decimal("0")) - amt - fee < 0:
            raise ValueError("insufficient funds")
        self._bal[src] = self._bal.get(src, Decimal("0")) - amt - fee
        self._bal[dst] = self._bal.get(dst, Decimal("0")) + amt
        self._bal["fees"] = self._bal.get("fees", Decimal("0")) + fee

    def total(self) -> str:
        return f"{sum(self._bal.values(), Decimal('0')):.2f}"
