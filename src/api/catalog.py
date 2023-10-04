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
        potions = connection.execute(sqlalchemy.text("SELECT num_red_potions, num_green_potions, num_blue_potions FROM global_inventory")).first()

    catalog = []
    if potions.num_red_potions > 0:
        # Can return a max of 20 items.
        catalog.append(
            {
                "sku": "RED_POTION_0",
                "name": "red potion",
                "quantity": potions.num_red_potions,
                "price": 50,
                "potion_type": [100, 0, 0, 0],
            }
        )
    if potions.num_green_potions > 0:
        catalog.append(
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": potions.num_green_potions,
                "price": 50,
                "potion_type": [0, 100, 0, 0],
            }
        )
    if potions.num_green_potions > 0:
        catalog.append(
            {
                "sku": "BLUE_POTION_0",
                "name": "blue potion",
                "quantity": potions.num_blue_potions,
                "price": 60,
                "potion_type": [0, 0, 100, 0],
            }
        )

    return catalog
