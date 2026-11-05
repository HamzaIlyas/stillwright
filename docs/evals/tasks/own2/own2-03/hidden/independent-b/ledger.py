"""A tiny ledger of accounts in one currency. Amounts arrive as decimal strings or floats with at most two
decimals; balances are exact to the cent and reported as two-decimal strings. A transfer may charge the
sender a fee of amount * fee_rate, rounded half-up to the cent and credited to the account "fees"; a move
an account cannot cover raises ValueError and changes nothing."""


from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_CENT = Decimal("0.01")


def _to_cents(amount) -> int:
    """Exact cents from a decimal string or float (floats via their shortest repr, not binary expansion)."""
    try:
        d = Decimal(str(amount).strip())
    except InvalidOperation:
        raise ValueError(f"invalid amount: {amount!r}") from None
    if not d.is_finite() or d < 0 or d != d.quantize(_CENT):
        raise ValueError(f"invalid amount: {amount!r}")
    return int(d / _CENT)


def _fee_cents(cents: int, fee_rate) -> int:
    fee = Decimal(cents) * Decimal(str(fee_rate))
    return int(fee.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _fmt(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100}.{abs(cents) % 100:02d}"


class Ledger:
    def __init__(self):
        self._bal: dict[str, int] = {}  # cents

    def balance(self, account: str) -> str:
        return _fmt(self._bal.get(account, 0))

    def deposit(self, account: str, amount) -> None:
        cents = _to_cents(amount)
        self._bal[account] = self._bal.get(account, 0) + cents

    def withdraw(self, account: str, amount) -> None:
        cents = _to_cents(amount)
        new = self._bal.get(account, 0) - cents
        if new < 0:
            raise ValueError("insufficient funds")
        self._bal[account] = new

    def transfer(self, src: str, dst: str, amount, fee_rate: float = 0.0) -> None:
        cents = _to_cents(amount)
        fee = _fee_cents(cents, fee_rate)
        if self._bal.get(src, 0) - cents - fee < 0:
            raise ValueError("insufficient funds")
        self._bal[src] = self._bal.get(src, 0) - cents - fee
        self._bal[dst] = self._bal.get(dst, 0) + cents
        self._bal["fees"] = self._bal.get("fees", 0) + fee

    def total(self) -> str:
        return _fmt(sum(self._bal.values()))
