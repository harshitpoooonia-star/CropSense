"""Pure fertilizer arithmetic (spec 03, R2). No Flask, no I/O.

Standard dose (kg nutrient per hectare) -> products:
    phosphate from DAP first, and DAP's nitrogen is subtracted from the N need;
    potash from MOP; the rest of the nitrogen from urea.
    With SSP instead of DAP, all nitrogen comes from urea.
Card dose (kg product per hectare or acre) -> scaled to the field.
Then kg -> bags (to 0.1) -> whole bags to buy -> Rs for the bags bought.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

HECTARES_PER_ACRE = Decimal("0.40468564224")
ZERO = Decimal(0)


@dataclass(frozen=True)
class Product:
    code: str  # urea | dap | mop | ssp
    n_pct: Decimal
    p2o5_pct: Decimal
    k2o_pct: Decimal
    bag_kg: Decimal
    price_per_bag: Decimal


@dataclass(frozen=True)
class Dose:
    """kg of nutrient per hectare."""

    n: Decimal = ZERO
    p2o5: Decimal = ZERO
    k2o: Decimal = ZERO


@dataclass(frozen=True)
class Line:
    product: str
    kg: Decimal
    bags: Decimal  # exact, to 0.1
    bags_to_buy: int
    cost: Decimal  # for the bags to buy


@dataclass
class Plan:
    lines: list[Line]
    stages: dict[str, dict[str, Decimal]] = field(default_factory=dict)  # stage -> product -> kg

    @property
    def total_cost(self) -> Decimal:
        return sum((line.cost for line in self.lines), ZERO)

    def line(self, product: str) -> Line | None:
        return next((line for line in self.lines if line.product == product), None)


def product_kg(dose: Dose, area_ha: Decimal, products: dict[str, Product], phosphate: str = "dap") -> dict[str, Decimal]:
    """kg of each product for the whole field. phosphate: 'dap' or 'ssp'."""
    n, p, k = dose.n * area_ha, dose.p2o5 * area_ha, dose.k2o * area_ha
    kg: dict[str, Decimal] = {}
    if p > 0:
        source = products[phosphate]
        kg[phosphate] = p / (source.p2o5_pct / 100)
        n -= kg[phosphate] * source.n_pct / 100
    if k > 0:
        kg["mop"] = k / (products["mop"].k2o_pct / 100)
    if n > 0:
        kg["urea"] = n / (products["urea"].n_pct / 100)
    return kg


def card_kg(per_unit: dict[str, Decimal], unit: str, area_ha: Decimal) -> dict[str, Decimal]:
    """A Soil Health Card dose in kg of product per hectare/acre -> kg for the field."""
    area = area_ha if unit == "hectare" else area_ha / HECTARES_PER_ACRE
    return {code: amount * area for code, amount in per_unit.items() if amount and amount > 0}


def to_plan(kg: dict[str, Decimal], products: dict[str, Product]) -> Plan:
    order = ("urea", "dap", "ssp", "mop")
    lines = []
    for code in sorted(kg, key=order.index):
        product = products[code]
        bags = kg[code] / product.bag_kg
        to_buy = int(bags.to_integral_value(rounding=ROUND_CEILING))
        lines.append(Line(
            product=code,
            kg=kg[code].quantize(Decimal("1"), rounding=ROUND_HALF_UP),
            bags=bags.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
            bags_to_buy=to_buy,
            cost=(product.price_per_bag * to_buy).quantize(Decimal("1"), rounding=ROUND_HALF_UP),
        ))
    return Plan(lines)


def parse_split(text: str) -> dict[str, dict[str, Decimal]]:
    """'basal:N=0.667,P=1,K=1;earthing_up:N=0.333' -> {stage: {nutrient: share}}."""
    stages: dict[str, dict[str, Decimal]] = {}
    for part in filter(None, (text or "").split(";")):
        stage, shares = part.split(":", 1)
        stages[stage.strip()] = {k.strip(): Decimal(v) for k, v in (s.split("=") for s in shares.split(","))}
    return stages


def split_by_stage(dose: Dose, area_ha: Decimal, products: dict[str, Product], phosphate: str,
                   schedule: dict[str, dict[str, Decimal]]) -> dict[str, dict[str, Decimal]]:
    """Product kg per stage, following a cited nutrient split. Each stage's
    products are worked out from that stage's share of each nutrient."""
    out = {}
    for stage, shares in schedule.items():
        part = Dose(dose.n * shares.get("N", ZERO), dose.p2o5 * shares.get("P", ZERO), dose.k2o * shares.get("K", ZERO))
        out[stage] = {code: kg.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                      for code, kg in product_kg(part, area_ha, products, phosphate).items()}
    return out
