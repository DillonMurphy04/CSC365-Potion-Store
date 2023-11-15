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
    dark_ml = 0
    dark_price = 0
    for barrel in barrels_delivered:
        parts = barrel.sku.split('_')
        color = parts[1]
        if color == "RED":
            red_ml += barrel.ml_per_barrel * barrel.quantity
            red_price += barrel.price * barrel.quantity
        elif color == 'GREEN':
            green_ml += barrel.ml_per_barrel * barrel.quantity
            green_price += barrel.price * barrel.quantity
        elif color == 'BLUE':
            blue_ml += barrel.ml_per_barrel * barrel.quantity
            blue_price += barrel.price * barrel.quantity
        elif color == 'DARK':
            dark_ml += barrel.ml_per_barrel * barrel.quantity
            dark_price += barrel.price * barrel.quantity

    with db.engine.begin() as connection:
        transaction_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO transactions (description, type)
                VALUES (:description, :type)
                RETURNING id
                """
            ).params(description=f"Buying Red: {red_ml} ml, Green: {green_ml} ml, Blue: {blue_ml} ml, Dark: {dark_ml} ml", type="Barreler")
        ).first().id

        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO inventory_ledger_entries (transaction_id, change_gold, change_red, change_green, change_blue, change_dark)
                VALUES (:transaction_id, -:total_cost, :red_ml, :green_ml, :blue_ml, :dark_ml)
                """
            )
            .params(transaction_id=transaction_id,
                    total_cost=red_price+green_price+blue_price+dark_price,
                    red_ml=red_ml,
                    green_ml=green_ml,
                    blue_ml=blue_ml,
                    dark_ml=dark_ml)
        )

    return "OK"

