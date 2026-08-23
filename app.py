import os
from datetime import timedelta
from flask import Flask, render_template, Blueprint, redirect, url_for, request, flash, session
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from database.restaurant_db import db, FoodItem, User

app = Flask(__name__)
app.config["SECRET_KEY"] = "4815030a019b690c80146c93ccbba37544504242f7e019f21be6622a7eefff55"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "database", "restaurant.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

main = Blueprint("main", __name__)
auth = Blueprint("auth", __name__, url_prefix="/auth")
food = Blueprint("food", __name__, url_prefix="/food")
delivery = Blueprint("delivery", __name__, url_prefix="/delivery")
orders = Blueprint("orders", __name__, url_prefix="/orders")
ai = Blueprint("ai", __name__, url_prefix="/ai")
admin = Blueprint("admin", __name__, url_prefix="/admin")

@main.route("/")
def index():
    items = FoodItem.query.all()
    return render_template("main/index.html", items=items)

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()

        session.permanent = True
        login_user(user, remember=True)

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user)
        flash("Logged in successfully!", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/login.html")

@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("Email already registered.", "danger")
            return redirect(url_for("auth.register"))

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))

@auth.route("/profile")
def profile():
    return "Profile page - coming soon"

@auth.route('/policy')
def policy():
    return render_template('auth/policy.html')

@food.route("/menu")
def menu():
    items = FoodItem.query.all()
    return render_template("food/menu.html", items=items)

@food.route("/add_food", methods=["GET", "POST"])
def add_food():
    if request.method == "POST":
        name = request.form.get("name")
        category = request.form.get("category")
        price = float(request.form.get("price", 0))
        description = request.form.get("description")
        image_url = request.form.get("image_url")

        new_item = FoodItem(
            name=name,
            category=category,
            price=price,
            description=description,
            image_url=image_url
        )
        db.session.add(new_item)
        db.session.commit()
        flash(f"Added '{name}' successfully!", "success")
        return redirect(url_for("food.add_food"))

    items = FoodItem.query.all()
    return render_template("food/food.html", items=items)

@food.route("/food/delete/<int:food_id>", methods=["POST"])
def delete_food(food_id):
    food_item = db.session.get(FoodItem, food_id)
    if food_item:
        db.session.delete(food_item)
        db.session.commit()
        flash(f"Deleted '{food_item.name}' successfully!", "info")
    return redirect(url_for("food.add_food"))

@delivery.route("/")
def delivery_page():
    return "Delivery page - coming soon"

@orders.route("/history")
def history():
    return "Order history - coming soon"

@orders.route("/cart")
@login_required
def cart():
    cart_data = session.get("cart", {})
    cart_items = []
    total_price = 0.0

    for food_id, quantity in cart_data.items():
        food = db.session.get(FoodItem, int(food_id))
        if food:
            subtotal = food.price * quantity
            total_price += subtotal
            cart_items.append({
                "food": food,
                "quantity": quantity,
                "subtotal": subtotal
            })

    return render_template("cart/cart.html", items=cart_items, total=total_price)

@orders.route("/cart/add/<int:food_id>", methods=["POST"])
@login_required
def add_to_cart(food_id):
    food = db.session.get(FoodItem, food_id)
    if not food:
        flash("Item not found.", "danger")
        return redirect(url_for("food.menu"))

    cart = session.get("cart", {})
    str_id = str(food_id)
    current_qty = cart.get(str_id, 0)

    if current_qty >= 10:
        flash("Maximum limit of 10 items per product reached!", "warning")
    else:
        cart[str_id] = current_qty + 1
        session["cart"] = cart
        session.modified = True
        flash(f"Added {food.name} to cart!", "success")

    return redirect(url_for("food.menu"))

@orders.route("/cart/update/<int:food_id>", methods=["POST"])
@login_required
def update_cart(food_id):
    cart = session.get("cart", {})
    str_id = str(food_id)
    new_qty = int(request.form.get("quantity", 1))

    if new_qty < 1:
        new_qty = 1
    elif new_qty > 10:
        new_qty = 10
        flash("Maximum limit is 10 items per product.", "warning")

    if str_id in cart:
        cart[str_id] = new_qty
        session["cart"] = cart
        session.modified = True

    return redirect(url_for("orders.cart"))

@orders.route("/cart/remove/<int:food_id>", methods=["POST"])
@login_required
def remove_from_cart(food_id):
    cart = session.get("cart", {})
    str_id = str(food_id)
    if str_id in cart:
        del cart[str_id]
        session["cart"] = cart
        session.modified = True
        flash("Item removed from cart.", "info")
    return redirect(url_for("orders.cart"))

@orders.route("/cart/clear", methods=["POST"])
@login_required
def clear_cart():
    session.pop("cart", None)
    flash("Cart cleared.", "info")
    return redirect(url_for("orders.cart"))

@orders.route("/cart/checkout", methods=["POST"])
@login_required
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty!", "danger")
        return redirect(url_for("orders.cart"))

    session["cart"] = {}
    session.modified = True
    flash("🎉 Order placed successfully! Thank you for your purchase.", "success")
    return redirect(url_for("main.index"))

@ai.route("/assistant")
def assistant():
    return "AI Assistant - coming soon"

@admin.route("/")
def dashboard():
    return "Admin dashboard - coming soon"

app.register_blueprint(main)
app.register_blueprint(auth)
app.register_blueprint(food)
app.register_blueprint(delivery)
app.register_blueprint(orders)
app.register_blueprint(ai)
app.register_blueprint(admin)

with app.app_context():
    db.create_all()

    if not FoodItem.query.first():
        default_items = [
            FoodItem(
                name="Cheeseburger",
                description="Juicy beef patty with cheddar, lettuce, and tomato.",
                price=8.99,
                category="Burgers",
                image_url="https://images.unsplash.com/photo-1568901346375-23c9450c58cd"
            ),
            FoodItem(
                name="Pepperoni Pizza",
                description="Crispy crust topped with mozzarella and pepperoni.",
                price=14.50,
                category="Pizza",
                image_url="https://images.unsplash.com/photo-1628840042765-356cda07504e"
            )
        ]
        db.session.add_all(default_items)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
