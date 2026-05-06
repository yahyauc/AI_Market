"""
Vision AI routes — Zone management + YOLOv8 detection endpoints.
Includes stock sync, live dashboard data, and email alerts.
"""

from flask import Blueprint, request, jsonify, current_app, Response
from models import db
from models.zone import Zone
from models.zone_log import ZoneLog
from models.product import Product
from datetime import datetime
import os
import io
import base64
import traceback
import threading
import requests as http_requests

vision_bp = Blueprint("vision", __name__)


# ── Camera Session Manager — uses OpenCV to capture from any URL ──
# Supports: YouTube, webcam sites, direct MJPEG/RTSP streams, video files

import cv2
import numpy as np
import time

_camera_session = {
    "active": False,
    "capture": None,
    "thread": None,
    "latest_frame": None,       # raw JPEG bytes of latest frame
    "url": None,
    "error": None,
    "fps": 0,
    "frame_count": 0,
    "lock": threading.Lock(),
}


def _resolve_video_url(url):
    """
    Resolve a URL to a direct video stream URL.
    Handles YouTube, webcam sites, and other platforms via yt-dlp.
    Returns the direct stream URL or the original URL if no extraction needed.
    """
    # Direct streams / IP cameras — no extraction needed
    direct_extensions = ('.mjpg', '.mjpeg', '.mp4', '.avi', '.mov', '.webm', '.m3u8')
    if any(url.lower().endswith(ext) for ext in direct_extensions):
        return url

    # Check if it's a plain IP/port (like http://192.168.1.100:8080)
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.hostname and parsed.hostname.replace('.', '').isdigit():
        return url  # Direct IP camera

    # Try yt-dlp to extract the actual video stream URL
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[height<=720]/bestvideo[height<=720]+bestaudio/best',
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get('url'):
                print(f"[CAMERA] yt-dlp resolved: {url} -> stream found")
                return info['url']
            # Some extractors put the URL in 'formats'
            if info and info.get('formats'):
                # Pick the best format with a direct URL
                for fmt in reversed(info['formats']):
                    if fmt.get('url') and fmt.get('vcodec', 'none') != 'none':
                        print(f"[CAMERA] yt-dlp format: {fmt.get('format_id')} {fmt.get('resolution', '?')}")
                        return fmt['url']
    except Exception as e:
        print(f"[CAMERA] yt-dlp extraction failed: {e}")
        if 'youtube.com' in url or 'youtu.be' in url:
            raise Exception(f"YouTube extraction failed: {str(e)}")

    # Fallback — return original URL and let OpenCV try
    return url


def _camera_capture_loop():
    """Background thread that continuously captures frames from the video source."""
    session = _camera_session
    cap = session["capture"]
    if cap is None or not cap.isOpened():
        session["error"] = "Failed to open video source"
        session["active"] = False
        return

    print(f"[CAMERA] Capture loop started for: {session['url']}")
    consecutive_failures = 0
    max_failures = 30  # Stop after 30 consecutive failed reads

    while session["active"]:
        ret, frame = cap.read()
        if ret and frame is not None:
            consecutive_failures = 0
            session["frame_count"] += 1

            # Encode frame as JPEG
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            with session["lock"]:
                session["latest_frame"] = jpeg.tobytes()
                session["error"] = None

            # Control frame rate (~10 fps max to reduce CPU)
            time.sleep(0.1)
        else:
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                session["error"] = "Video stream ended or connection lost"
                print(f"[CAMERA] Stream ended after {session['frame_count']} frames")
                break
            time.sleep(0.5)  # Wait before retry

    # Cleanup
    if cap and cap.isOpened():
        cap.release()
    session["active"] = False
    session["capture"] = None
    print("[CAMERA] Capture loop stopped")


