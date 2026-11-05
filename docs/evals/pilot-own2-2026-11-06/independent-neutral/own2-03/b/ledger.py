"""A tiny ledger of accounts in one currency. Amounts arrive as decimal strings or floats with at most two
decimals; balances are exact to the cent and reported as two-decimal strings. A transfer may charge the
sender a fee of amount * fee_rate, rounded half-up to the cent and credited to the account "fees"; a move
an account cannot cover raises ValueError and changes nothing."""

from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


def _to_cents(amount) -> int:
    value = Decimal(str(amount)).quantize(_CENT, rounding=ROUND_HALF_UP)
    return int(value * 100)


def _fmt(cents: int) -> str:
    return f"{Decimal(cents) / 100:.2f}"


class Ledger:
    def __init__(self):
        self._bal: dict[str, int] = {}

    def balance(self, account: str) -> str:
        return _fmt(self._bal.get(account, 0))

    def deposit(self, account: str, amount) -> None:
        self._bal[account] = self._bal.get(account, 0) + _to_cents(amount)

    def withdraw(self, account: str, amount) -> None:
        new = self._bal.get(account, 0) - _to_cents(amount)
        if new < 0:
            raise ValueError("insufficient funds")
        self._bal[account] = new

    def transfer(self, src: str, dst: str, amount, fee_rate: float = 0.0) -> None:
        cents = _to_cents(amount)
        fee = int(
            (Decimal(cents) * Decimal(str(fee_rate))).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        )
        if self._bal.get(src, 0) - cents - fee < 0:
            raise ValueError("insufficient funds")
        self._bal[src] = self._bal.get(src, 0) - cents - fee
        self._bal[dst] = self._bal.get(dst, 0) + cents
        self._bal["fees"] = self._bal.get("fees", 0) + fee

    def total(self) -> str:
        return _fmt(sum(self._bal.values()))
