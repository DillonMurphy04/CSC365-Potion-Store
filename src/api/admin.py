from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api.carts import cart_items

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    cart_items.clear()
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                "DELETE FROM cart_customers"
            )
        )
 
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory "
                "SET num_red_potions = 0, num_red_ml = 0, "
                "num_blue_potions = 0, num_blue_ml = 0, "
                "num_green_potions = 0, num_green_ml = 0, gold = 100"
            )
        )

    return "OK"


@router.get("/shop_info/")
def get_shop_info():
    """ """
    # TODO: Change me!
    return {
        "shop_name": "Dillon's Dandy Boutique",
        "shop_owner": "Dillon Murphy",
    }

