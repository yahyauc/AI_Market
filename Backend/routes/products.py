from flask import Blueprint, request, jsonify, current_app
from models import db
from models.product import Product
from models.zone import Zone
import os
import uuid

products_bp = Blueprint("products", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Upload image ─────────────────────────────────────────────────
@products_bp.route("/products/upload-image", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, webp, gif"}), 400

    # Max size 5MB
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > 5 * 1024 * 1024:
        return jsonify({"error": "File too large. Max 5MB"}), 400

    # Generate unique filename
    ext      = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    uploads_dir = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file.save(os.path.join(uploads_dir, filename))

    image_url = f"http://127.0.0.1:5000/uploads/{filename}"
    return jsonify({"message": "Image uploaded", "image_url": image_url}), 201


# ── Get all products ─────────────────────────────────────────────
@products_bp.route("/products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    search   = request.args.get("search", "").strip()

    query = Product.query
    if category: query = query.filter_by(category=category)
    if search:   query = query.filter(Product.name.ilike(f"%{search}%"))

    products = query.order_by(Product.name).all()
    return jsonify([p.to_dict() for p in products]), 200


# ── Get categories ────────────────────────────────────────────────
@products_bp.route("/products/categories", methods=["GET"])
def get_categories():
    rows = db.session.query(Product.category).distinct().all()
    return jsonify([r[0] for r in rows]), 200


# ── Get single product ────────────────────────────────────────────
@products_bp.route("/products/<int:pid>", methods=["GET"])
def get_product(pid):
    p = Product.query.get_or_404(pid)
    return jsonify(p.to_dict()), 200


# ── Add product ───────────────────────────────────────────────────
@products_bp.route("/products", methods=["POST"])
def add_product():
    data     = request.get_json()
    name     = data.get("name", "").strip()
    category = data.get("category", "").strip()
    price    = data.get("price")
    stock    = data.get("stock")
    zone_id  = data.get("zone_id")

    if not name or not category or price is None or stock is None:
        return jsonify({"error": "name, category, price and stock are required"}), 400

    if float(price) < 0 or int(stock) < 0:
        return jsonify({"error": "Price and stock must be positive"}), 400

    # Validate zone capacity if zone_id provided
    if zone_id:
        zone = Zone.query.get(int(zone_id))
        if not zone:
            return jsonify({"error": "Zone not found"}), 404
        if zone.baseline_capacity > 0:
            current_stock = db.session.query(
                db.func.coalesce(db.func.sum(Product.stock), 0)
            ).filter_by(zone_id=zone.id).scalar()
            remaining = zone.baseline_capacity - current_stock
            if int(stock) > remaining:
                return jsonify({
                    "error": f"Stock exceeds zone capacity. Zone '{zone.name}' has {remaining} of {zone.baseline_capacity} slots remaining."
                }), 400

    product = Product(
        name        = name,
        category    = category,
        price       = float(price),
        stock       = int(stock),
        description = data.get("description", ""),
        image_url   = data.get("image_url", ""),
        zone_id     = int(zone_id) if zone_id else None,
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Product added", "product": product.to_dict()}), 201


# ── Update product ────────────────────────────────────────────────
@products_bp.route("/products/<int:pid>", methods=["PUT"])
def update_product(pid):
    product = Product.query.get_or_404(pid)
    data    = request.get_json()

    new_stock = int(data.get("stock", product.stock))
    new_zone_id = data.get("zone_id", product.zone_id)
    if new_zone_id is not None:
        new_zone_id = int(new_zone_id) if new_zone_id else None

    # Validate zone capacity
    target_zone_id = new_zone_id if "zone_id" in data else product.zone_id
    if target_zone_id:
        zone = Zone.query.get(target_zone_id)
        if zone and zone.baseline_capacity > 0:
            # Subtract this product's current stock from zone total
            current_stock = db.session.query(
                db.func.coalesce(db.func.sum(Product.stock), 0)
            ).filter(Product.zone_id == zone.id, Product.id != product.id).scalar()
            remaining = zone.baseline_capacity - current_stock
            if new_stock > remaining:
                return jsonify({
                    "error": f"Stock exceeds zone capacity. Zone '{zone.name}' has {remaining} of {zone.baseline_capacity} slots remaining."
                }), 400

    product.name        = data.get("name",        product.name)
    product.category    = data.get("category",    product.category)
    product.price       = float(data.get("price", product.price))
    product.stock       = new_stock
    product.description = data.get("description", product.description)
    # Only update image_url if explicitly included in the request
    if "image_url" in data:
        product.image_url = data["image_url"]
    if "zone_id" in data:
        product.zone_id = new_zone_id

    db.session.commit()
    return jsonify({"message": "Product updated", "product": product.to_dict()}), 200


# ── Delete product ────────────────────────────────────────────────
@products_bp.route("/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    product = Product.query.get_or_404(pid)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"}), 200