from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from models import db
from models.user import User
from models.product import Product
from models.order import Order
from models.order_item import OrderItem
from models.zone import Zone
from models.zone_log import ZoneLog
from routes.auth import auth_bp
from routes.products import products_bp
from routes.orders import orders_bp
from routes.stats import stats_bp
from routes.chatbot import chatbot_bp
from routes.reviews import reviews_bp
from routes.vision import vision_bp
from models.review import Review
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "static", "uploads"), exist_ok=True)

    CORS(app, resources={r"/*": {"origins": "*"}})
    db.init_app(app)
    app.register_blueprint(auth_bp,     url_prefix="/api")
    app.register_blueprint(products_bp, url_prefix="/api")
    app.register_blueprint(orders_bp,   url_prefix="/api")
    app.register_blueprint(stats_bp,    url_prefix="/api")
    app.register_blueprint(chatbot_bp,  url_prefix="/api")
    app.register_blueprint(reviews_bp,  url_prefix="/api")
    app.register_blueprint(vision_bp,   url_prefix="/api")

    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        uploads_dir = os.path.join(app.root_path, "static", "uploads")
        return send_from_directory(uploads_dir, filename)

    # ── Serve Frontend ────────────────────────────────────────────
    frontend_dir = os.path.join(app.root_path, "..", "Frontend")

    @app.route("/")
    def home():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/index.html")
    def home_index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/pages/<path:filename>")
    def serve_page(filename):
        return send_from_directory(os.path.join(frontend_dir, "pages"), filename)

    @app.route("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(os.path.join(frontend_dir, "css"), filename)

    @app.route("/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(os.path.join(frontend_dir, "js"), filename)

    @app.route("/images/<path:filename>")
    def serve_images(filename):
        return send_from_directory(os.path.join(frontend_dir, "images"), filename)

    @app.route("/fonts/<path:filename>")
    def serve_fonts(filename):
        return send_from_directory(os.path.join(frontend_dir, "fonts"), filename)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    with app.app_context():
        db.create_all()
        _seed_data()

    return app


def _seed_data():
    if User.query.count() == 0:
        admin = User(username="admin", email="admin@smart.ma", role="admin")
        admin.set_password("admin123")
        customer = User(username="abdo", email="abdo@smart.ma", role="customer")
        customer.set_password("abdo123")
        db.session.add_all([admin, customer])
        db.session.commit()

    # Seed zones if none exist (products are added manually by admin)
    if Zone.query.count() == 0:
        zones = [
            Zone(
                name="Dairy Zone",
                description="Milk, butter, yogurt, cheese and dairy products",
                camera_source="0",
                product_types="milk,butter,yogurt,cheese,eggs",
                baseline_capacity=200,
            ),
            Zone(
                name="Bakery Zone",
                description="Bread, pastries and baked goods",
                camera_source="0",
                product_types="bread,croissant,pastry,cake",
                baseline_capacity=150,
            ),
            Zone(
                name="Beverages Zone",
                description="Juices, soft drinks and water",
                camera_source="0",
                product_types="juice,water,soda,tea",
                baseline_capacity=250,
            ),
        ]
        db.session.add_all(zones)
        db.session.commit()
        print(f"[SEED] Created {len(zones)} zones (add products manually via admin panel)")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)