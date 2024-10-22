from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.controller import lookup_data
from app.models import BarCodeCache
import openfoodfacts

@pytest.fixture
def session():
    return MagicMock(spec=Session)


def test_lookup_data_cache_hit(session:Session):
    barcode = "123456789"
    cache_data = "Product (Brand) - 100g"
    session.exec.return_value.first.return_value = BarCodeCache(
        barcode=barcode, data=cache_data
    )

    result = lookup_data(session, barcode)

    assert result == cache_data
    session.exec.assert_called_once()
    session.add.assert_not_called()
    session.commit.assert_not_called()


@patch("app.controller.api.product.get")
def test_lookup_data_cache_miss(api_get_mock:openfoodfacts.API, session:Session):
    barcode = "123456789"
    api_data = {"product_name": "Product", "brands": "Brand", "quantity": "100g"}
    api_get_mock.return_value = api_data
    session.exec.return_value.first.return_value = None

    result = lookup_data(session, barcode)

    expected_data_str = "Product (Brand) - 100g"
    assert result == expected_data_str
    session.add.assert_called_once_with(
        BarCodeCache(barcode=barcode, data=expected_data_str)
    )
    session.commit.assert_called_once()


@patch("app.controller.api.product.get")
def test_lookup_data_missing_fields(api_get_mock:openfoodfacts.API, session:Session):
    barcode = "123456789"
    api_data = {"product_name": "Product", "brands": "Brand"}
    api_get_mock.return_value = api_data
    session.exec.return_value.first.return_value = None

    result = lookup_data(session, barcode)

    expected_data_str = "Product (Brand) - -"
    assert result == expected_data_str
    session.add.assert_called_once_with(
        BarCodeCache(barcode=barcode, data=expected_data_str)
    )
    session.commit.assert_called_once()


@patch("app.controller.api.product.get")
def test_lookup_data_api_error(api_get_mock:openfoodfacts.API, session:Session):
    barcode = "123456789"
    api_get_mock.side_effect = ValueError("API error")
    session.exec.return_value.first.return_value = None

    result = lookup_data(session, barcode)

    assert result == ""
    session.add.assert_not_called()
    session.commit.assert_not_called()
