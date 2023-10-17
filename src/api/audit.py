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

        customer_potions = connection.execute(
            sqlalchemy.text(
                """
                SELECT
                    COALESCE(SUM(change_potions), 0) AS total_potions,
                    COALESCE(SUM(change_gold), 0) AS gold
                FROM customer_ledger_entries
                """
            )
        ).first()

        bottled_potions = connection.execute(
            sqlalchemy.text(
                """
                SELECT
                    COALESCE(SUM(change_potions), 0) AS total_potions
                FROM potion_ledger_entries
                """
            )
        ).first()

    gold = customer_potions.gold + inventory.gold
    potions = customer_potions.total_potions + bottled_potions.total_potions

    return {"number_of_potions": potions, 
            "ml_in_barrels": inventory.num_red_ml + inventory.num_green_ml + inventory.num_blue_ml, 
            "gold": gold}

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
