from models import db
from datetime import datetime


class ZoneLog(db.Model):
    __tablename__ = "zone_logs"

    id             = db.Column(db.Integer, primary_key=True)
    zone_id        = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)
    detected_count = db.Column(db.Integer, default=0)
    empty_slots    = db.Column(db.Integer, default=0)
    alert_level    = db.Column(db.String(20), default="ok")      # ok, low, medium, high
    scanned_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":             self.id,
            "zone_id":        self.zone_id,
            "detected_count": self.detected_count,
            "empty_slots":    self.empty_slots,
            "alert_level":    self.alert_level,
            "scanned_at":     self.scanned_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
