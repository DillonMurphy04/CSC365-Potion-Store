from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from enum import Enum

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """
    print(sort_col.value)
    with db.engine.begin() as connection:
        customer_transactions = connection.execute(
            sqlalchemy.text(
                f"""
                SELECT
                    cle.id AS line_item_id,
                    cle.item_sku,
                    cc.customer AS customer_name,
                    cle.change_gold AS line_item_total,
                    t.created_at AS timestamp
                FROM customer_ledger_entries AS cle
                JOIN cart_customers AS cc ON cle.customer_id = cc.id
                JOIN transactions AS t ON cle.transaction_id = t.id
                ORDER BY {sort_col.value} {sort_order.value}
                LIMIT 5
                """
            )
        )

    items = [row._asdict() for row in customer_transactions]

    return {
        "previous": "",
        "next": "",
        "results": items,
    }


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
        transaction_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO transactions (description, type)
                VALUES (:description, :type)
                RETURNING id
                """
            ).params(description=f"Checkout for cart {cart_id}", type="Checkout")
        ).first().id

        customer_cart = connection.execute(
            sqlalchemy.text(
                """
                WITH cart_details AS (
                    SELECT
                        id AS customer_id,
                        item_sku,
                        quantity
                    FROM cart_items
                    WHERE cart_items.id = :cart_id
                ),
                ledger_insert AS (
                    INSERT INTO customer_ledger_entries (customer_id, transaction_id, item_sku, change_potions, change_gold)
                    SELECT
                        customer_id,
                        :transaction_id,
                        cart_details.item_sku,
                        -quantity,
                        (quantity * potions.cost)
                    FROM cart_details
                    JOIN potions ON cart_details.item_sku = potions.item_sku
                    RETURNING item_sku, change_potions, change_gold
                )
                SELECT
                    SUM(change_potions) AS total_potions_bought,
                    SUM(change_gold) AS total_gold_paid
                FROM ledger_insert
                """
            ).params(cart_id=cart_id, transaction_id=transaction_id)
        ).first()

        connection.execute(
            sqlalchemy.text(
                "DELETE FROM cart_items WHERE id = :cart_id"
            ).params(cart_id=cart_id)
        )

    return {"total_potions_bought": -customer_cart.total_potions_bought, "total_gold_paid": customer_cart.total_gold_paid}
