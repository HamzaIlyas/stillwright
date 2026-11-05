"""Rule 1 only: reserve decrements, may go negative, release not implemented."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._n = 0

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        self._stock[sku] = self._stock.get(sku, 0) - qty
        self._n += 1
        return str(self._n)

    def release(self, reservation_id: str) -> None:
        raise NotImplementedError
