"""Behave step for initializing the product catalog from feature tables."""

import requests
from behave import given

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204


@given('the following products')
def step_impl(context):
    """Clear any previous products and load this scenario's initial data."""
    endpoint = f'{context.base_url}/products'
    response = requests.get(endpoint, timeout=20)
    assert response.status_code == HTTP_200_OK, response.text
    for product in response.json():
        response = requests.delete(f"{endpoint}/{product['id']}", timeout=20)
        assert response.status_code == HTTP_204_NO_CONTENT, response.text

    for row in context.table:
        payload = {
            'name': row['name'],
            'description': row['description'],
            'price': row['price'],
            'available': row['available'].strip().lower() == 'true',
            'category': row['category'],
        }
        response = requests.post(endpoint, json=payload, timeout=20)
        assert response.status_code == HTTP_201_CREATED, response.text
