from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT * FROM potions")
        )

    catalog = []
    for row in result:
        if row.num_potion > 0:
            catalog.append(
                {
                    "sku": row.item_sku,
                    "name": f"{row.item_sku.replace('_', ' ')}",
                    "quantity": row.num_potion,
                    "price": row.cost,
                    "potion_type": [row.red_amount, row.green_amount, row.blue_amount, row.dark_amount],
                }
            )
    return catalog