from models import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = "products"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True, default="")
    category    = db.Column(db.String(100), nullable=False)
    price       = db.Column(db.Float,   nullable=False)
    stock       = db.Column(db.Integer, nullable=False, default=0)
    image_url   = db.Column(db.String(255), nullable=True, default="")
    zone_id     = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", backref="product", lazy=True)

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "category":    self.category,
            "price":       self.price,
            "stock":       self.stock,
            "image_url":   self.image_url,
            "zone_id":     self.zone_id,
            "created_at":  self.created_at.strftime("%Y-%m-%d")
        }
