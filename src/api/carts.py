from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from collections import defaultdict

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class NewCart(BaseModel):
    customer: str


@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    print(new_cart)

    with db.engine.begin() as connection:   
        customer_id = connection.execute(
            sqlalchemy.text("SELECT id FROM cart_customers WHERE customer = :customer")
            .params(customer=new_cart.customer)
        ).scalar()    

        if customer_id:
            return {"cart_id": customer_id}
        else:
            customer_id = connection.execute(
                sqlalchemy.text(
                    "INSERT INTO cart_customers (customer) "
                    "VALUES (:customer) "
                    "RETURNING id"
                    ).params(customer=new_cart.customer)
                    ).scalar()

    return {"cart_id": customer_id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    return {}


class CartItem(BaseModel):
    quantity: int


cart_items = defaultdict(dict)

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    print(f"{cart_id}: {item_sku}")
    print(f"{cart_id}: {cart_item}")

    cart_items[cart_id][item_sku] = cart_item.quantity

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(f"{cart_id}: {cart_checkout}")
    customer_cart = cart_items.pop(cart_id)
    
    total_potions_bought = 0
    total_gold_paid = 0

    with db.engine.begin() as connection:
        for item_sku, quantity in customer_cart.items():  
            if item_sku == "blue_potions":
                cost = 70
            else:
                cost = 60
            connection.execute(
                sqlalchemy.text(
                    "UPDATE global_inventory "
                    f"SET num_{item_sku} = num_{item_sku} - :quantity, gold = gold + :gold"
                )
                .params(quantity=quantity, gold=quantity * cost)
            )
            total_potions_bought += quantity
            total_gold_paid += quantity * cost

    return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}
