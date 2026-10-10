"""Factory for generating realistic fake Product instances in tests."""

# pylint: disable=too-few-public-methods
import factory
from factory.fuzzy import FuzzyChoice, FuzzyDecimal
from service.models import Product, Category


class ProductFactory(factory.Factory):
    """Create fake products for model and API testing."""

    class Meta:
        """Associate this factory with the model."""

        model = Product

    id = factory.Sequence(lambda n: n)
    name = factory.Faker("name")
    description = factory.Faker("text", max_nb_chars=100)
    price = FuzzyDecimal(1.00, 1000.00, 2)
    available = FuzzyChoice([True, False])
    category = FuzzyChoice(list(Category))
