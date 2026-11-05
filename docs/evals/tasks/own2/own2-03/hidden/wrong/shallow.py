"""Shallow fix: round every stored balance to two decimals; fees still use float round()."""


class Ledger:
    def __init__(self):
        self._bal: dict[str, float] = {}

    def balance(self, account: str) -> str:
        return f"{round(self._bal.get(account, 0.0), 2):.2f}"

    def deposit(self, account: str, amount) -> None:
        self._bal[account] = round(self._bal.get(account, 0.0) + float(amount), 2)

    def withdraw(self, account: str, amount) -> None:
        new = round(self._bal.get(account, 0.0) - float(amount), 2)
        if new < 0:
            raise ValueError("insufficient funds")
        self._bal[account] = new

    def transfer(self, src: str, dst: str, amount, fee_rate: float = 0.0) -> None:
        amount = float(amount)
        fee = round(amount * fee_rate, 2)
        if round(self._bal.get(src, 0.0) - amount - fee, 2) < 0:
            raise ValueError("insufficient funds")
        self._bal[src] = round(self._bal.get(src, 0.0) - amount - fee, 2)
        self._bal[dst] = round(self._bal.get(dst, 0.0) + amount, 2)
        self._bal["fees"] = round(self._bal.get("fees", 0.0) + fee, 2)

    def total(self) -> str:
        return f"{round(sum(self._bal.values()), 2):.2f}"
