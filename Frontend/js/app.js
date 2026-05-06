// ── Toast notifications ──────────────────────────────────────────
function getToastContainer() {
    let c = document.getElementById("toast-container");
    if (!c) {
        c = document.createElement("div");
        c.id = "toast-container";
        c.className = "toast-container";
        document.body.appendChild(c);
    }
    return c;
}

export function toast(message, type = "default", duration = 3200) {
    const container = getToastContainer();
    const el = document.createElement("div");
    el.className = `toast ${type}`;

    const icons = {
        success: '<i class="fa-solid fa-circle-check" style="color:#16a34a"></i>',
        error:   '<i class="fa-solid fa-circle-xmark" style="color:#dc2626"></i>',
        warning: '<i class="fa-solid fa-triangle-exclamation" style="color:#ea580c"></i>',
        default: '<i class="fa-solid fa-circle-info" style="color:#16a34a"></i>'
    };
    el.innerHTML = `<span>${icons[type] || icons.default}</span> ${message}`;

    container.appendChild(el);
    setTimeout(() => {
        el.style.opacity = "0";
        el.style.transform = "translateX(20px)";
        el.style.transition = "all 0.3s";
        setTimeout(() => el.remove(), 300);
    }, duration);
}

// ── Cart (localStorage) ──────────────────────────────────────────
export function getCart() {
    return JSON.parse(localStorage.getItem("cart") || "[]");
}

export function saveCart(cart) {
    localStorage.setItem("cart", JSON.stringify(cart));
    updateCartBadge();
}

export function addToCart(product) {
    const cart = getCart();
    const existing = cart.find(i => i.product_id === product.id);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            product_id:   product.id,
            product_name: product.name,
            price:        product.price,
            quantity:     1
        });
    }
    saveCart(cart);
}

export function removeFromCart(productId) {
    saveCart(getCart().filter(i => i.product_id !== productId));
}

export function updateQty(productId, qty) {
    const cart = getCart().map(i =>
        i.product_id === productId ? { ...i, quantity: Math.max(1, qty) } : i
    );
    saveCart(cart);
}

export function clearCart() {
    localStorage.removeItem("cart");
    updateCartBadge();
}

export function getCartTotal() {
    return getCart().reduce((sum, i) => sum + i.price * i.quantity, 0);
}

export function getCartCount() {
    return getCart().reduce((sum, i) => sum + i.quantity, 0);
}

export function updateCartBadge() {
    const el = document.getElementById("cart-count");
    if (el) {
        const count = getCartCount();
        el.textContent = count;
        el.style.display = count > 0 ? "flex" : "none";
    }
}

// ── Navbar builder ────────────────────────────────────────────────
export function buildNavbar(activePage = "") {
    const user = JSON.parse(localStorage.getItem("user"));
    const isAdmin = user?.role === "admin";

    const nav = document.getElementById("navbar");
    if (!nav) return;

    const prefix = window.location.pathname.includes("/pages/") ? "" : "pages/";

    nav.className = "navbar";
    nav.innerHTML = `
        <a href="../index.html" class="nav-brand">
            <div class="brand-icon"><i class="fa-solid fa-cart-shopping" style="color:white;font-size:14px"></i></div>
            Smart Supermarket
        </a>
        <div class="nav-links">
            <a href="${prefix}products.html" class="nav-link ${activePage === 'products' ? 'active' : ''}">Products</a>
            ${user ? `<a href="${prefix}orders.html"  class="nav-link ${activePage === 'orders'   ? 'active' : ''}">My Orders</a>` : ''}
            ${isAdmin ? `<a href="${prefix}admin-dashboard.html" class="nav-link ${activePage === 'admin' ? 'active' : ''}"><i class="fa-solid fa-gear" style="font-size:12px;margin-right:4px"></i> Admin</a>` : ''}
        </div>
        <div class="nav-right">
            ${user
                ? `<a href="${prefix}cart.html" class="cart-btn">
                       <i class="fa-solid fa-cart-shopping"></i> Cart
                       <span class="cart-count" id="cart-count" style="display:none">0</span>
                   </a>
                   <span style="font-size:13px;color:var(--text-2)">Hi, <strong>${user.username}</strong></span>
                   <button onclick="logoutUser()" class="btn btn-outline btn-sm">Logout</button>`
                : `<a href="${prefix}login.html"    class="btn btn-outline btn-sm">Login</a>
                   <a href="${prefix}register.html" class="btn btn-primary btn-sm">Register</a>`
            }
        </div>
    `;

    updateCartBadge();
}

window.logoutUser = function () {
    localStorage.removeItem("user");
    localStorage.removeItem("cart");
    window.location.href = "../index.html";
};

// ── Format helpers ────────────────────────────────────────────────
export function formatPrice(n) {
    return Number(n).toLocaleString("fr-MA", { minimumFractionDigits: 2 }) + " MAD";
}

export function formatDate(str) {
    return new Date(str).toLocaleDateString("fr-MA", {
        day: "2-digit", month: "short", year: "numeric"
    });
}

export function stockBadge(stock) {
    if (stock === 0)  return `<span class="badge badge-red">Out of stock</span>`;
    if (stock <= 5)   return `<span class="badge badge-orange">Low: ${stock}</span>`;
    return `<span class="badge badge-green">${stock} in stock</span>`;
}

export function statusBadge(status) {
    return `<span class="badge status-${status}">${status}</span>`;
}

export function categoryEmoji(cat) {
    // Returns a small FA icon class name for the category
    const map = {
        "Dairy":         "fa-cow",
        "Bakery":        "fa-bread-slice",
        "Drinks":        "fa-mug-hot",
        "Pantry":        "fa-jar",
        "Fruits":        "fa-apple-whole",
        "Vegetables":    "fa-carrot",
        "Veggies":       "fa-carrot",
        "Meat":          "fa-drumstick-bite",
        "Fish":          "fa-fish",
        "Oils":          "fa-bottle-droplet",
        "Snacks":        "fa-cookie-bite",
        "Frozen":        "fa-snowflake",
        "Cleaning":      "fa-spray-can-sparkles",
        "Personal Care": "fa-pump-soap",
    };
    const icon = map[cat] || "fa-box";
    return `<i class="fa-solid ${icon}" style="font-size:14px;color:var(--primary)"></i>`;
}