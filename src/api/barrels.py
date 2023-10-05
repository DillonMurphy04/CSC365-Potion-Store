from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

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
                "SELECT num_red_potions, num_green_potions, num_blue_potions, gold "
                "FROM global_inventory"
                )
                ).first()

    purchase_plan = []
    gold = potions.gold

    if gold < 60:
        return purchase_plan
    
    if gold < 320:
        purch_quant = 1
        size = "MINI"
    elif gold < 800:
        purch_quant = 1
        size = "SMALL"
    else:
        purch_quant = gold // 800
        size = "MEDIUM"

    potion_info = {
        f"{size}_RED_BARREL": float('inf'),
        f"{size}_GREEN_BARREL": float('inf'),
        f"{size}_BLUE_BARREL": float('inf'),
    }

    for barrel in wholesale_catalog:
        if barrel.sku == f"{size}_RED_BARREL":
            potion_info[f"{size}_RED_BARREL"] = barrel.price
        elif barrel.sku == f"{size}_GREEN_BARREL":
            potion_info[f"{size}_GREEN_BARREL"] = barrel.price
        elif barrel.sku == f"{size}_BLUE_BARREL":
            potion_info[f"{size}_BLUE_BARREL"] = barrel.price

    potions_sorted = [
        (potions.num_red_potions, f"{size}_RED_BARREL"),
        (potions.num_blue_potions, f"{size}_BLUE_BARREL"),
        (potions.num_green_potions, f"{size}_GREEN_BARREL"),
    ]

    potions_sorted.sort()

    for quantity, name in potions_sorted:
        price = potion_info[name]
        if gold < 60:
            return purchase_plan
        if quantity < 10 * purch_quant and gold >= price:
            purchase_plan.append({"sku": name, "quantity": purch_quant})
            gold -= price
    
    return purchase_plan
