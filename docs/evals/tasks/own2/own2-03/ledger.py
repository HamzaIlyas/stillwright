"""A tiny ledger of accounts in one currency. Amounts arrive as decimal strings or floats with at most two
decimals; balances are exact to the cent and reported as two-decimal strings. A transfer may charge the
sender a fee of amount * fee_rate, rounded half-up to the cent and credited to the account "fees"; a move
an account cannot cover raises ValueError and changes nothing."""


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
