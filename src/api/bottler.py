from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print(potions_delivered)

    red_bottles = 0
    green_bottles = 0
    blue_bottles = 0
    for potion in potions_delivered:
        if potion.potion_type == [100, 0, 0, 0]:
            red_bottles = potion.quantity
        if potion.potion_type == [0, 100, 0, 0]:
            green_bottles = potion.quantity
        if potion.potion_type == [0, 0, 100, 0]:
            blue_bottles = potion.quantity

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory "
                "SET num_red_potions = num_red_potions + :red_bottles, num_red_ml = num_red_ml - :red_ml, "
                "num_green_potions = num_green_potions + :green_bottles, num_green_ml = num_green_ml - :green_ml, "
                "num_blue_potions = num_blue_potions + :blue_bottles, num_blue_ml = num_blue_ml - :blue_ml"
            )
            .params(
                red_bottles=red_bottles,
                red_ml=red_bottles * 100,
                green_bottles=green_bottles,
                green_ml=green_bottles * 100,
                blue_bottles=blue_bottles,
                blue_ml=blue_bottles * 100
            )
        )

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

    with db.engine.begin() as connection:
        ml = connection.execute(
            sqlalchemy.text(
                "SELECT * FROM global_inventory"
                )
                ).first()
        
    num_red_bottles = ml.num_red_ml // 100
    num_green_bottles = ml.num_green_ml // 100
    num_blue_bottles = ml.num_blue_ml // 100

    num_red_bottles = min(num_red_bottles, 100 - ml.num_red_potions)
    num_green_bottles = min(num_green_bottles, 100 - ml.num_green_potions)
    num_blue_bottles = min(num_blue_bottles, 100 - ml.num_blue_potions)

    bottle_plan = []

    if num_red_bottles > 0:
        bottle_plan.append({"potion_type": [100, 0, 0, 0], "quantity": num_red_bottles})
    if num_green_bottles > 0:
        bottle_plan.append({"potion_type": [0, 100, 0, 0], "quantity": num_green_bottles})
    if num_blue_bottles > 0:
        bottle_plan.append({"potion_type": [0, 0, 100, 0], "quantity": num_blue_bottles})

    return bottle_plan
