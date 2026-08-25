import asyncio

from faker import Faker

from app.db.database import AsyncSessionLocal
from app.models.products import Product
from app.utils.logger import logger

fake = Faker()

async def seed_products():
    async with AsyncSessionLocal() as session:
        products = []

        for _ in range(50):
            stock_quantity=fake.random_int(min=1, max=100)
            product = Product(
                title=fake.catch_phrase(),
                description=fake.text(max_nb_chars=150),
                image_url=None,
                price=fake.random_int(min=100, max=10000),
                in_stock=stock_quantity > 0,
                stock_quantity=stock_quantity
            )
            products.append(product)

        session.add_all(products)
        await session.commit()
    return {"message": "50 products seeded successfully"}


if __name__ == "__main__":
    output = asyncio.run(seed_products())
    logger.info(output)
