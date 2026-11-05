class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._reservations: dict[str, tuple[str, int]] = {}
        self._released: set[str] = set()
        self._next = 0

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        if qty < 1:
            raise ValueError("qty must be >= 1")
        if self._stock.get(sku, 0) < qty:
            raise OutOfStock(sku)
        self._stock[sku] -= qty
        self._next += 1
        rid = f"r{self._next}"
        self._reservations[rid] = (sku, qty)
        return rid

    def release(self, reservation_id: str) -> None:
        if reservation_id in self._released:
            return
        if reservation_id not in self._reservations:
            raise KeyError(reservation_id)
        sku, qty = self._reservations[reservation_id]
        self._stock[sku] = self._stock.get(sku, 0) + qty
        self._released.add(reservation_id)
