from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from requests.exceptions import RequestException
import os
from sqlalchemy.exc import OperationalError

app = Flask(__name__)
app.secret_key = "secret123"

# --------------------- Database Config ---------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

BASE_URL = "https://dummyjson.com/products"

# --------------------- Fallback Products ---------------------
FALLBACK_PRODUCTS = [
    {"id": 1, "title": "Sample Product 1", "price": 100, "thumbnail": "/static/img1.jpg"},
    {"id": 2, "title": "Sample Product 2", "price": 200, "thumbnail": "/static/img2.jpg"},
    {"id": 3, "title": "Sample Product 3", "price": 300, "thumbnail": "/static/img3.jpg"},
]

# --------------------- DATABASE MODELS ---------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    price = db.Column(db.Float)
    thumbnail = db.Column(db.String(300))
    quantity = db.Column(db.Integer, default=1)

# --------------------- Helpers ---------------------
@app.before_request
def ensure_cart():
    if "cart" not in session:
        session["cart"] = []

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

def safe_commit():
    try:
        db.session.commit()
    except OperationalError:
        db.session.rollback()
        flash("Database busy. Try again!")

def fetch_products(endpoint):
    """Fetch products from DummyJSON safely with fallback"""
    try:
        res = requests.get(endpoint, timeout=5)
        res.raise_for_status()
        return res.json().get("products", [])
    except RequestException:
        flash("Could not fetch products from API. Showing fallback products.")
        return FALLBACK_PRODUCTS

def fetch_product(product_id):
    """Fetch single product safely with fallback"""
    try:
        res = requests.get(f"{BASE_URL}/{product_id}", timeout=5)
        res.raise_for_status()
        return res.json()
    except RequestException:
        flash("Could not fetch product details. Showing fallback product.")
        # Return first fallback product for demo
        fallback = next((p for p in FALLBACK_PRODUCTS if p["id"] == product_id), FALLBACK_PRODUCTS[0])
        return fallback

# --------------------- Home / Products ----------------------------
@app.route("/")
def home():
    query = request.args.get("q", "")
    category = request.args.get("category", "")

    if category:
        products = fetch_products(f"{BASE_URL}/category/{category}")
    elif query:
        products = fetch_products(f"{BASE_URL}/search?q={query}")
    else:
        products = fetch_products(f"{BASE_URL}?limit=20")

    return render_template("products.html", products=products, query=query, category=category)

# --------------------- Add to Cart ---------------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    username = session.get("user")
    product = fetch_product(product_id)

    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            db_item = CartItem.query.filter_by(user_id=user.id, product_id=product_id).first()
            if db_item:
                db_item.quantity += 1
            else:
                db_item = CartItem(
                    user_id=user.id,
                    product_id=product["id"],
                    title=product["title"],
                    price=product["price"],
                    thumbnail=product.get("thumbnail", ""),
                    quantity=1
                )
                db.session.add(db_item)
            safe_commit()
    else:
        # Guest cart in session
        cart = session.get("cart", [])
        for item in cart:
            if item["id"] == product["id"]:
                item["quantity"] += 1
                break
        else:
            cart.append({
                "id": product["id"],
                "title": product["title"],
                "price": product["price"],
                "thumbnail": product.get("thumbnail", ""),
                "quantity": 1
            })
        session["cart"] = cart

    flash(f"Added {product['title']} to cart!")
    return redirect(url_for("home"))

# --------------------- Cart Page ---------------------
@app.route("/cart")
def cart():
    username = session.get("user")
    if username:
        user = User.query.filter_by(username=username).first()
        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        cart_items = [{
            "id": item.product_id,
            "title": item.title,
            "price": item.price,
            "thumbnail": item.thumbnail,
            "quantity": item.quantity
        } for item in cart_items]
    else:
        cart_items = session.get("cart", [])

    total = sum(item["price"] * item["quantity"] for item in cart_items)
    return render_template("cart.html", cart=cart_items, total=total)

# --------------------- Update Quantity ---------------------
@app.route("/increase/<int:product_id>")
def increase_quantity(product_id):
    username = session.get("user")
    if username:
        user = User.query.filter_by(username=username).first()
        item = CartItem.query.filter_by(user_id=user.id, product_id=product_id).first()
        if item:
            item.quantity += 1
            safe_commit()
    else:
        cart = session.get("cart", [])
        for item in cart:
            if item["id"] == product_id:
                item["quantity"] += 1
                break
        session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/decrease/<int:product_id>")