@vision_bp.route("/vision/camera-start", methods=["POST"])
def camera_start():
    """
    Start capturing video from a URL.
    Accepts: YouTube links, webcam site URLs, direct stream URLs, video files.
    Body JSON: { "url": "https://..." }
    """
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    # Stop any existing session
    _stop_camera_session()

    # Resolve the URL (extract stream from YouTube/webcam sites)
    try:
        resolved_url = _resolve_video_url(url)
    except Exception as e:
        return jsonify({"error": f"Could not resolve video URL: {str(e)}"}), 400

    # Open with OpenCV
    print(f"[CAMERA] Opening: {resolved_url[:100]}...")
    cap = cv2.VideoCapture(resolved_url)

    # Give it a moment to connect
    if not cap.isOpened():
        # Try with different backends
        cap = cv2.VideoCapture(resolved_url, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        return jsonify({"error": "Could not open video source. The URL may be invalid or the video is not accessible."}), 400

    # Get video info
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    # Read one test frame
    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        cap.release()
        return jsonify({"error": "Connected but could not read any frames from this source."}), 400

    # Encode first frame
    _, jpeg = cv2.imencode('.jpg', test_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

    # Setup session
    session = _camera_session
    session["active"] = True
    session["capture"] = cap
    session["url"] = url
    session["error"] = None
    session["fps"] = fps
    session["frame_count"] = 1
    with session["lock"]:
        session["latest_frame"] = jpeg.tobytes()

    # Start background capture thread
    t = threading.Thread(target=_camera_capture_loop, daemon=True)
    t.start()
    session["thread"] = t

    return jsonify({
        "status": "started",
        "url": url,
        "resolution": f"{width}x{height}",
        "fps": round(fps, 1),
    })


@vision_bp.route("/vision/camera-frame")
def camera_frame():
    """Return the latest captured frame as a JPEG image."""
    session = _camera_session

    if not session["active"] and session["latest_frame"] is None:
        return jsonify({"error": "No active camera session"}), 404

    if session.get("error") and session["latest_frame"] is None:
        return jsonify({"error": session["error"]}), 502

    with session["lock"]:
        frame_data = session["latest_frame"]

    if frame_data is None:
        return jsonify({"error": "No frame available yet"}), 404

    return Response(
        frame_data,
        mimetype="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store", "Pragma": "no-cache"}
    )


@vision_bp.route("/vision/camera-stop", methods=["POST"])
def camera_stop():
    """Stop the active camera session."""
    _stop_camera_session()
    return jsonify({"status": "stopped"})


@vision_bp.route("/vision/camera-status")
def camera_status():
    """Get the status of the current camera session."""
    session = _camera_session
    return jsonify({
        "active": session["active"],
        "url": session["url"],
        "frame_count": session["frame_count"],
        "error": session["error"],
        "fps": session["fps"],
    })


def _stop_camera_session():
    """Stop and cleanup the active camera session."""
    session = _camera_session
    session["active"] = False

    if session["thread"] and session["thread"].is_alive():
        session["thread"].join(timeout=3)

    if session["capture"] and session["capture"].isOpened():
        session["capture"].release()

    session["capture"] = None
    session["thread"] = None
    session["latest_frame"] = None
    session["url"] = None
    session["error"] = None
    session["frame_count"] = 0

# ── Lazy-loaded YOLO models (loaded once on first detection) ─────
_empty_shelf_model = None
_product_detector_model = None


def _load_empty_shelf_model():
    global _empty_shelf_model
    if _empty_shelf_model is None:
        from ultralytics import YOLO
        path = current_app.config.get("YOLO_EMPTY_SHELF_MODEL")
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Empty shelf model not found at: {path}")
        _empty_shelf_model = YOLO(path)
    return _empty_shelf_model


def _load_product_detector():
    global _product_detector_model
    if _product_detector_model is None:
        from ultralytics import YOLO
        path = current_app.config.get("YOLO_PRODUCT_DETECTOR")
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Product detector model not found at: {path}")
        _product_detector_model = YOLO(path)
    return _product_detector_model


# ── Percentage-based alert system ─────────────────────────────────

def _compute_alert_level(detected_count, empty_slots, baseline_capacity=0):
    """
    Determine alert level based on stock PERCENTAGE of baseline capacity.

    Thresholds:
      - >= 60% of baseline  →  "ok"      (green)
      - 40% – 59%           →  "medium"   (orange warning)
      - < 40%               →  "high"     (red critical)

    If no baseline is set, fall back to detected vs empty ratio.
    """
    # Use baseline if available, otherwise use total detected + empty as reference
    if baseline_capacity > 0:
        reference = baseline_capacity
    else:
        reference = detected_count + empty_slots
        if reference == 0:
            return "ok"  # no data yet

    if reference == 0:
        return "ok"

    percentage = detected_count / reference

    if percentage >= 0.60:
        return "ok"
    if percentage >= 0.40:
        return "medium"
    return "high"


def _sync_stock_to_products(zone, product_count):
    """
    Sync the YOLO-detected product count to the Product.stock field.
    Primary: use zone_id FK. Fallback: text-match by product_types.
    Distributes the total count equally among matching products.
    """
    try:
        # Primary: products linked by zone_id
        matching = Product.query.filter_by(zone_id=zone.id).all()

        # Fallback: text-match if no zone_id-linked products
        if not matching:
            zone_types = [t.strip().lower() for t in (zone.product_types or "").split(",") if t.strip()]
            if not zone_types:
                return
            for p in Product.query.all():
                p_cat = (p.category or "").lower()
                p_name = (p.name or "").lower()
                for zt in zone_types:
                    if zt in p_cat or zt in p_name:
                        matching.append(p)
                        break

        if not matching:
            return

        # Distribute evenly among linked products
        per_product = max(0, round(product_count / len(matching)))
        remainder = product_count - (per_product * len(matching))
        for i, p in enumerate(matching):
            p.stock = per_product + (1 if i < remainder else 0)

        db.session.commit()
        print(f"[STOCK SYNC] Zone '{zone.name}': {product_count} detected -> {len(matching)} products updated")
        for p in matching:
            print(f"  - {p.name} ({p.category}): stock = {p.stock}")

    except Exception as e:
        print(f"[STOCK SYNC ERROR] {e}")
        traceback.print_exc()





def _send_critical_alert_email(zone, product_count, empty_slots):
    """Send email alert to admin when zone is in critical state."""
    try:
        MAIL_USER = os.getenv("MAIL_USERNAME", "")
        MAIL_PASS = os.getenv("MAIL_PASSWORD", "")
        ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", MAIL_USER)

        if not MAIL_USER or not MAIL_PASS or not ADMIN_EMAIL:
            print("[EMAIL ALERT] Skipped -- no email credentials configured")
            return

        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        # Calculate percentage for the email
        baseline = zone.baseline_capacity or (product_count + empty_slots) or 1
        pct = round((product_count / baseline) * 100, 1) if baseline > 0 else 0

        now_str = datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')
        subject = f"CRITICAL ALERT -- {zone.name} -- Stock below 40% ({pct}%)"

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f6fa;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:600px;margin:40px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08)">
    <div style="background:#dc2626;padding:32px 40px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:22px">Critical Stock Alert</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px">Stock has dropped below 40% — immediate attention required</p>
    </div>
    <div style="padding:36px 40px">
        <h2 style="color:#1a1f36;font-size:18px;margin:0 0 8px">Zone: {zone.name}</h2>
        <p style="color:#6b7280;font-size:14px;margin:0 0 24px;line-height:1.6">
            The AI Vision system detected that stock in this zone has dropped to <strong>{pct}%</strong> of baseline capacity.
            This indicates a severe stock shortage that needs immediate restocking.
        </p>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
            <tr>
                <td style="width:33%;text-align:center;padding:20px;background:#fef2f2;border:1px solid #fecaca;border-radius:12px">
                    <div style="font-size:32px;font-weight:800;color:#dc2626">{pct}%</div>
                    <div style="font-size:11px;font-weight:700;color:#991b1b;text-transform:uppercase;margin-top:4px">Stock Level</div>
                </td>
                <td style="width:33%;text-align:center;padding:20px;background:#f0f4ff;border:1px solid #bfcffe;border-radius:12px">
                    <div style="font-size:32px;font-weight:800;color:#2563eb">{product_count}</div>
                    <div style="font-size:11px;font-weight:700;color:#1e40af;text-transform:uppercase;margin-top:4px">Products Found</div>
                </td>
                <td style="width:33%;text-align:center;padding:20px;background:#fff7ed;border:1px solid #fed7aa;border-radius:12px">
                    <div style="font-size:32px;font-weight:800;color:#ea580c">{zone.baseline_capacity}</div>
                    <div style="font-size:11px;font-weight:700;color:#9a3412;text-transform:uppercase;margin-top:4px">Baseline Capacity</div>
                </td>
            </tr>
        </table>
        <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:16px 20px;margin-bottom:20px">
            <h4 style="color:#ea580c;margin:0 0 6px;font-size:14px;font-weight:700">Recommended Action</h4>
            <p style="color:#9a3412;font-size:13px;margin:0;line-height:1.6">
                Check {zone.name} immediately and restock the shelves.
                Products in this zone: <strong>{zone.product_types}</strong>
            </p>
        </div>
        <p style="font-size:12px;color:#9ca3af;text-align:center;margin:0">Detected at {now_str}</p>
    </div>
    <div style="background:#f5f6fa;padding:20px 40px;text-align:center;border-top:1px solid #e8ecf0">
        <p style="color:#9ca3af;font-size:11px;margin:0">Smart Supermarket -- AI Vision Alert System</p>
    </div>
