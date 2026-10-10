"""Test suite for the product persistence model."""

import logging
import os
import unittest
from decimal import Decimal

from service import app
from service.models import Category, DataValidationError, Product, db
from tests.factories import ProductFactory

DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://postgres:postgres@localhost:5432/postgres')


# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Verify CRUD, database queries, and product validation."""

    @classmethod
    def setUpClass(cls):
        """Initialize a test database once for this suite."""
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Close the database session."""
        db.session.close()

    def setUp(self):
        """Begin each test with an empty catalog."""
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        """Dispose of the active session."""
        db.session.remove()

    def _save_products(self, count):
        """Create a batch of persisted products."""
        products = ProductFactory.create_batch(count)
        for product in products:
            product.id = None
            product.create()
        return products

    def test_create_a_product(self):
        """It should instantiate a Product and print its representation."""
        product = Product(name='Fedora', description='A red hat', price=12.50,
                          available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), '<Product Fedora id=[None]>')
        self.assertIsNone(product.id)
        self.assertEqual(product.name, 'Fedora')
        self.assertEqual(product.description, 'A red hat')
        self.assertEqual(product.price, 12.50)
        self.assertTrue(product.available)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should add one factory product to the database."""
        self.assertEqual(Product.all(), [])
        product = self._save_products(1)[0]
        self.assertIsNotNone(product.id)
        self.assertEqual(len(Product.all()), 1)
        found = Product.all()[0]
        self.assertEqual(found.name, product.name)
        self.assertEqual(found.description, product.description)
        self.assertEqual(Decimal(found.price), product.price)
        self.assertEqual(found.available, product.available)
        self.assertEqual(found.category, product.category)

    def test_read_a_product(self):
        """It should read back the product by its assigned ID."""
        product = self._save_products(1)[0]
        found = Product.find(product.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, product.id)
        self.assertEqual(found.name, product.name)
        self.assertEqual(found.description, product.description)
        self.assertEqual(Decimal(found.price), product.price)
        self.assertEqual(found.available, product.available)
        self.assertEqual(found.category, product.category)

    def test_read_a_product_not_found(self):
        """It should not find a missing product."""
        self.assertIsNone(Product.find(0))

    def test_update_a_product(self):
        """It should persist changes without adding another product."""
        product = self._save_products(1)[0]
        original_id = product.id
        product.description = 'Updated description'
        product.update()
        self.assertEqual(product.id, original_id)
        self.assertEqual(product.description, 'Updated description')
        self.assertEqual(len(Product.all()), 1)
        self.assertEqual(Product.find(original_id).description, 'Updated description')

    def test_update_without_an_id(self):
        """It should reject updates of unsaved products."""
        product = ProductFactory()
        product.id = None
        with self.assertRaises(DataValidationError):
            product.update()

    def test_delete_a_product(self):
        """It should remove a previously saved product."""
        product = self._save_products(1)[0]
        product_id = product.id
        self.assertEqual(len(Product.all()), 1)
        product.delete()
        self.assertEqual(len(Product.all()), 0)
        self.assertIsNone(Product.find(product_id))

    def test_list_all_products(self):
        """It should list all five newly created products."""
        self.assertEqual(len(Product.all()), 0)
        self._save_products(5)
        self.assertEqual(len(Product.all()), 5)

    def test_find_by_name(self):
        """It should find all products with a matching name."""
        products = self._save_products(5)
        name = products[0].name
        expected_count = sum(product.name == name for product in products)
        found = list(Product.find_by_name(name))
        self.assertEqual(len(found), expected_count)
        for product in found:
            self.assertEqual(product.name, name)

    def test_find_by_category(self):
        """It should filter by enumeration category."""
        products = self._save_products(10)
        category = products[0].category
        expected_count = sum(product.category == category for product in products)
        found = list(Product.find_by_category(category))
        self.assertEqual(len(found), expected_count)
        for product in found:
            self.assertEqual(product.category, category)

    def test_find_by_availability(self):
        """It should filter by the available flag."""
        products = self._save_products(10)
        available = products[0].available
        expected_count = sum(product.available == available for product in products)
        found = list(Product.find_by_availability(available))
        self.assertEqual(len(found), expected_count)
        for product in found:
            self.assertEqual(product.available, available)

    def test_find_by_price(self):
        """It should support decimal price queries."""
        products = self._save_products(3)
        price = products[0].price
        found = list(Product.find_by_price(price))
        self.assertTrue(found)
        for product in found:
            self.assertEqual(product.price, price)

    def test_find_by_price_from_string(self):
        """It should parse a string price query."""
        product = self._save_products(1)[0]
        found = list(Product.find_by_price(str(product.price)))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].id, product.id)

    def test_serialize_product(self):
        """It should emit the expected JSON-compatible attributes."""
        product = ProductFactory()
        data = product.serialize()
        self.assertEqual(data['name'], product.name)
        self.assertEqual(data['description'], product.description)
        self.assertEqual(product.price, Decimal(data['price']))
        self.assertEqual(data['available'], product.available)
        self.assertEqual(data['category'], product.category.name)

    def test_deserialize_product(self):
        """It should create a valid product from serialized attributes."""
        sample = ProductFactory().serialize()
        product = Product().deserialize(sample)
        self.assertEqual(product.name, sample['name'])
        self.assertEqual(product.description, sample['description'])
        self.assertEqual(product.price, Decimal(sample['price']))
        self.assertEqual(product.category, Category[sample['category']])
        self.assertEqual(product.available, sample['available'])

    def test_deserialize_missing_attribute(self):
        """It should reject a missing name."""
        data = ProductFactory().serialize()
        del data['name']
        with self.assertRaises(DataValidationError):
            Product().deserialize(data)

    def test_deserialize_bad_category(self):
        """It should reject a non-existent category."""
        data = ProductFactory().serialize()
        data['category'] = 'NOT_A_CATEGORY'
        with self.assertRaises(DataValidationError):
            Product().deserialize(data)

    def test_deserialize_bad_availability(self):
        """It should reject non-boolean availability."""
        data = ProductFactory().serialize()
        data['available'] = 'True'
        with self.assertRaises(DataValidationError):
            Product().deserialize(data)

    def test_deserialize_bad_data(self):
        """It should reject a non-dictionary request body."""
        with self.assertRaises(DataValidationError):
            Product().deserialize(None)
