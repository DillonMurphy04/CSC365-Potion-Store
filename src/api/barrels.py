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
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory "
                "SET num_red_ml = num_red_ml + :red_ml, "
                "num_green_ml = num_green_ml + :green_ml, "
                "num_blue_ml = num_blue_ml + :blue_ml, "
                "gold = gold - :red_price - :green_price - :blue_price"
            )
            .params(red_ml=red_ml, green_ml=green_ml, blue_ml=blue_ml, red_price=red_price, green_price=green_price, blue_price=blue_price)
        )

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        potions = connection.execute(
            sqlalchemy.text(
                "SELECT * "
                "FROM global_inventory"
                )
                ).first()
        
        rgb_count = connection.execute(sqlalchemy.text(
                "SELECT "
                "SUM(red_amount * num_potion) AS total_red, "
                "SUM(green_amount * num_potion) AS total_green, "
                "SUM(blue_amount * num_potion) AS total_blue "
                "FROM potions"
            )).first()

    purchase_plan = []
    gold = potions.gold

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

    num_red_potions = rgb_count.total_red / 100
    num_green_potions = rgb_count.total_green / 100
    num_blue_potions = rgb_count.total_blue / 100
    total = num_red_potions + num_green_potions + num_blue_potions

    colors_sorted = []
    if num_red_potions < 200:
        if num_red_potions <= math.ceil((total + 1) / 2):
            colors_sorted.append((num_red_potions, "RED"))
    if num_green_potions < 200:
        if num_green_potions <= math.ceil((total + 1) / 2):
            colors_sorted.append((num_green_potions, "GREEN"))
    if num_blue_potions < 200:
        if num_blue_potions <= math.ceil((total + 1) / 2):
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
