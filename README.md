# 🛒 Smart Market — AI-Powered Supermarket Management System

<div align="center">

**An intelligent supermarket management platform powered by Computer Vision and AI**

*Final Year Project (PFE) — École Supérieure de Technologie*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)](https://docs.ultralytics.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org)

---

</div>

## 📖 Table of Contents

- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [AI Modules](#-ai-modules-computer-vision)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Screenshots](#-screenshots)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Downloading AI Models](#downloading-ai-models)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
- [API Endpoints](#-api-endpoints)
- [How It Works](#-how-it-works)
- [Team](#-team)
- [License](#-license)

---

## 🎯 About the Project

**Smart Market** is a full-stack AI-powered supermarket management system designed as a Final Year Project (Projet de Fin d'Études). It combines a modern e-commerce storefront with a powerful administration dashboard, real-time AI-based shelf monitoring using computer vision (YOLOv8), and an intelligent AI chatbot assistant powered by Groq's LLaMA 3.3 model.

The system enables supermarket administrators to:
- **Monitor shelf stock in real-time** using camera feeds and YOLO object detection
- **Automatically detect empty shelves** and receive critical alerts via email
- **Manage products, orders, and zones** through a professional admin panel
- **Get AI-powered business insights** through a smart chatbot that analyzes live store data
- **Serve customers** with a beautiful online storefront and an AI shopping assistant

---

## ✨ Key Features

### 🏪 Customer Storefront
- Professional, responsive homepage with hero banners and promotional sections
- Product catalog with category filtering and search
- Shopping cart with order placement
- Customer AI chatbot for product recommendations and store assistance
- User registration and authentication
- Order tracking and history

### 📊 Admin Dashboard
- Real-time statistics: total products, orders, revenue, low stock alerts
- Live Vision AI monitoring dashboard with zone alerts
- Product management (CRUD) with image uploads
- Order management with status updates (Pending → Confirmed → Delivered)
- Zone management for camera-based monitoring areas
- AI business assistant chatbot with markdown-formatted reports

### 🤖 AI Vision System (Module 1 — Computer Vision)
- **Product Detector Model** — Custom-trained YOLOv8 model that detects and counts products on supermarket shelves
- **Empty Shelf Detector Model** — Custom-trained YOLOv8 model that identifies empty shelf spaces
- Real-time camera feed integration (supports webcams, IP cameras, YouTube streams, RTSP)
- Automatic stock level calculation based on detection results
- Percentage-based alert system:
  - 🟢 **OK** (≥ 60% stocked)
  - 🟠 **Medium** (40%–59% stocked)
  - 🔴 **Critical** (< 40% stocked)
- Automatic stock synchronization — detection results update product stock in the database
- Email alerts sent to administrators when stock drops below critical levels
- Background threaded camera capture for smooth real-time processing
- Diagnostic endpoint for troubleshooting model and camera status

### 💬 AI Chatbot System (Module 2 — LLM Chatbot)
- **Admin Chatbot** — AI business assistant powered by Groq (LLaMA 3.3 70B Versatile)
  - Generates professional business reports with markdown tables
  - Analyzes revenue (daily, weekly, monthly, all-time)
  - Stock alerts and restocking recommendations
  - Top-selling products analysis
  - Order status summaries
  - Uses live database context for real-time insights
- **Customer Chatbot** — AI shopping assistant
  - Helps customers find products by name, category, or description
  - Provides price information in MAD (Moroccan Dirham)
  - Suggests alternatives when items are out of stock
  - Friendly, conversational tone

### 📧 Email Alert System
- Automatic email notifications when zones reach critical stock levels
- Professional HTML email templates with zone stats, stock percentages, and recommended actions
- Configurable via environment variables (Gmail SMTP)

### 🗃️ Additional Features
- Product reviews and ratings system
- Dynamic category suggestions from the database
- Automatic database seeding with default admin user and zones
- Docker support for containerized deployment
- Fully RESTful API architecture

---

## 🧠 AI Modules (Computer Vision)

This project uses **two custom-trained YOLOv8 models** for real-time supermarket shelf analysis:

### Module 1 — Product Detector (`Product_detector_model.pt`)
| Detail | Value |
|--------|-------|
| **Architecture** | YOLOv8 (Ultralytics) |
| **Purpose** | Detect and count individual products on supermarket shelves |
| **File Size** | ~326 MB |
| **Input** | RGB image of a shelf (any resolution) |
| **Output** | Bounding boxes with class labels and confidence scores |

This model scans shelf images and identifies each visible product. The total count is used to determine current stock levels and is automatically synced to the product database.

### Module 2 — Empty Shelf Detector (`impty_shelfs.pt`)
| Detail | Value |
|--------|-------|
| **Architecture** | YOLOv8 (Ultralytics) |
| **Purpose** | Detect empty shelf spaces that need restocking |
| **File Size** | ~109 MB |
| **Input** | RGB image of a shelf (any resolution) |
| **Output** | Bounding boxes highlighting empty shelf areas |

This model identifies gaps and empty spaces on shelves. Combined with the product detector, it provides a complete picture of shelf utilization and triggers alerts when stock is low.

### How Detection Works
1. An image is captured from the zone's camera source (or uploaded manually)
2. Both YOLO models run on the image simultaneously
3. Products detected → counted and synced to the database
4. Empty slots detected → used to calculate stock percentage
5. Alert level is computed: `stock_percentage = products / baseline_capacity`
6. If critical (< 40%), an email alert is sent to the admin
7. Results are logged in the `zone_logs` table for historical tracking

> **Note:** The `.pt` model files are too large for GitHub. See [Downloading AI Models](#downloading-ai-models) for download instructions.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, Flask 3.0, Flask-SQLAlchemy, Flask-CORS |
| **Database** | SQLite (via SQLAlchemy ORM) |
| **AI / Vision** | Ultralytics YOLOv8, OpenCV, Pillow, NumPy |
| **AI / Chatbot** | Groq Cloud API, LLaMA 3.3 70B Versatile |
| **Frontend** | HTML5, CSS3 (Vanilla), JavaScript (ES6 Modules) |
| **Icons** | Font Awesome 6.5 |
| **Email** | SMTP (Gmail) with HTML templates |
| **Video Streams** | OpenCV VideoCapture, yt-dlp (YouTube/webcam sites) |
| **Containerization** | Docker |

---

## 📁 Project Structure

```
Smart-Market/
├── Backend/
│   ├── app.py                    # Flask application factory & seed data
│   ├── config.py                 # Configuration (DB, model paths, email)
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # Docker configuration
│   ├── test.py                   # Backend tests
│   ├── models/
│   │   ├── __init__.py           # SQLAlchemy db instance
│   │   ├── user.py               # User model (admin/customer roles)
│   │   ├── product.py            # Product model (with zone FK)
│   │   ├── order.py              # Order model
│   │   ├── order_item.py         # Order line items
│   │   ├── review.py             # Product reviews
│   │   ├── zone.py               # Vision monitoring zones
│   │   └── zone_log.py           # Detection scan history
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py               # Registration & login endpoints
│   │   ├── products.py           # Product CRUD + categories
│   │   ├── orders.py             # Order management
│   │   ├── stats.py              # Dashboard statistics
│   │   ├── reviews.py            # Product reviews
│   │   ├── chatbot.py            # AI chatbot (admin + customer)
│   │   └── vision.py             # Vision AI: zones, detection, camera, alerts
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── email_service.py      # Email notification service
│   │   └── helpers.py            # Utility functions
│   └── static/
│       └── uploads/              # Uploaded product images & debug frames
│
├── Frontend/
│   ├── index.html                # Storefront homepage
│   ├── css/
│   │   └── style.css             # Global stylesheet
│   ├── js/
│   │   ├── api.js                # API client (all fetch calls)
│   │   └── app.js                # Shared UI logic (navbar, cart, toasts)
│   ├── pages/
│   │   ├── login.html            # Login page
│   │   ├── register.html         # Registration page
│   │   ├── products.html         # Product catalog (customer)
│   │   ├── cart.html              # Shopping cart
│   │   ├── orders.html           # Order history
│   │   ├── admin-dashboard.html  # Admin main dashboard
│   │   ├── admin-products.html   # Admin product management
│   │   ├── admin-orders.html     # Admin order management
│   │   ├── admin-chatbot.html    # AI business assistant
│   │   ├── admin-vision.html     # Vision AI monitoring panel
│   │   └── admin-releve.html     # Stock reports
│   └── images/
│       ├── hero-banner.png       # Homepage hero image
│       └── promo-banner.png      # Promotional banner
│
├── Modules/
│   └── DOWNLOAD_MODELS.txt       # Download links for the YOLO .pt models
│
├── .gitignore
├── Dockerfile
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

Make sure the following are installed on your system:

- **Python 3.10+** — [Download Python](https://www.python.org/downloads/)
- **pip** — Python package manager (comes with Python)
- **Git** — [Download Git](https://git-scm.com/downloads)
- **A Groq API Key** — Free at [console.groq.com](https://console.groq.com) (for the AI chatbot)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kanarkhalid/AI_Market.git
   cd AI_Market
   ```

2. **Create a Python virtual environment** (recommended)
   ```bash
   cd Backend
   python -m venv venv
   ```

3. **Activate the virtual environment**

   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     source venv/bin/activate
     ```

4. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Downloading AI Models

The two YOLO model files are too large for GitHub (~435 MB total). You need to download them and place them in the `Modules/` directory at the project root.

1. **Create the Modules directory** (if it doesn't exist):
   ```bash
   mkdir Modules
   ```

2. **Download the models** from the links provided in `Modules/DOWNLOAD_MODELS.txt`

3. **Place the files** so your structure looks like:
   ```
   AI_Market/
   ├── Modules/
   │   ├── Product_detector_model.pt    (~326 MB)
   │   └── impty_shelfs.pt              (~109 MB)
   ├── Backend/
   ├── Frontend/
   └── ...
   ```

> **Important:** The backend expects the models at the exact paths configured in `Backend/config.py`. The default configuration looks for them in `../Modules/` relative to the `Smart-Market` directory.

### Configuration

#### 1. Groq API Key (Required for AI Chatbot)

Open `Backend/routes/chatbot.py` and replace the placeholder API key on **line 16**:

```python
GROQ_API_KEY = "your_groq_api_key_here"
```

Get a free API key at: [https://console.groq.com](https://console.groq.com)

#### 2. Email Alerts (Optional)

To enable critical stock email alerts, set these environment variables before running:

```bash
# Windows (PowerShell)
$env:MAIL_USERNAME = "your.email@gmail.com"
$env:MAIL_PASSWORD = "your_app_password"
$env:ADMIN_EMAIL = "admin@example.com"

# macOS / Linux
export MAIL_USERNAME="your.email@gmail.com"
export MAIL_PASSWORD="your_app_password"
export ADMIN_EMAIL="admin@example.com"
```

> **Note:** For Gmail, you need to use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### Running the Application

1. **Make sure your virtual environment is activated** and you are in the `Backend/` directory

2. **Start the Flask server:**
   ```bash
   python app.py
   ```

3. **Open your browser** and navigate to:
   ```
   http://127.0.0.1:5000
   ```

4. **Default accounts** (auto-created on first run):

   | Role | Username | Email | Password |
   |------|----------|-------|----------|
   | Admin | `admin` | `admin@smart.ma` | `admin123` |
   | Customer | `abdo` | `abdo@smart.ma` | `abdo123` |

5. **Access the admin panel:**
   ```
   http://127.0.0.1:5000/pages/admin-dashboard.html
   ```
   Log in with the admin credentials above.

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login with username/email + password |

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/products` | List all products (with optional filters) |
| `GET` | `/api/products/categories` | Get all unique categories |
| `POST` | `/api/products` | Add a new product |
| `PUT` | `/api/products/:id` | Update a product |
| `DELETE` | `/api/products/:id` | Delete a product |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/orders` | Get all orders |
| `GET` | `/api/orders/user/:id` | Get orders for a specific user |
| `POST` | `/api/orders` | Create a new order |
| `PUT` | `/api/orders/:id/status` | Update order status |

### Statistics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stats` | Dashboard statistics |

### Vision AI & Zones
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/zones` | List all monitoring zones |
| `GET` | `/api/zones/:id` | Get a specific zone |
| `POST` | `/api/zones` | Create a new zone |
| `PUT` | `/api/zones/:id` | Update a zone |
| `DELETE` | `/api/zones/:id` | Delete a zone |
| `POST` | `/api/zones/:id/toggle` | Toggle zone active/inactive |
| `GET` | `/api/zones/:id/remaining-capacity` | Get remaining stock capacity |
| `GET` | `/api/zones/:id/logs` | Get detection scan history |
| `POST` | `/api/vision/detect` | Run YOLO detection on an image |
| `GET` | `/api/vision/summary` | Overview of all zones |
| `GET` | `/api/vision/live-dashboard` | Real-time dashboard data |
| `GET` | `/api/vision/diagnostic` | System diagnostic info |
| `POST` | `/api/vision/camera-start` | Start camera stream |
| `GET` | `/api/vision/camera-frame` | Get latest camera frame |
| `POST` | `/api/vision/camera-stop` | Stop camera stream |
| `GET` | `/api/vision/camera-status` | Camera session status |

### AI Chatbot
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chatbot/admin` | Admin AI assistant |
| `POST` | `/api/chatbot/customer` | Customer shopping assistant |
| `GET` | `/api/chatbot/suggestions` | Get suggested prompts |

### Reviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| Various | `/api/reviews/*` | Product review endpoints |

---

## ⚙️ How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (HTML/CSS/JS)            │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │Storefront│  │Admin Panel│  │  Vision Dashboard │  │
│  └────┬─────┘  └─────┬─────┘  └────────┬─────────┘  │
│       │              │                  │            │
│       └──────────────┴──────────────────┘            │
│                      │ REST API (fetch)              │
└──────────────────────┼───────────────────────────────┘
                       │
┌──────────────────────┼───────────────────────────────┐
│               Flask Backend (Python)                 │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────────┐  │
│  │Auth/CRUD│  │ Chatbot  │  │    Vision Engine    │  │
│  │ Routes  │  │(Groq API)│  │ (YOLOv8 + OpenCV)   │  │
│  └────┬────┘  └────┬─────┘  └──────────┬──────────┘  │
│       │            │                    │             │
│       └────────────┴────────────────────┘             │
│                    │                                  │
│            ┌───────┴────────┐                         │
│            │  SQLite (ORM)  │                         │
│            └────────────────┘                         │
└───────────────────────────────────────────────────────┘
```

### Data Flow — Vision Detection

```
Camera/Image Upload
       │
       ▼
  ┌──────────┐     ┌─────────────────────┐
  │  /detect  │────▶│  YOLOv8 Product     │──── products count
  │ endpoint  │     │  Detector Model     │
  └──────────┘     └─────────────────────┘
       │
       │           ┌─────────────────────┐
       └──────────▶│  YOLOv8 Empty Shelf │──── empty slots count
                   │  Detector Model     │
                   └─────────────────────┘
                            │
                            ▼
                   ┌─────────────────────┐
                   │ Compute Alert Level │
                   │ stock% = products / │
                   │    baseline_capacity │
                   └─────────┬───────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌───────────┐  ┌────────────┐
        │ Sync DB  │  │ Log Scan  │  │ Send Email │
        │ Product  │  │ to zone_  │  │ if Critical│
        │  stock   │  │   logs    │  │  (< 40%)   │
        └──────────┘  └───────────┘  └────────────┘
```

---

## 👥 Team

This project was created as a **Final Year Project (PFE)** at **École Supérieure de Technologie** by:

| Name | Role |
|------|------|
| **Kanar Khalid** | Project Developer |
| **Hamza Yahia** | Project Developer |
| **Marouane Rhazlani** | Project Developer |

---

## 📄 License

This project is developed for educational purposes as part of a Final Year Project (PFE).

---

<div align="center">

**Built with ❤️ by Kanar Khalid, Hamza Yahia & Marouane Rhazlani**

*École Supérieure de Technologie — 2025*

</div>
