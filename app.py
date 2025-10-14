from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

BASE_URL = "https://dummyjson.com/products"

# --------------------- Simulated User Database ---------------------
users_db = {}  # key=email, value={username, password_hash}

# --------------------- Ensure Cart in Session ---------------------
@app.before_request
def ensure_cart():
    if "cart" not in session:
        session["cart"] = []

# --------------------- Home / Products ---------------------
@app.route("/")
def home():
    query = request.args.get("q", "")
    category = request.args.get("category", "")

    if category:
        res = requests.get(f"{BASE_URL}/category/{category}")
    elif query:
        res = requests.get(f"{BASE_URL}/search?q={query}")
    else:
        res = requests.get(f"{BASE_URL}?limit=20")

    products = res.json().get("products", [])
    return render_template("products.html", products=products, query=query, category=category)

# --------------------- Add to Cart ---------------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    res = requests.get(f"{BASE_URL}/{product_id}")
    product = res.json()

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
            "thumbnail": product["thumbnail"],
            "quantity": 1
        })

    session["cart"] = cart
    flash(f"Added {product['title']} to cart!")
    return redirect(url_for("home"))

# --------------------- Cart Page ---------------------
@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    for item in cart:
        if "quantity" not in item:
            item["quantity"] = 1
    total = sum(item["price"] * item["quantity"] for item in cart)
    session["cart"] = cart
    return render_template("cart.html", cart=cart, total=total)

# --------------------- Update Quantity ---------------------
@app.route("/increase/<int:product_id>")
def increase_quantity(product_id):
    cart = session.get("cart", [])
    for item in cart:
        if item["id"] == product_id:
            item["quantity"] += 1
            break
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/decrease/<int:product_id>")
def decrease_quantity(product_id):
    cart = session.get("cart", [])
    for item in cart:
        if item["id"] == product_id:
            item["quantity"] -= 1
            if item["quantity"] <= 0:
                cart.remove(item)
            break
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/remove/<int:product_id>")
def remove_item(product_id):
    cart = [item for item in session.get("cart", []) if item["id"] != product_id]
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/clear_cart")
def clear_cart():
    session.pop("cart", None)
    flash("Cart cleared!")
    return redirect(url_for("cart"))

# --------------------- Checkout ---------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart_items = session.get("cart", [])
    total = sum(item["price"] * item["quantity"] for item in cart_items)

    if not cart_items:
        flash("Your cart is empty!")
        return redirect(url_for("cart"))

    if request.method == "POST":
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
        flash("Please fill all fields!")
        return redirect(url_for("home"))

    if password != confirm_password:
        flash("Passwords do not match!")
        return redirect(url_for("home"))

    if email in users_db:
        flash("Email already registered!")
        return redirect(url_for("home"))

    users_db[email] = {
        "username": username,
        "password_hash": generate_password_hash(password),
    }
    session["user"] = username
    flash("Registration successful! You are logged in.")
    return redirect(url_for("home"))

# --------------------- Login ---------------------
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    user = users_db.get(email)
    if user and check_password_hash(user["password_hash"], password):
        session["user"] = user["username"]
        flash(f"Welcome {user['username']}!")
        return redirect(url_for("home"))
    else:
        flash("Invalid credentials!")
        return redirect(url_for("home"))
    
    # --------------------- Product Detail Page ---------------------
@app.route("/product/<int:product_id>")
def product_detail(product_id):
    res = requests.get(f"{BASE_URL}/{product_id}")
    product = res.json()
    return render_template("product_detail.html", product=product)


# --------------------- Buy Now ---------------------
@app.route("/buy_now/<int:product_id>")
def buy_now(product_id):
    res = requests.get(f"{BASE_URL}/{product_id}")
    product = res.json()

    # Save only this product to cart temporarily
    session["cart"] = [{
        "id": product["id"],
        "title": product["title"],
        "price": product["price"],
        "thumbnail": product["thumbnail"],
        "quantity": 1
    }]

    return redirect(url_for("checkout"))


# --------------------- Logout ---------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully!")
    return redirect(url_for("home"))

# --------------------- Run App ---------------------
if __name__ == "__main__":
    app.run(debug=True)
