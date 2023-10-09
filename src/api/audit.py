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