</div>
</body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Smart Supermarket <{MAIL_USER}>"
        msg["To"] = ADMIN_EMAIL
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(MAIL_USER, MAIL_PASS)
            server.sendmail(MAIL_USER, ADMIN_EMAIL, msg.as_string())

        print(f"[EMAIL ALERT] Critical alert sent for zone '{zone.name}' to {ADMIN_EMAIL}")

    except Exception as e:
        print(f"[EMAIL ALERT ERROR] {e}")
        traceback.print_exc()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ZONE  C R U D
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@vision_bp.route("/zones", methods=["GET"])
def get_zones():
    zones = Zone.query.order_by(Zone.created_at.desc()).all()
    return jsonify([z.to_dict() for z in zones]), 200


@vision_bp.route("/zones/<int:zone_id>", methods=["GET"])
def get_zone(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    return jsonify(zone.to_dict()), 200


@vision_bp.route("/zones", methods=["POST"])
def create_zone():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Zone name is required"}), 400

    pt = data.get("product_types", "")
    if isinstance(pt, list):
        pt = ",".join(pt)

    zone = Zone(
        name=name,
        description=data.get("description", ""),
        camera_source=data.get("camera_source", "0"),
        product_types=pt,
        baseline_capacity=int(data.get("baseline_capacity", 0)),
        is_active=data.get("is_active", False),
    )
    db.session.add(zone)
    db.session.commit()

    return jsonify({
        "message": "Zone created",
        "zone": zone.to_dict(),
    }), 201


@vision_bp.route("/zones/<int:zone_id>", methods=["PUT"])
def update_zone(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    data = request.get_json()

    zone.name = data.get("name", zone.name)
    zone.description = data.get("description", zone.description)
    zone.camera_source = data.get("camera_source", zone.camera_source)

    pt = data.get("product_types")
    if pt is not None:
        zone.product_types = ",".join(pt) if isinstance(pt, list) else pt

    if "is_active" in data:
        zone.is_active = data["is_active"]

    if "baseline_capacity" in data:
        zone.baseline_capacity = int(data["baseline_capacity"])

    db.session.commit()

    return jsonify({
        "message": "Zone updated",
        "zone": zone.to_dict(),
    }), 200


@vision_bp.route("/zones/<int:zone_id>", methods=["DELETE"])
def delete_zone(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    db.session.delete(zone)
    db.session.commit()
    return jsonify({"message": "Zone deleted"}), 200


@vision_bp.route("/zones/<int:zone_id>/toggle", methods=["POST"])
def toggle_zone(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    zone.is_active = not zone.is_active
    db.session.commit()
    return jsonify({"message": f"Zone {'activated' if zone.is_active else 'deactivated'}",
                     "zone": zone.to_dict()}), 200


@vision_bp.route("/zones/<int:zone_id>/remaining-capacity", methods=["GET"])
def zone_remaining_capacity(zone_id):
    """Return how much stock capacity is left in a zone."""
    zone = Zone.query.get_or_404(zone_id)
    current_stock = db.session.query(
        db.func.coalesce(db.func.sum(Product.stock), 0)
    ).filter_by(zone_id=zone.id).scalar()
    remaining = max(0, zone.baseline_capacity - current_stock)
    return jsonify({
        "zone_id": zone.id,
        "zone_name": zone.name,
        "baseline_capacity": zone.baseline_capacity,
        "used": current_stock,
        "remaining": remaining,
    }), 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  D E T E C T I O N
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@vision_bp.route("/vision/detect", methods=["POST"])
def detect():
    """
    Run YOLO detection on an uploaded image.
    After detection: syncs stock to DB products + sends alert emails if critical.
    Supports 'conf' parameter to set confidence threshold (default 0.15 for better camera detection).
    """
    import numpy as np
    from PIL import Image

    zone_id = request.form.get("zone_id") or (request.get_json(silent=True) or {}).get("zone_id")
    if not zone_id:
        return jsonify({"error": "zone_id is required"}), 400

    zone = Zone.query.get(int(zone_id))
    if not zone:
        return jsonify({"error": "Zone not found"}), 404

    # ── Confidence threshold (lower = more detections) ───────────
    conf_threshold = float(request.form.get("conf", 0) or
                          (request.get_json(silent=True) or {}).get("conf", 0) or 0.05)
    conf_threshold = max(0.01, min(conf_threshold, 0.95))  # clamp to safe range

    # ── Parse image ───────────────────────────────────────────────
    img = None
    if "image" in request.files:
        file = request.files["image"]
        img = Image.open(file.stream).convert("RGB")
    else:
        data = request.get_json(silent=True)
        if data and data.get("image_base64"):
            raw = data["image_base64"]
            if "," in raw:
                raw = raw.split(",", 1)[1]
            img_bytes = base64.b64decode(raw)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    if img is None:
        return jsonify({"error": "No image provided. Send 'image' file or 'image_base64'."}), 400

    img_np = np.array(img)
    # Debug save
    debug_path = os.path.join(current_app.root_path, "static", "uploads", f"debug_detect_{zone.id}.jpg")
    img.save(debug_path)
    
    print(f"[DETECT] Zone '{zone.name}' | Image: {img.width}x{img.height} | Conf threshold: {conf_threshold} | Saved to {debug_path}")

    # ── Run YOLO models ──────────────────────────────────────────
    product_count = 0
    empty_count   = 0
    detections    = []

    try:
        product_model = _load_product_detector()
        prod_results  = product_model(img_np, conf=conf_threshold, verbose=False)
        for r in prod_results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                label  = r.names.get(cls_id, f"class_{cls_id}")
                coords = box.xyxy[0].tolist()
                product_count += 1
                detections.append({
                    "type": "product", "label": label,
                    "confidence": round(conf, 3),
                    "bbox": [round(c, 1) for c in coords],
                })
        print(f"[DETECT] Products found: {product_count}")
    except FileNotFoundError as e:
        print(f"[DETECT ERROR] Product model not found: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"[DETECT ERROR] Product detection failed: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Product detection failed: {str(e)}"}), 500

    try:
        shelf_model   = _load_empty_shelf_model()
        shelf_results = shelf_model(img_np, conf=conf_threshold, verbose=False)
        for r in shelf_results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                label  = r.names.get(cls_id, f"class_{cls_id}")
                coords = box.xyxy[0].tolist()
                empty_count += 1
                detections.append({
                    "type": "empty", "label": label,
                    "confidence": round(conf, 3),
                    "bbox": [round(c, 1) for c in coords],
                })
        print(f"[DETECT] Empty slots found: {empty_count}")
    except FileNotFoundError as e:
        print(f"[DETECT ERROR] Empty shelf model not found: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"[DETECT ERROR] Empty shelf detection failed: {e}")
        traceback.print_exc()
        empty_count = 0

    # ── Auto-set baseline capacity on first scan ──────────────────
    total_detected_plus_empty = product_count + empty_count
    if zone.baseline_capacity == 0 and total_detected_plus_empty > 0:
        zone.baseline_capacity = total_detected_plus_empty
        print(f"[BASELINE] Auto-set baseline for '{zone.name}' = {zone.baseline_capacity}")
    elif total_detected_plus_empty > zone.baseline_capacity and zone.baseline_capacity > 0:
        # Zone was restocked — update baseline to the new higher count
        zone.baseline_capacity = total_detected_plus_empty
        print(f"[BASELINE] Updated baseline for '{zone.name}' = {zone.baseline_capacity}")

    # ── Compute alert using percentage-based logic ────────────────
    alert = _compute_alert_level(product_count, empty_count, zone.baseline_capacity)
    now = datetime.utcnow()
    zone.last_detected_count = product_count
    zone.empty_slots         = empty_count
    zone.last_scan_at        = now

    log = ZoneLog(
        zone_id=zone.id, detected_count=product_count,
        empty_slots=empty_count, alert_level=alert, scanned_at=now,
    )
    db.session.add(log)
    db.session.commit()

    # ── Sync detection count to Product.stock in database ─────────
    _sync_stock_to_products(zone, product_count)

    # ── Send email alert if critical (< 40% stock) ────────────────
    if alert == "high":
        app = current_app._get_current_object()
        def _alert_thread():
            with app.app_context():
                _send_critical_alert_email(zone, product_count, empty_count)
        threading.Thread(target=_alert_thread, daemon=True).start()

    return jsonify({
        "zone":              zone.to_dict(),
        "product_count":     product_count,
        "empty_slots":       empty_count,
        "baseline_capacity": zone.baseline_capacity,
        "stock_percentage":  zone.stock_percentage,
        "alert_level":       alert,
        "detections":        detections,
        "scanned_at":        now.strftime("%Y-%m-%d %H:%M:%S"),
        "image_width":       img.width,
        "image_height":      img.height,
    }), 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  L O G S   &   S U M M A R Y   &   L I V E   D A S H B O A R D
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@vision_bp.route("/zones/<int:zone_id>/logs", methods=["GET"])
def get_zone_logs(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    limit = request.args.get("limit", 20, type=int)
    logs = ZoneLog.query.filter_by(zone_id=zone_id) \
                        .order_by(ZoneLog.scanned_at.desc()) \
                        .limit(limit).all()
    return jsonify({
        "zone": zone.to_dict(),
        "logs": [l.to_dict() for l in logs],
    }), 200


@vision_bp.route("/vision/summary", methods=["GET"])
def vision_summary():
    """Overview of all zones with their latest detection data."""
    zones = Zone.query.order_by(Zone.name).all()
    total_products = sum(z.last_detected_count for z in zones)
    total_empty    = sum(z.empty_slots for z in zones)
    active_zones   = sum(1 for z in zones if z.is_active)

    return jsonify({
        "zones":          [z.to_dict() for z in zones],
        "total_zones":    len(zones),
        "active_zones":   active_zones,
        "total_products": total_products,
        "total_empty":    total_empty,
    }), 200


@vision_bp.route("/vision/live-dashboard", methods=["GET"])
def live_dashboard():
    """
    Live dashboard data combining zone detection + product stock + orders.
    Called by the dashboard every 10 seconds for real-time updates.
    Uses percentage-based alert levels.
    """
    from models.order import Order

    zones = Zone.query.order_by(Zone.name).all()
    products = Product.query.all()
    orders = Order.query.all()

    total_detected = sum(z.last_detected_count for z in zones)
    total_empty    = sum(z.empty_slots for z in zones)

    # Zone alerts — using percentage-based logic
    zone_alerts = []
    critical_zones = []
    for z in zones:
        alert = _compute_alert_level(z.last_detected_count, z.empty_slots, z.baseline_capacity)
        zone_data = z.to_dict()
        zone_data["alert_level"] = alert
        zone_alerts.append(zone_data)
        if alert == "high":
            critical_zones.append(z.name)

    # Product stock
    low_stock = [p for p in products if p.stock <= 5]
    out_of_stock = [p for p in products if p.stock == 0]

    return jsonify({
        "zones":                zone_alerts,
        "total_detected":       total_detected,
        "total_empty":          total_empty,
        "total_products_db":    len(products),
        "total_orders":         len(orders),
        "low_stock_count":      len(low_stock),
        "out_of_stock_count":   len(out_of_stock),
        "critical_zones":       critical_zones,
        "has_critical_alert":   len(critical_zones) > 0,
        "timestamp":            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }), 200


@vision_bp.route("/vision/diagnostic", methods=["GET"])
def vision_diagnostic():
    """Diagnostic endpoint: checks model files, system info, camera status."""
    product_model_path = current_app.config.get("YOLO_PRODUCT_DETECTOR", "")
    empty_model_path = current_app.config.get("YOLO_EMPTY_SHELF_MODEL", "")

    product_exists = os.path.exists(product_model_path) if product_model_path else False
    empty_exists = os.path.exists(empty_model_path) if empty_model_path else False

    product_size = os.path.getsize(product_model_path) if product_exists else 0
    empty_size = os.path.getsize(empty_model_path) if empty_exists else 0

    session = _camera_session

    return jsonify({
        "models": {
            "product_detector": {
                "path": product_model_path,
                "exists": product_exists,
                "size_mb": round(product_size / (1024 * 1024), 1) if product_size else 0,
            },
            "empty_shelf": {
                "path": empty_model_path,
                "exists": empty_exists,
                "size_mb": round(empty_size / (1024 * 1024), 1) if empty_size else 0,
            }
        },
        "camera": {
            "active": session["active"],
            "url": session["url"],
            "frame_count": session["frame_count"],
            "error": session["error"],
        },
        "models_loaded": {
            "product_detector": _product_detector_model is not None,
            "empty_shelf": _empty_shelf_model is not None,
        },
        "opencv_version": cv2.__version__,
    }), 200
