import math
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from collections import defaultdict

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    print(barrels_delivered)

    red_ml = 0
    red_price = 0
    green_ml = 0
    green_price = 0
    blue_ml = 0
    blue_price = 0
    for barrel in barrels_delivered:
        parts = barrel.sku.split('_')
        color = parts[1]
        if color == "RED":
            red_ml += barrel.ml_per_barrel * barrel.quantity
            red_price += barrel.price * barrel.quantity
        if color == 'GREEN':
            green_ml += barrel.ml_per_barrel * barrel.quantity
            green_price += barrel.price * barrel.quantity
        if color == 'BLUE':
            blue_ml += barrel.ml_per_barrel * barrel.quantity
            blue_price += barrel.price * barrel.quantity

    with db.engine.begin() as connection:
        transaction_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO transactions (description, type)
                VALUES (:description, :type)
                RETURNING id
                """
            ).params(description=f"Buying Red: {red_ml} ml, Green: {green_ml} ml, Blue: {blue_ml} ml", type="Barreler")
        ).first().id

        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO inventory_ledger_entries (transaction_id, change_gold, change_red, change_green, change_blue)
                VALUES (:transaction_id, -:total_cost, :red_ml, :green_ml, :blue_ml)
                """
            )
            .params(transaction_id=transaction_id,
                    total_cost=red_price+green_price+blue_price,
                    red_ml=red_ml,
                    green_ml=green_ml,
                    blue_ml=blue_ml)
        )

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        inventory = connection.execute(
            sqlalchemy.text(
                """
                WITH combined_ledgers AS (
                    SELECT change_gold, change_red, change_green, change_blue
                    FROM inventory_ledger_entries
                    UNION ALL
                    SELECT 0 AS change_gold, change_red, change_green, change_blue
                    FROM potion_ledger_entries
                )
                SELECT
                    COALESCE(SUM(change_gold), 0) AS gold,
                    COALESCE(SUM(change_red), 0) AS num_red_ml,
                    COALESCE(SUM(change_green), 0) AS num_green_ml,
                    COALESCE(SUM(change_blue), 0) AS num_blue_ml
                FROM combined_ledgers
                """
            )
        ).first()

        customer_ml = connection.execute(
            sqlalchemy.text(
                """
                SELECT
                    COALESCE(SUM(potions.red_amount * customer_ledger_entries.change_potions), 0) AS total_red,
                    COALESCE(SUM(potions.green_amount * customer_ledger_entries.change_potions), 0) AS total_green,
                    COALESCE(SUM(potions.blue_amount * customer_ledger_entries.change_potions), 0) AS total_blue,
                    COALESCE(SUM(change_gold), 0) AS gold
                FROM customer_ledger_entries
                JOIN potions ON customer_ledger_entries.item_sku = potions.item_sku
                """
            )
        ).first()

        bottled_ml = connection.execute(
            sqlalchemy.text(
                """
                SELECT
                    COALESCE(SUM(potions.red_amount * potion_ledger_entries.change_potions), 0) AS total_red,
                    COALESCE(SUM(potions.green_amount * potion_ledger_entries.change_potions), 0) AS total_green,
                    COALESCE(SUM(potions.blue_amount * potion_ledger_entries.change_potions), 0) AS total_blue
                FROM public.potion_ledger_entries
                JOIN potions ON potion_ledger_entries.item_sku = potions.item_sku
                """
            )
        ).first()

    bottled_red_ml = customer_ml.total_red + bottled_ml.total_red
    bottled_green_ml = customer_ml.total_green + bottled_ml.total_green
    bottled_blue_ml = customer_ml.total_blue + bottled_ml.total_blue

    purchase_plan = []
    gold = inventory.gold + customer_ml.gold

    if gold < 60:
        return purchase_plan

    desired_size = []
    if gold > 1500:
        purch_quant = gold // 1500
        desired_size.extend(["LARGE", "MEDIUM", "SMALL", "MINI"])
    elif gold > 800:
        purch_quant = 1
        desired_size.extend(["MEDIUM", "SMALL", "MINI"])
    elif gold > 320:
        purch_quant = 1
        desired_size.extend(["SMALL", "MINI"])
    else:
        purch_quant = 1
        desired_size.append("MINI")

    potion_info = defaultdict(dict)

    for barrel in wholesale_catalog:
        parts = barrel.sku.split('_')
        color = parts[1]
        size = parts[0]
        potion_info[size][color] = (barrel.price, barrel.quantity)

    colors_sorted = []

    num_red_potions = bottled_red_ml / 100
    num_green_potions = bottled_green_ml / 100
    num_blue_potions = bottled_blue_ml / 100
    ml_red = inventory.num_red_ml / 100
    ml_green = inventory.num_green_ml / 100
    ml_blue = inventory.num_blue_ml / 100
    threshold = math.ceil((ml_red + ml_green + ml_blue) / 2) + 1

    colors_sorted = []
    if num_red_potions < 200:
        if ml_red <= threshold:
            colors_sorted.append((num_red_potions, "RED"))
    if num_green_potions < 200:
        if ml_green <= threshold:
            colors_sorted.append((num_green_potions, "GREEN"))
    if num_blue_potions < 200:
        if ml_blue <= threshold:
            colors_sorted.append((num_blue_potions, "BLUE"))

    color_weights = {"RED": 3, "GREEN": 2, "BLUE": 1}
    colors_sorted.sort(key=lambda x: (x[0], -color_weights[x[1]]))
    # colors_sorted.sort()

    used_colors = set()

    money_spent = 0

    for size in desired_size:
        if size not in potion_info:
            continue
        for quantity, color in colors_sorted:
            if color not in potion_info[size] or color in used_colors:
                continue
            price, barrel_quantity = potion_info[size][color]
            if gold < 60:
                return purchase_plan
            purchase_quantity = min(purch_quant, barrel_quantity)
            if quantity < 10 * purch_quant and gold >= price:
                used_colors.add(color)
                money_spent += price * purchase_quantity
                purchase_plan.append({"sku": f"{size}_{color}_BARREL", "quantity": purchase_quantity})
                gold -= price * purchase_quantity

            if len(used_colors) == len(colors_sorted):
                if gold > money_spent:
                    money_spent = 0
                    used_colors = set()
                else:
                    return purchase_plan

    return purchase_plan
