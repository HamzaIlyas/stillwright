"""Stock reservations."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        raise NotImplementedError

    def release(self, reservation_id: str) -> None:
        raise NotImplementedError
