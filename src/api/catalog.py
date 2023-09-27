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
        red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory")).scalar()

    # Can return a max of 20 items.
    return [
            {
                "sku": "RED_POTION_0",
                "name": "red potion",
                "quantity": 1 if red_potions > 0 else 0,
                "price": 50 if red_potions > 0 else 0,
                "potion_type": [100, 0, 0, 0],
            }
        ]
