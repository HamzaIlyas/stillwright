"""Stock reservations. See the change request in instruction.md for the three rules."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._counter = 0
        self._reservations: dict[str, list] = {}

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
            raise ValueError("qty must be an integer >= 1")
        if self._stock.get(sku, 0) < qty:
            raise OutOfStock(sku)
        self._stock[sku] -= qty
        self._counter += 1
        rid = f"res-{self._counter}"
        self._reservations[rid] = [sku, qty, True]
        return rid

    def release(self, reservation_id: str) -> None:
        entry = self._reservations[reservation_id]  # KeyError if unknown
        sku, qty, active = entry
        if not active:
            return
        entry[2] = False
        self._stock[sku] = self._stock.get(sku, 0) + qty
