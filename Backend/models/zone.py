from models import db
from datetime import datetime


class Zone(db.Model):
    __tablename__ = "zones"

    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(120), nullable=False, unique=True)
    description         = db.Column(db.Text, nullable=True, default="")
    camera_source       = db.Column(db.String(255), nullable=True, default="0")
    product_types       = db.Column(db.Text, nullable=False, default="")
    last_detected_count = db.Column(db.Integer, default=0)
    empty_slots         = db.Column(db.Integer, default=0)
    baseline_capacity   = db.Column(db.Integer, default=0)   # max products when fully stocked
    last_scan_at        = db.Column(db.DateTime, nullable=True)
    is_active           = db.Column(db.Boolean, default=False)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    logs = db.relationship("ZoneLog", backref="zone", lazy=True,
                           cascade="all, delete-orphan",
                           order_by="ZoneLog.scanned_at.desc()")

    def get_product_list(self):
        """Return product_types as a list."""
        if not self.product_types:
            return []
        return [t.strip() for t in self.product_types.split(",") if t.strip()]

    @property
    def stock_percentage(self):
        """Calculate current stock as percentage of baseline capacity."""
        if self.baseline_capacity <= 0:
            return 100.0  # no baseline set yet → assume OK
        pct = (self.last_detected_count / self.baseline_capacity) * 100
        return round(min(pct, 100.0), 1)

    def to_dict(self):
        return {
            "id":                  self.id,
            "name":                self.name,
            "description":         self.description,
            "camera_source":       self.camera_source,
            "product_types":       self.get_product_list(),
            "last_detected_count": self.last_detected_count,
            "empty_slots":         self.empty_slots,
            "baseline_capacity":   self.baseline_capacity,
            "stock_percentage":    self.stock_percentage,
            "last_scan_at":        self.last_scan_at.strftime("%Y-%m-%d %H:%M:%S") if self.last_scan_at else None,
            "is_active":           self.is_active,
            "created_at":          self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
