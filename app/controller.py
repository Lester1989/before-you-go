import openfoodfacts
from sqlmodel import Session, select

from app.models import BarCodeCache

api = openfoodfacts.API(user_agent="BeforeYouGo/0.1")


def lookup_data(session: Session, barcode: str):
    if cache := session.exec(
        select(BarCodeCache).where(BarCodeCache.barcode == barcode)
    ).first():
        return cache.data
    # Call external API
    try:
        if data := api.product.get(
            code=barcode, fields=["product_name", "quantity", "brands"]
        ):
            data_str = f'{data["product_name"]} ({data["brands"]}) - {data["quantity"]}'
            session.add(BarCodeCache(barcode=barcode, data=data_str))
            session.commit()
            return data_str
    except ValueError as e:
        print(e)
    return ""
