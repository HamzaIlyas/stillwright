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


class Ledger:
    def __init__(self):
        self._bal: dict[str, float] = {}

    def balance(self, account: str) -> str:
        return f"{self._bal.get(account, 0.0):.2f}"

    def deposit(self, account: str, amount) -> None:
        self._bal[account] = self._bal.get(account, 0.0) + float(amount)

    def withdraw(self, account: str, amount) -> None:
        new = self._bal.get(account, 0.0) - float(amount)
        if new < 0:
            raise ValueError("insufficient funds")
        self._bal[account] = new

    def transfer(self, src: str, dst: str, amount, fee_rate: float = 0.0) -> None:
        amount = float(amount)
        fee = round(amount * fee_rate, 2)
        if self._bal.get(src, 0.0) - amount - fee < 0:
            raise ValueError("insufficient funds")
        self._bal[src] = self._bal.get(src, 0.0) - amount - fee
        self._bal[dst] = self._bal.get(dst, 0.0) + amount
        self._bal["fees"] = self._bal.get("fees", 0.0) + fee

    def total(self) -> str:
        return f"{sum(self._bal.values()):.2f}"
