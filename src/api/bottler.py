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

    with db.engine.begin() as connection:
        total_potions_bottled = sum([potion.quantity for potion in potions_delivered])

        transaction_id = connection.execute(
            sqlalchemy.text(
                "INSERT INTO transactions (description, type) VALUES (:description, :transaction_type) RETURNING id"
            ).params(
                description=f"Bottled {total_potions_bottled} potions",
                transaction_type="Bottler"
            )
        ).first().id

        for potion in potions_delivered:
            change_red_ml = - (potion.potion_type[0] * potion.quantity)
            change_green_ml = - (potion.potion_type[1] * potion.quantity)
            change_blue_ml = - (potion.potion_type[2] * potion.quantity)
            change_dark_ml = - (potion.potion_type[3] * potion.quantity)

            item_sku = connection.execute(
                sqlalchemy.text(
                    "SELECT item_sku FROM potions WHERE "
                    "red_amount = :red_amount AND "
                    "green_amount = :green_amount AND "
                    "blue_amount = :blue_amount AND "
                    "dark_amount = :dark_amount"
                ).params(
                    red_amount=potion.potion_type[0],
                    green_amount=potion.potion_type[1],
                    blue_amount=potion.potion_type[2],
                    dark_amount=potion.potion_type[3]
                )
            ).first().item_sku

            connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO potion_ledger_entries (
                        transaction_id,
                        item_sku,
                        change_potions,
                        change_red,
                        change_green,
                        change_blue,
                        change_dark
                    )
                    VALUES (:transaction_id, :item_sku, :change_potions, :change_red, :change_green, :change_blue, :change_dark)
                    """
                )
                .params(
                    transaction_id=transaction_id,
                    item_sku=item_sku,
                    change_potions=potion.quantity,
                    change_red=change_red_ml,
                    change_green=change_green_ml,
                    change_blue=change_blue_ml,
                    change_dark=change_dark_ml
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
                """
                WITH combined_ledgers AS (
                    SELECT change_red, change_green, change_blue, change_dark FROM inventory_ledger_entries
                    UNION ALL
                    SELECT change_red, change_green, change_blue, change_dark FROM potion_ledger_entries
                )
                SELECT
                    COALESCE(SUM(change_red), 0) AS num_red_ml,
                    COALESCE(SUM(change_green), 0) AS num_green_ml,
                    COALESCE(SUM(change_blue), 0) AS num_blue_ml,
                    COALESCE(SUM(change_dark), 0) AS num_dark_ml
                FROM combined_ledgers
                """
            )
        ).first()


        potions = connection.execute(
            sqlalchemy.text(
                """
                WITH combined_ledgers AS (
                    SELECT
                        item_sku,
                        COALESCE(SUM(change_potions), 0) AS total_potions
                    FROM (
                        SELECT item_sku, change_potions FROM customer_ledger_entries
                        UNION ALL
                        SELECT item_sku, change_potions FROM potion_ledger_entries
                    ) AS temp
                    GROUP BY item_sku
                )
                SELECT
                    potions.item_sku,
                    potions.red_amount,
                    potions.green_amount,
                    potions.blue_amount,
                    potions.dark_amount,
                    COALESCE(combined_ledgers.total_potions, 0) AS total_potions
                FROM potions
                LEFT JOIN combined_ledgers ON potions.item_sku = combined_ledgers.item_sku
                ORDER BY COALESCE(combined_ledgers.total_potions, 0) ASC
                """
            )
        ).fetchall()

    sum_potions = sum([row.total_potions for row in potions])

    bottle_plan = []

    red = ml.num_red_ml
    green = ml.num_green_ml
    blue = ml.num_blue_ml
    dark = ml.num_dark_ml

    for row in potions:
        if row.item_sku == "teal_potions":
            continue

        if red + green + blue + dark < 100:
            return bottle_plan

        # if row.total_potions > math.ceil((sum_potions + 1) / 5):
        #     continue

        possible = min(
            float('inf') if row.red_amount == 0 else red // row.red_amount,
            float('inf') if row.green_amount == 0 else green // row.green_amount,
            float('inf') if row.blue_amount == 0 else blue // row.blue_amount,
            float('inf') if row.dark_amount == 0 else dark // row.dark_amount
        )
        num_potion = min(possible, 60 - row.total_potions)
        if num_potion > 0:
            red -= row.red_amount * num_potion
            green -= row.green_amount * num_potion
            blue -= row.blue_amount * num_potion
            dark -= row.dark_amount * num_potion
            bottle_plan.append({
                "potion_type": [row.red_amount, row.green_amount, row.blue_amount, row.dark_amount],
                "quantity": num_potion
            })

    return bottle_plan
