from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        ml = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        potions = connection.execute(sqlalchemy.text("SELECT SUM(potions.num_potion) FROM potions")).scalar()

    return {"number_of_potions": potions, 
            "ml_in_barrels": ml.num_red_ml + ml.num_green_ml + ml.num_blue_ml, 
            "gold": ml.gold}

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print(audit_explanation)

    return "OK"

# To be called once every 3 days (resets potions sold after called)
@router.post("/adjust")
def adjust_price():
    UPPER_PERCENTAGE = 20
    LOWER_PERCENTAGE = 10
    PRICE_INCREASE_AMOUNT = 3
    PRICE_DECREASE_AMOUNT = 3
    MINIMUM_SALES_THRESHOLD = 10

    changes_made = []

    with db.engine.begin() as connection:
        total_sold = connection.execute(
            sqlalchemy.text("SELECT SUM(potions_sold) FROM potions")
        ).scalar()

        if total_sold < MINIMUM_SALES_THRESHOLD:
            return changes_made

        potions_data = connection.execute(
            sqlalchemy.text("SELECT item_sku, potions_sold, cost, num_potion FROM potions")
        )

        for potion in potions_data:
            if potion.num_potion == 0:
                continue

            sales_percentage = (potion.potions_sold / total_sold) * 100

            if sales_percentage >= UPPER_PERCENTAGE and potion.cost < 80:
                new_cost = min(potion.cost + PRICE_INCREASE_AMOUNT, 80)
                connection.execute(
                    sqlalchemy.text(
                        "UPDATE potions SET cost = :new_cost, potions_sold = 0 WHERE item_sku = :item_sku"
                    ).params(new_cost=new_cost, item_sku=potion.item_sku)
                )
                changes_made.append(f"Adjusted price of {potion.item_sku} from {potion.cost} to {new_cost}.")
            elif sales_percentage <= LOWER_PERCENTAGE and potion.cost > 40:
                new_cost = max(potion.cost - PRICE_DECREASE_AMOUNT, 40)
                connection.execute(
                    sqlalchemy.text(
                        "UPDATE potions SET cost = :new_cost, potions_sold = 0 WHERE item_sku = :item_sku"
                    ).params(new_cost=new_cost, item_sku=potion.item_sku)
                )
                changes_made.append(f"Adjusted price of {potion.item_sku} from {potion.cost} to {new_cost}.")
            else:
                connection.execute(
                    sqlalchemy.text(
                        "UPDATE potions SET potions_sold = 0 WHERE item_sku = :item_sku"
                    ).params(item_sku=potion.item_sku)
                )

    return changes_made