def get_desired_size_for_color(gold, ml_color):
    """Returns the desired sizes based on gold and current ml of the color"""
    desired_size = []
    purch_quant = 1

    if gold > 1500:
        if ml_color < 10:
            desired_size.extend(["LARGE", "MEDIUM", "SMALL", "MINI"])
            purch_quant = max(1, min(gold // 2550, (200 - ml_color) // 25))
        elif ml_color < 20:
            desired_size.extend(["LARGE", "MEDIUM", "SMALL"])
            purch_quant = max(1, min(gold // 2550, (200 - ml_color) // 25))
        elif ml_color < 100:
            desired_size.extend(["LARGE", "MEDIUM"])
            purch_quant = max(1, min(gold // 2550, (200 - ml_color) // 25))
        else:
            desired_size.extend(["LARGE"])
            purch_quant = max(1, min(4, gold // 2550))
    elif gold > 800:
        if ml_color < 10:
            desired_size.extend(["MEDIUM", "SMALL", "MINI"])
        elif ml_color < 20:
            desired_size.extend(["MEDIUM", "SMALL"])
        elif ml_color < 100:
            desired_size.extend(["MEDIUM"])
    elif gold > 320:
        if ml_color < 10:
            desired_size.extend(["SMALL", "MINI"])
        elif ml_color < 20:
            desired_size.extend(["SMALL"])
    else:
        desired_size.extend(["MINI"])

    return desired_size, purch_quant

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    # return []

    with db.engine.begin() as connection:
        inventory = connection.execute(
            sqlalchemy.text(
                """
                WITH combined_ledgers AS (
                    SELECT change_gold, change_red, change_green, change_blue, change_dark
                    FROM inventory_ledger_entries
                    UNION ALL
                    SELECT 0 AS change_gold, change_red, change_green, change_blue, change_dark
                    FROM potion_ledger_entries
                )
                SELECT
                    COALESCE(SUM(change_gold), 0) AS gold,
                    COALESCE(SUM(change_red), 0) AS num_red_ml,
                    COALESCE(SUM(change_green), 0) AS num_green_ml,
                    COALESCE(SUM(change_blue), 0) AS num_blue_ml,
                    COALESCE(SUM(change_dark), 0) AS num_dark_ml
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
                    COALESCE(SUM(potions.dark_amount * customer_ledger_entries.change_potions), 0) AS total_dark,
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
                    COALESCE(SUM(potions.blue_amount * potion_ledger_entries.change_potions), 0) AS total_blue,
                    COALESCE(SUM(potions.dark_amount * potion_ledger_entries.change_potions), 0) AS total_dark
                FROM public.potion_ledger_entries
                JOIN potions ON potion_ledger_entries.item_sku = potions.item_sku
                """
            )
        ).first()

    bottled_red_ml = customer_ml.total_red + bottled_ml.total_red
    bottled_green_ml = customer_ml.total_green + bottled_ml.total_green
    bottled_blue_ml = customer_ml.total_blue + bottled_ml.total_blue
    bottled_dark_ml = customer_ml.total_dark + bottled_ml.total_dark

    purchase_plan = []
    gold = inventory.gold + customer_ml.gold

    if gold < 60:
        return purchase_plan

    potion_info = defaultdict(dict)

    offered_colors = set()
    for barrel in wholesale_catalog:
        parts = barrel.sku.split('_')
        color = parts[1]
        size = parts[0]
        potion_info[size][color] = (barrel.price, barrel.quantity)
        offered_colors.add(color)

    colors_sorted = []

    num_red_potions = bottled_red_ml / 100
    num_green_potions = bottled_green_ml / 100
    num_blue_potions = bottled_blue_ml / 100
    num_dark_potions = bottled_dark_ml / 100
    ml_red = inventory.num_red_ml / 100
    ml_green = inventory.num_green_ml / 100
    ml_blue = inventory.num_blue_ml / 100
    ml_dark = inventory.num_dark_ml / 100
    threshold = math.ceil((ml_red + ml_green + ml_blue + ml_dark) / 2) + 1

    colors_sorted = []
    current_colors = set()
    if ml_red < 100 and "RED" in offered_colors:
        if ml_red <= threshold:
            colors_sorted.append((num_red_potions, "RED"))
            current_colors.add("RED")

    # if ml_green < 200 and "GREEN" in offered_colors:
    #     if ml_green <= threshold:
    #         colors_sorted.append((num_green_potions, "GREEN"))
    #         current_colors.add("GREEN")

    # if ml_blue < 200 and "BLUE" in offered_colors:
    #     if ml_blue <= threshold:
    #         colors_sorted.append((num_blue_potions, "BLUE"))
    #         current_colors.add("BLUE")

    # if ml_dark < 200 and "DARK" in offered_colors:
    #     if ml_dark <= threshold:
    #         colors_sorted.append((num_dark_potions, "DARK"))
    #         current_colors.add("DARK")

    color_weights = {"DARK": 4, "RED": 3, "GREEN": 2, "BLUE": 1}
    colors_sorted.sort(key=lambda x: (x[0], -color_weights[x[1]]))
    # colors_sorted.sort()

    used_colors = set()

    money_spent = 0

    desired_sizes_dict = {}

    for quantity, color in colors_sorted:
        desired_sizes_for_color, purch_quant = get_desired_size_for_color(gold, eval(f"ml_{color.lower()}"))
        num_available_sizes = len(desired_sizes_for_color)
        for index, size in enumerate(desired_sizes_for_color):
            if size not in desired_sizes_dict:
                desired_sizes_dict[size] = []
            desired_sizes_dict[size].append((color, quantity, purch_quant, num_available_sizes - index))

    sizes_order = ["LARGE", "MEDIUM"]

    for size in sizes_order:
        if size not in desired_sizes_dict:
            continue

        for color, quantity, purch_quant, remaining_sizes in desired_sizes_dict[size]:
            if remaining_sizes == 1:
                current_colors.discard(color)
            if color in used_colors:
                continue
            if size not in potion_info or color not in potion_info[size]:
                continue

            price, barrel_quantity = potion_info[size][color]
            purchase_quantity = min(purch_quant, barrel_quantity, 2)

            if gold < 60:
                return purchase_plan
            if gold >= price:
                used_colors.add(color)
                money_spent += price * purchase_quantity
                purchase_plan.append({"sku": f"{size}_{color}_BARREL", "quantity": int(purchase_quantity)})
                gold -= price * purchase_quantity

            if len(used_colors) >= len(current_colors):
                if gold > money_spent:
                    money_spent = 0
                    used_colors = set()
                else:
                    return purchase_plan

    return purchase_plan