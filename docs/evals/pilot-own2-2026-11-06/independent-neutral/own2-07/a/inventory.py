"""Stock reservations."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._reservations: dict[str, tuple[str, int]] = {}
        self._released: set[str] = set()
        self._next_id = 0

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        if qty < 1:
            raise ValueError("qty must be at least 1")
        if self._stock.get(sku, 0) < qty:
            raise OutOfStock(sku)
        self._stock[sku] -= qty
        self._next_id += 1
        rid = f"r{self._next_id}"
        self._reservations[rid] = (sku, qty)
        return rid

    def release(self, reservation_id: str) -> None:
        if reservation_id in self._released:
            return
        sku, qty = self._reservations.pop(reservation_id)  # KeyError if unknown
        self._stock[sku] = self._stock.get(sku, 0) + qty
        self._released.add(reservation_id)
