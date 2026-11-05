"""Rules 1 and 2; release returns units every time it is called (not idempotent) and never raises."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._reservations: dict[str, tuple[str, int]] = {}
        self._n = 0

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        if qty < 1:
            raise ValueError("qty must be >= 1")
        if self._stock.get(sku, 0) < qty:
            raise OutOfStock(sku)
        self._stock[sku] -= qty
        self._n += 1
        rid = f"r{self._n}"
        self._reservations[rid] = (sku, qty)
        return rid

    def release(self, reservation_id: str) -> None:
        sku, qty = self._reservations.get(reservation_id, (None, 0))
        if sku is not None:
            self._stock[sku] += qty
