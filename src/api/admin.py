from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

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
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                DELETE FROM customer_ledger_entries;
                DELETE FROM potion_ledger_entries;
                DELETE FROM inventory_ledger_entries;
                DELETE FROM cart_items;
                DELETE FROM cart_customers;
                DELETE FROM transactions;
                """
            )
        )

        transaction_id = connection.execute(
            sqlalchemy.text(
                "INSERT INTO transactions (type, description) VALUES ('Reset', 'Game Reset') RETURNING id"
            )
        ).first().id

        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO inventory_ledger_entries (transaction_id, change_gold, change_red, change_green, change_blue)
                VALUES (:transaction_id, 100, 0, 0, 0)
                """
            )
            .params(transaction_id=transaction_id)
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
