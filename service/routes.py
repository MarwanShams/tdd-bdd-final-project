"""Flask routes for the Product Catalog REST API and administration UI."""

from flask import abort, jsonify, request, url_for
from service.models import Product, Category
from service.common import status
from . import app


@app.route('/health')
def healthcheck():
    """Return a simple health status."""
    return jsonify(status=200, message='OK'), status.HTTP_200_OK


@app.route('/')
def index():
    """Serve the product administration interface."""
    return app.send_static_file('index.html')


def check_content_type(content_type):
    """Reject requests without the expected Content-Type."""
    if 'Content-Type' not in request.headers:
        app.logger.error('No Content-Type specified')
        abort(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f'Content-Type must be {content_type}')
    if request.headers['Content-Type'] != content_type:
        app.logger.error('Invalid Content-Type: %s', request.headers['Content-Type'])
        abort(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f'Content-Type must be {content_type}')


@app.route('/products', methods=['POST'])
def create_products():
    """Create a product from the posted JSON data."""
    app.logger.info('Request to create a Product')
    check_content_type('application/json')
    product = Product()
    product.deserialize(request.get_json())
    product.create()
    location_url = url_for('get_products', product_id=product.id, _external=True)
    return jsonify(product.serialize()), status.HTTP_201_CREATED, {'Location': location_url}


@app.route('/products', methods=['GET'])
def list_products():
    """List all products or filter by name, category, or availability."""
    name = request.args.get('name')
    category = request.args.get('category')
    available = request.args.get('available')

    if name:
        products = Product.find_by_name(name)
    elif category:
        try:
            selected_category = Category[category.upper()]
        except KeyError:
            abort(status.HTTP_400_BAD_REQUEST, 'Invalid category')
        products = Product.find_by_category(selected_category)
    elif available is not None:
        if available.lower() not in ('true', 'false'):
            abort(status.HTTP_400_BAD_REQUEST, 'Invalid availability')
        products = Product.find_by_availability(available.lower() == 'true')
    else:
        products = Product.all()

    return jsonify([product.serialize() for product in products]), status.HTTP_200_OK


@app.route('/products/<int:product_id>', methods=['GET'])
def get_products(product_id):
    """Retrieve a product by ID, or return 404 when it does not exist."""
    product = Product.find(product_id)
    if product is None:
        abort(status.HTTP_404_NOT_FOUND, 'Product not found')
    return jsonify(product.serialize()), status.HTTP_200_OK


@app.route('/products/<int:product_id>', methods=['PUT'])
def update_products(product_id):
    """Replace a product's details with submitted JSON data."""
    check_content_type('application/json')
    product = Product.find(product_id)
    if product is None:
        abort(status.HTTP_404_NOT_FOUND, 'Product not found')
    product.deserialize(request.get_json())
    product.update()
    return jsonify(product.serialize()), status.HTTP_200_OK


@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_products(product_id):
    """Remove an existing product."""
    product = Product.find(product_id)
    if product is None:
        abort(status.HTTP_404_NOT_FOUND, 'Product not found')
    product.delete()
    return '', status.HTTP_204_NO_CONTENT