def decrease_quantity(product_id):
    username = session.get("user")
    if username:
        user = User.query.filter_by(username=username).first()
        item = CartItem.query.filter_by(user_id=user.id, product_id=product_id).first()
        if item:
            item.quantity -= 1
            if item.quantity <= 0:
                db.session.delete(item)
            safe_commit()
    else:
        cart = session.get("cart", [])
        for item in cart:
            if item["id"] == product_id:
                item["quantity"] -= 1
                if item["quantity"] <= 0:
                    cart.remove(item)
                break
        session["cart"] = cart
    return redirect(url_for("cart"))

# --------------------- Remove Item ---------------------
@app.route("/remove/<int:product_id>")
def remove_item(product_id):
    username = session.get("user")
    if username:
        user = User.query.filter_by(username=username).first()
        item = CartItem.query.filter_by(user_id=user.id, product_id=product_id).first()
        if item:
            db.session.delete(item)
            safe_commit()
    else:
        cart = [item for item in session.get("cart", []) if item["id"] != product_id]
        session["cart"] = cart
    return redirect(url_for("cart"))

# --------------------- Clear Cart ---------------------
@app.route("/clear_cart")
def clear_cart():
    username = session.get("user")
    if username:
        user = User.query.filter_by(username=username).first()
        CartItem.query.filter_by(user_id=user.id).delete()
        safe_commit()
    session.pop("cart", None)
    flash("Cart cleared!")
    return redirect(url_for("cart"))

# --------------------- Navbar Cart Count ---------------------
@app.context_processor
def cart_count():
    username = session.get("user")
    count = 0
    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            count = db.session.query(db.func.sum(CartItem.quantity)).filter_by(user_id=user.id).scalar() or 0
    else:
        cart = session.get("cart", [])
        count = sum(item["quantity"] for item in cart)
    return dict(cart_count=count)

# --------------------- Checkout ---------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    username = session.get("user")
    if username:
        user = User.query.filter_by(username=username).first()
        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        cart_items = [{
            "id": item.product_id,
            "title": item.title,
            "price": item.price,
            "thumbnail": item.thumbnail,
            "quantity": item.quantity
        } for item in cart_items]
    else:
        cart_items = session.get("cart", [])

    total = sum(item["price"] * item["quantity"] for item in cart_items)

    if not cart_items:
        flash("Your cart is empty!")
        return redirect(url_for("cart"))

    if request.method == "POST":
        if username:
            CartItem.query.filter_by(user_id=user.id).delete()
            safe_commit()
        session["cart"] = []
        flash("Payment Successful! 🎉")
        return render_template("checkout_success.html", total=total)

    return render_template("checkout.html", cart=cart_items, total=total)

# --------------------- Register ---------------------
@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not all([username, email, password, confirm_password]):
        return jsonify({"status": "error", "message": "Please fill all fields!"})

    if password != confirm_password:
        return jsonify({"status": "error", "message": "Passwords do not match!"})

    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered!"})

    new_user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(new_user)
    safe_commit()
    session["user"] = username

    return jsonify({"status": "success", "message": "Registration successful! Logged in."})

# --------------------- Login ---------------------
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"status": "error", "message": "User not found! Please sign up first."})

    if not check_password_hash(user.password_hash, password):
        return jsonify({"status": "error", "message": "Invalid password! Please try again."})

    session["user"] = user.username
    return jsonify({"status": "success", "message": f"Welcome {user.username}!"})


# --------------------- Product Detail ---------------------
@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = fetch_product(product_id)
    return render_template("product_detail.html", product=product)

# --------------------- Buy Now ---------------------
@app.route("/buy_now/<int:product_id>")
def buy_now(product_id):
    product = fetch_product(product_id)
    username = session.get("user")

    if username:
        user = User.query.filter_by(username=username).first()
        CartItem.query.filter_by(user_id=user.id).delete()
        db.session.add(CartItem(
            user_id=user.id,
            product_id=product["id"],
            title=product["title"],
            price=product["price"],
            thumbnail=product.get("thumbnail", ""),
            quantity=1
        ))
        safe_commit()
    else:
        session["cart"] = [{
            "id": product["id"],
            "title": product["title"],
            "price": product["price"],
            "thumbnail": product.get("thumbnail", ""),
            "quantity": 1
        }]
    return redirect(url_for("checkout"))

# --------------------- Logout ---------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully!")
    return redirect(url_for("home"))

# --------------------- Debug ---------------------
@app.route("/view_data")
def view_data():
    users = User.query.all()
    cart_items = CartItem.query.all()
    return jsonify({
        "users": [{"id": u.id, "username": u.username, "email": u.email} for u in users],
        "cart_items": [{"user_id": c.user_id, "title": c.title, "price": c.price, "quantity": c.quantity} for c in cart_items]
    })

# --------------------- Run App ---------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database path:", os.path.abspath("products.db"))
    app.run(debug=True)

