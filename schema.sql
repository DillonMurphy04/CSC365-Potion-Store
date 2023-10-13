create table
  public.cart_customers (
    id bigint generated by default as identity,
    customer text not null,
    constraint cart_customers_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.cart_items (
    id bigint not null,
    item_sku text not null,
    quantity bigint not null,
    constraint unique_cart_item unique (id, item_sku),
    constraint cart_items_id_fkey foreign key (id) references cart_customers (id),
    constraint cart_items_item_sku_fkey foreign key (item_sku) references potions (item_sku)
  ) tablespace pg_default;

  create table
  public.global_inventory (
    num_red_ml integer not null,
    gold integer not null,
    num_blue_ml integer not null default 0,
    num_green_ml integer not null default 0
  ) tablespace pg_default;

create table
  public.potions (
    item_sku text not null,
    red_amount integer not null default 0,
    blue_amount integer not null default 0,
    green_amount integer not null default 0,
    dark_amount integer not null default 0,
    cost integer not null default 0,
    num_potion integer not null default 0,
    potions_sold integer not null default 0,
    constraint potions_pkey primary key (item_sku)
  ) tablespace pg_default;