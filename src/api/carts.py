from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class NewCart(BaseModel):
    customer: str


cart_customers = {}

@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    print(new_cart)
    if new_cart.customer in cart_customers:
        customer_id = cart_customers[new_cart.customer]
    else:
        customer_id = len(cart_customers) + 1
        cart_customers[new_cart.customer] = customer_id

    return {"cart_id": customer_id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    return {}


class CartItem(BaseModel):
    quantity: int


cart_items = {}

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    print(f"{cart_id}: {item_sku}")
    print(f"{cart_id}: {cart_item}")

    cart_items[cart_id] = cart_item.quantity

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(f"{cart_id}: {cart_checkout}")
    customer_cart = cart_items.pop(cart_id)
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory "
                "SET num_red_potions = num_red_potions - :bottles, gold = gold + :gold"
            )
            .params(bottles=customer_cart, gold=customer_cart * 50)
        )

    return {"total_potions_bought": customer_cart, "total_gold_paid": customer_cart * 50}
