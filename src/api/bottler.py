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

    red_bottles = None
    for potion in potions_delivered:
        if potion.potion_type == [100, 0, 0, 0]:
            red_bottles = potion.quantity

    if red_bottles:
        with db.engine.begin() as connection:
            connection.execute(
                sqlalchemy.text(
                    "UPDATE global_inventory "
                    "SET num_red_potions = num_red_potions + :red_bottles, num_red_ml = num_red_ml - :red_ml"
                )
                .params(red_bottles=red_bottles, red_ml=red_bottles*100)
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
        red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar()
    num_bottles = red_ml // 100
    return [
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": num_bottles,
            }
        ]
