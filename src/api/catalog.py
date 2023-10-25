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
            sqlalchemy.text("""
                WITH potions_count AS (
                    SELECT 
                        potions.item_sku, 
                        potions.cost,
                        potions.red_amount,
                        potions.green_amount,
                        potions.blue_amount,
                        potions.dark_amount,
                        COALESCE(
                            (SELECT SUM(change_potions) FROM potion_ledger_entries WHERE item_sku = potions.item_sku), 
                            0
                        ) +
                        COALESCE(
                            (SELECT SUM(change_potions) FROM customer_ledger_entries WHERE item_sku = potions.item_sku), 
                            0
                        ) as num_potion
                    FROM potions
                )
                SELECT *
                FROM potions_count
                WHERE num_potion > 0
                ORDER BY num_potion ASC, RANDOM()
                LIMIT 6;
            """)
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
