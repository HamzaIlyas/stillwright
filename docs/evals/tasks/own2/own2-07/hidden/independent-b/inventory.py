"""Stock reservations."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._reservations: dict[str, list] = {}  # id -> [sku, qty, active]
        self._counter = 0

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        if qty < 1:
            raise ValueError("qty must be at least 1")
        if self.available(sku) < qty:
            raise OutOfStock(f"{sku}: requested {qty}, available {self.available(sku)}")
        self._stock[sku] = self.available(sku) - qty
        self._counter += 1
        rid = f"r{self._counter}"
        self._reservations[rid] = [sku, qty, True]
        return rid

    def release(self, reservation_id: str) -> None:
        sku, qty, active = self._reservations[reservation_id]  # KeyError if unknown
        if not active:
            return
        self._reservations[reservation_id][2] = False
        self._stock[sku] = self.available(sku) + qty
