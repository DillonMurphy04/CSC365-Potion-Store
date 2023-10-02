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
    for barrel in barrels_delivered:
        if barrel.sku == "SMALL_RED_BARREL":
            red_ml += barrel.ml_per_barrel # * barrel.quantity ??
            red_price += barrel.price # * barrel.quantity ??
            break

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory "
                "SET num_red_ml = num_red_ml + :red_ml, gold = gold - :red_price"
            )
            .params(red_ml=red_ml, red_price=red_price)
        )

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions, gold FROM global_inventory")).first()

    red_price = 0
    for barrel in wholesale_catalog:
        if barrel.sku == "SMALL_RED_BARREL":
            red_price += barrel.price
            break
    
    if (red_potions.num_red_potions < 10 and red_potions.gold >= red_price):
        return [
            {
                "sku": "SMALL_RED_BARREL",
                "quantity": 1,
            }
        ]
    else:
        return []
