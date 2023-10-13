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


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    print(f"{cart_id}: {item_sku}")
    print(f"{cart_id}: {cart_item}")

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO cart_items (id, item_sku, quantity)
                VALUES (:cart_id, :item_sku, :quantity)
                ON CONFLICT (id, item_sku)
                DO UPDATE SET
                quantity = cart_items.quantity + EXCLUDED.quantity
                """
            ).params(cart_id=cart_id, item_sku=item_sku, quantity=cart_item.quantity)
        )

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(f"{cart_id}: {cart_checkout}")

    with db.engine.begin() as connection:
        customer_cart = connection.execute(
            sqlalchemy.text(
                """
                WITH updated_potions AS (
                    UPDATE potions
                    SET num_potion = num_potion - cart_items.quantity
                    FROM cart_items
                    WHERE cart_items.item_sku = potions.item_sku AND cart_items.id = :cart_id
                    RETURNING cart_items.quantity, potions.cost
                )
                SELECT SUM(quantity) AS total_potions_bought, SUM(quantity * cost) AS total_gold_paid
                FROM updated_potions
                """
            ).params(cart_id=cart_id)).first()
        
        connection.execute(
            sqlalchemy.text(
                "DELETE FROM cart_items WHERE id = :cart_id"
            ).params(cart_id=cart_id)
        )

        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory SET gold = gold + :total_gold_paid"
            ).params(total_gold_paid=customer_cart.total_gold_paid)
        )

    return {"total_potions_bought": customer_cart.total_potions_bought, "total_gold_paid": customer_cart.total_gold_paid}
