"""A tiny ledger of accounts holding money in a single currency.

Rules:
- Amounts are given as decimal strings or floats with at most two decimals ("12.34"). The ledger keeps
  them exact: `balance(account)` returns a `str` with exactly two decimals, never a float artefact.
- `deposit(account, amount)` and `withdraw(account, amount)` adjust one account. A withdrawal that would
  take an account below 0.00 raises `ValueError` and changes nothing.
- `transfer(src, dst, amount, fee_rate)` moves `amount` from `src` to `dst` and charges `src` a fee of
  `amount * fee_rate`, rounded to the cent half-up (0.015 -> 0.02, 0.025 -> 0.03, 0.0149 -> 0.01). The
  fee goes to the account named "fees". If `src` cannot cover amount plus fee, raise `ValueError` and
  change nothing.
- `total()` is the sum of all balances, as a two-decimal `str`.
- Unknown accounts have balance 0.00.
"""


from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_CENT = Decimal("0.01")


def _to_money(amount) -> Decimal:
    """Parse a str/int/float amount into an exact Decimal with at most two decimals."""
    try:
        value = Decimal(str(amount).strip())
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {amount!r}") from exc
    if not value.is_finite():
        raise ValueError(f"invalid amount: {amount!r}")
    if value != value.quantize(_CENT):
        raise ValueError(f"amount has more than two decimals: {amount!r}")
    if value < 0:
        raise ValueError("amount must not be negative")
    return value.quantize(_CENT)


def _fmt(value: Decimal) -> str:
    return f"{value.quantize(_CENT):.2f}"


class Ledger:
    def __init__(self):
        self._bal: dict[str, Decimal] = {}

    def _get(self, account: str) -> Decimal:
        return self._bal.get(account, Decimal("0.00"))

    def balance(self, account: str) -> str:
        return _fmt(self._get(account))

    def deposit(self, account: str, amount) -> None:
        value = _to_money(amount)
        self._bal[account] = self._get(account) + value

    def withdraw(self, account: str, amount) -> None:
        value = _to_money(amount)
        new = self._get(account) - value
        if new < 0:
            raise ValueError("insufficient funds")
        self._bal[account] = new

    def transfer(self, src: str, dst: str, amount, fee_rate=0) -> None:
        value = _to_money(amount)
        try:
            rate = Decimal(str(fee_rate))
        except InvalidOperation as exc:
            raise ValueError(f"invalid fee rate: {fee_rate!r}") from exc
        if not rate.is_finite() or rate < 0:
            raise ValueError(f"invalid fee rate: {fee_rate!r}")
        fee = (value * rate).quantize(_CENT, rounding=ROUND_HALF_UP)
        if self._get(src) - value - fee < 0:
            raise ValueError("insufficient funds")
        new = dict(self._bal)
        new[src] = new.get(src, Decimal("0.00")) - value - fee
        new[dst] = new.get(dst, Decimal("0.00")) + value
        new["fees"] = new.get("fees", Decimal("0.00")) + fee
        self._bal = new

    def total(self) -> str:
        return _fmt(sum(self._bal.values(), Decimal("0.00")))
