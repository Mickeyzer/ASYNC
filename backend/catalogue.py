import csv
from dataclasses import asdict, dataclass
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "YTL_TrackA_Udyam_Digital_Data"


@dataclass(frozen=True)
class Product:
    product_id: str
    category: str
    name: str
    description: str
    unit: str
    monthly_price: int
    monthly_max: int
    setup_fee: int
    contract_months: int
    city_tiers: tuple[int, ...]
    min_employees: int
    min_sites: int
    requires_gstin: bool
    requires_one_of: tuple[str, ...]
    install_days: int

    def public(self):
        return asdict(self)


def load_catalogue(path: Path = DATA_DIR / "product_catalogue.csv") -> dict[str, Product]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            product = Product(
                product_id=row["product_id"], category=row["category"],
                name=row["product_name"], description=row["description"], unit=row["unit"],
                monthly_price=int(row["price_min_inr_per_month"]),
                monthly_max=int(row["price_max_inr_per_month"]),
                setup_fee=int(row["one_time_setup_inr"]),
                contract_months=int(row["min_contract_months"]),
                city_tiers=tuple(map(int, row["available_city_tiers"].split(";"))),
                min_employees=int(row["min_employees"]), min_sites=int(row["min_sites"]),
                requires_gstin=row["requires_gstin"] == "Y",
                requires_one_of=tuple(filter(None, row["requires_one_of"].split("|"))),
                install_days=int(row["typical_install_days"]),
            )
            if product.product_id in result:
                raise ValueError("Duplicate catalogue product")
            result[product.product_id] = product
    for product in result.values():
        if not set(product.requires_one_of) <= result.keys():
            raise ValueError("Unknown product dependency")
    return result


CATALOGUE = load_catalogue()
