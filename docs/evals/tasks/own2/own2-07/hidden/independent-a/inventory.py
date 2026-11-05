"""Stock reservations."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._reservations: dict[str, list] = {}
        self._next_id = 0

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> str:
        if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
            raise ValueError(f"qty must be an integer >= 1, got {qty!r}")
        if self.available(sku) < qty:
            raise OutOfStock(f"{sku}: wanted {qty}, available {self.available(sku)}")
        self._stock[sku] = self.available(sku) - qty
        self._next_id += 1
        reservation_id = f"R{self._next_id}"
        self._reservations[reservation_id] = [sku, qty, True]
        return reservation_id

    def release(self, reservation_id: str) -> None:
        # Records are kept after release so ids are never reused and a
        # repeated release can be told apart from an unknown id.
        record = self._reservations[reservation_id]  # KeyError if unknown
        sku, qty, active = record
        if not active:
            return
        record[2] = False
        self._stock[sku] = self.available(sku) + qty
