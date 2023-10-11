from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import math

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

    red = 0
    green = 0
    blue = 0
    with db.engine.begin() as connection:
        for potion in potions_delivered:
            red += potion.potion_type[0] * potion.quantity
            green += potion.potion_type[1] * potion.quantity
            blue += potion.potion_type[2] * potion.quantity
            connection.execute(
                sqlalchemy.text(
                    "UPDATE potions "
                    "SET num_potion = num_potion + :quantity "
                    "WHERE red_amount = :red_amount AND "
                    "green_amount = :green_amount AND "
                    "blue_amount = :blue_amount AND "
                    "dark_amount = :dark_amount"
                )
                .params(
                    quantity=potion.quantity,
                    red_amount=potion.potion_type[0],
                    green_amount=potion.potion_type[1],
                    blue_amount=potion.potion_type[2],
                    dark_amount=potion.potion_type[3]
                )
            )

        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory "
                "SET num_red_ml = num_red_ml - :red_ml, "
                "num_green_ml = num_green_ml - :green_ml, "
                "num_blue_ml = num_blue_ml - :blue_ml"
            )
            .params(
                red_ml=red,
                green_ml=green,
                blue_ml=blue
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

        potions = connection.execute(
            sqlalchemy.text(
                "SELECT * FROM potions ORDER BY num_potion ASC"
                )
                )

    bottle_plan = []

    red = ml.num_red_ml
    green = ml.num_green_ml
    blue = ml.num_blue_ml
    avg_potion = math.ceil((red + green + blue) / 100 / 5)

    for row in potions:
        if red + green + blue < 100:
            return bottle_plan
        possible = min(
            float('inf') if row.red_amount == 0 else red // row.red_amount,
            float('inf') if row.green_amount == 0 else green // row.green_amount,
            float('inf') if row.blue_amount == 0 else blue // row.blue_amount
        )
        num_potion = min(possible, 42 - row.num_potion, avg_potion)
        if num_potion > 0:
            red -= row.red_amount * num_potion
            green -= row.green_amount * num_potion
            blue -= row.blue_amount * num_potion
            bottle_plan.append({
                "potion_type": [row.red_amount, row.green_amount, row.blue_amount, row.dark_amount],
                "quantity": num_potion
            })

    return bottle_plan
