"""Unit tests for the Flask REST API for products."""

import logging
import os
from decimal import Decimal
from urllib.parse import quote_plus
from unittest import TestCase

from service import app
from service.common import status
from service.models import Category, Product, db, init_db
from tests.factories import ProductFactory

DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://postgres:postgres@localhost:5432/postgres')
BASE_URL = '/products'


# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Cover standard routes, filters, HTTP errors, and validation."""

    @classmethod
    def setUpClass(cls):
        """Prepare the test application."""
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Close the database session."""
        db.session.close()

    def setUp(self):
        """Prepare an API client and clear the database."""
        self.client = app.test_client()
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        """Discard the active database session."""
        db.session.remove()

    def _create_products(self, count=1):
        """Persist a batch via POST endpoints and return factory objects."""
        products = []
        for _ in range(count):
            product = ProductFactory()
            response = self.client.post(BASE_URL, json=product.serialize())
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            product.id = response.get_json()['id']
            products.append(product)
        return products

    def get_product_count(self):
        """Return the count reported by the list endpoint."""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return len(response.get_json())

    def _assert_product_data(self, data, product):
        """Compare JSON response to all key product attributes."""
        self.assertEqual(data['id'], product.id)
        self.assertEqual(data['name'], product.name)
        self.assertEqual(data['description'], product.description)
        self.assertEqual(Decimal(data['price']), product.price)
        self.assertEqual(data['available'], product.available)
        self.assertEqual(data['category'], product.category.name)

    def test_index(self):
        """It should return the existing administration home page."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b'Product Catalog Administration', response.data)

    def test_health(self):
        """It should report a healthy service."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()['message'], 'OK')

    def test_create_product(self):
        """It should create a new product and return its URL."""
        product = ProductFactory()
        response = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product.id = response.get_json()['id']
        self._assert_product_data(response.get_json(), product)
        location = response.headers.get('Location')
        self.assertIsNotNone(location)
        retrieved = self.client.get(location)
        self.assertEqual(retrieved.status_code, status.HTTP_200_OK)
        self._assert_product_data(retrieved.get_json(), product)

    def test_create_product_with_no_name(self):
        """It should reject a missing required attribute."""
        product = ProductFactory().serialize()
        del product['name']
        response = self.client.post(BASE_URL, json=product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should reject a POST without JSON Content-Type."""
        response = self.client.post(BASE_URL, data='bad data')
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should reject non-JSON Content-Type."""
        response = self.client.post(BASE_URL, data={}, content_type='plain/text')
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        """It should read an existing product by ID."""
        product = self._create_products()[0]
        response = self.client.get(f'{BASE_URL}/{product.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._assert_product_data(response.get_json(), product)

    def test_get_product_not_found(self):
        """It should return 404 when the product is missing."""
        response = self.client.get(f'{BASE_URL}/0')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product(self):
        """It should modify one product without creating a duplicate."""
        product = self._create_products()[0]
        product.description = 'Updated product description'
        response = self.client.put(f'{BASE_URL}/{product.id}', json=product.serialize())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._assert_product_data(response.get_json(), product)
        self.assertEqual(self.get_product_count(), 1)
        response = self.client.get(f'{BASE_URL}/{product.id}')
        self.assertEqual(response.get_json()['description'], product.description)

    def test_update_product_not_found(self):
        """It should reject attempts to update a non-existent product."""
        response = self.client.put(f'{BASE_URL}/0', json=ProductFactory().serialize())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product_without_content_type(self):
        """It should reject a PUT without JSON Content-Type."""
        product = self._create_products()[0]
        response = self.client.put(f'{BASE_URL}/{product.id}', data='bad data')
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_delete_product(self):
        """It should delete a product and return HTTP 204."""
        product = self._create_products()[0]
        self.assertEqual(self.get_product_count(), 1)
        response = self.client.delete(f'{BASE_URL}/{product.id}')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.get_product_count(), 0)

    def test_delete_product_not_found(self):
        """It should return 404 when deleting an absent product."""
        response = self.client.delete(f'{BASE_URL}/0')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_all_products(self):
        """It should return a list of all persisted products."""
        self.assertEqual(self.get_product_count(), 0)
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.get_json()), 5)

    def test_list_by_name(self):
        """It should filter catalog records by exact name."""
        products = self._create_products(5)
        name = products[0].name
        expected = sum(product.name == name for product in products)
        response = self.client.get(f'{BASE_URL}?name={quote_plus(name)}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.get_json()), expected)
        for product in response.get_json():
            self.assertEqual(product['name'], name)

    def test_list_by_category(self):
        """It should filter catalog records by Category."""
        products = self._create_products(10)
        category = products[0].category
        expected = sum(product.category == category for product in products)
        response = self.client.get(f'{BASE_URL}?category={category.name}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.get_json()), expected)
        for product in response.get_json():
            self.assertEqual(product['category'], category.name)

    def test_list_by_availability(self):
        """It should filter the catalog by available true or false."""
        products = self._create_products(10)
        availability = products[0].available
        expected = sum(product.available == availability for product in products)
        response = self.client.get(f'{BASE_URL}?available={str(availability).lower()}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.get_json()), expected)
        for product in response.get_json():
            self.assertEqual(product['available'], availability)

    def test_list_by_available_false(self):
        """It should not treat the string false as a truthy boolean."""
        product = ProductFactory(available=False)
        response = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(f'{BASE_URL}?available=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.get_json()), 1)
        self.assertFalse(response.get_json()[0]['available'])

    def test_list_by_unknown_category(self):
        """It should reject unknown category filters with 400."""
        response = self.client.get(f'{BASE_URL}?category=FAKE_CATEGORY')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_by_invalid_availability(self):
        """It should reject non-boolean availability filters."""
        response = self.client.get(f'{BASE_URL}?available=sometimes')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_by_unknown_name(self):
        """It should return an empty list for an unknown name."""
        self._create_products(3)
        response = self.client.get(f'{BASE_URL}?name={quote_plus("NOT_A_PRODUCT_9282")}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    def test_method_not_allowed(self):
        """It should reject unsupported HTTP methods with 405."""
        response = self.client.put(BASE_URL, json=ProductFactory().serialize())
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_categories_are_serialized_as_strings(self):
        """It should preserve the enum name through JSON serialization."""
        product = ProductFactory(category=Category.TOOLS)
        response = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(response.get_json()['category'], 'TOOLS')
