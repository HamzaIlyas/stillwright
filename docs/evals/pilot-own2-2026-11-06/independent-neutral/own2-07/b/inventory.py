"""Stock reservations."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._counter = 0
        self._open: dict[str, tuple[str, int]] = {}
        self._released: set[str] = set()

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        if qty < 1:
            raise ValueError("qty must be at least 1")
        if self._stock.get(sku, 0) < qty:
            raise OutOfStock(sku)
        self._stock[sku] -= qty
        self._counter += 1
        rid = f"R{self._counter}"
        self._open[rid] = (sku, qty)
        return rid

    def release(self, reservation_id: str) -> None:
        if reservation_id in self._released:
            return
        if reservation_id not in self._open:
            raise KeyError(reservation_id)
        sku, qty = self._open.pop(reservation_id)
        self._stock[sku] = self._stock.get(sku, 0) + qty
        self._released.add(reservation_id)
