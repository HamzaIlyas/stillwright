"""A tiny ledger of accounts in one currency. Amounts arrive as decimal strings or floats with at most two
decimals; balances are exact to the cent and reported as two-decimal strings. A transfer may charge the
sender a fee of amount * fee_rate, rounded half-up to the cent and credited to the account "fees"; a move
an account cannot cover raises ValueError and changes nothing."""


from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")


def _to_cents(amount) -> int:
    """Exact conversion of a decimal string/float/Decimal to integer cents."""
    return int((Decimal(str(amount)) / _CENT).to_integral_value(ROUND_HALF_UP))


def _fmt(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole}.{frac:02d}"


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
        fee = int((Decimal(cents) * Decimal(str(fee_rate))).to_integral_value(ROUND_HALF_UP))
        if self._bal.get(src, 0) - cents - fee < 0:
            raise ValueError("insufficient funds")
        self._bal[src] = self._bal.get(src, 0) - cents - fee
        self._bal[dst] = self._bal.get(dst, 0) + cents
        self._bal["fees"] = self._bal.get("fees", 0) + fee

    def total(self) -> str:
        return _fmt(sum(self._bal.values()))
