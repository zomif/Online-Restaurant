import os
import time
import sqlite3
from dotenv import load_dotenv
from groq import Groq
from werkzeug.utils import secure_filename
from flask import Flask, render_template, Blueprint, redirect, url_for, request, flash, session, jsonify
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from database.restaurant_db import db, FoodItem, User, Order, OrderItem
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

load_dotenv()

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "4815030a019b690c80146c93ccbba37544504242f7e019f21be6622a7eefff55")

csrf = CSRFProtect(app)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        session.permanent = True
        login_user(user, remember=True)

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

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_email = request.form.get('email')
        if new_email:
            current_user.email = new_email

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename != '':
                allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
                extension = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''

                if extension not in allowed_extensions:
                    flash("Invalid profile picture format. Use PNG, JPG, JPEG, or WEBP.", "danger")
                    return redirect(url_for('auth.profile'))

                raw_filename = secure_filename(file.filename)
                unique_filename = f"{int(time.time())}_{raw_filename}"
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, unique_filename))
                current_user.profile_picture = unique_filename

        db.session.add(current_user)
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('auth.profile'))

    return render_template('account/profile.html')

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

@ai.route("/assistant")
def assistant():
    return render_template("ai/assistant.html")

@ai.route("/chat", methods=["POST"])
@csrf.exempt
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Please enter a message."}), 400

    if not os.getenv("GROQ_API_KEY"):
        return jsonify({"error": "GROQ_API_KEY is missing. Add it to your .env file."}), 500

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the friendly AI food assistant for Tasty Bytes, an online restaurant. "
                        "Help users choose food, compare meals, suggest options by budget, and answer restaurant questions. "
                        "Try to make your answears clear and short and if you cant you can use more text"
                        "Keep answers concise.\n\n"
                        "Here is our official menu:\n"
                        "1. Cheeseburger (Burgers) - $8.99\n"
                        "   Description: Juicy beef patty with cheddar, lettuce, and tomato.\n"
                        "2. Pepperoni Pizza (Pizza) - $14.50\n"
                        "   Description: Crispy crust topped with mozzarella and pepperoni.\n"
                        "3. Ultimate Bacon Cheeseburger (Burgers) - $13.99\n"
                        "   Description: A thick, juicy flame-grilled beef patty topped with melted cheddar cheese, crispy smoked bacon, fresh crisp lettuce, and a ripe tomato slice, all stacked inside a soft toasted sesame seed bun.\n"
                        "4. Golden Crispy French Fries with ketchup (Sides) - $4.99\n"
                         "   Description: Hand-cut, golden-crisp potatoes lightly seasoned with sea salt and served hot. The perfect crunchy companion to any burger or sandwich"
                        "Never recommend or claim an item exists unless it is explicitly listed on this menu text."
                    ),
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
        )
        return jsonify({
            "response": response.choices[0].message.content
        })

    except Exception as e:
        print("GROQ ERROR:", repr(e))
        return jsonify({"error": str(e)}), 500

@orders.route("/history")
@login_required
def history():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders/history.html", orders=user_orders)

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

    new_order = Order(
        user_id=current_user.id,
        total_price=0.0,
        status="Delivered"
    )
    db.session.add(new_order)
    db.session.flush()

    total_price = 0.0

    for food_id_str, quantity in cart.items():
        food = db.session.get(FoodItem, int(food_id_str))
        if food:
            item_price = food.price * quantity
            total_price += item_price

            order_item = OrderItem(
                order_id=new_order.id,
                food_id=food.id,
                quantity=quantity,
                price_at_purchase=food.price
            )
            db.session.add(order_item)

    new_order.total_price = total_price
    db.session.commit()

    session.pop("cart", None)
    flash("🎉 Order placed successfully! Thank you for your purchase.", "success")
    return redirect(url_for("main.index"))

@orders.route("/reorder/<int:order_id>", methods=["POST"])
@login_required
def reorder(order_id):
    past_order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()

    if not past_order:
        flash("Order not found.", "danger")
        return redirect(url_for("orders.history"))

    cart = session.get("cart", {})

    for item in past_order.items:
        str_id = str(item.food_id)
        current_qty = cart.get(str_id, 0)
        cart[str_id] = min(current_qty + item.quantity, 10)

    session["cart"] = cart
    session.modified = True

    flash("Items from your past order have been added to your cart!", "success")
    return redirect(url_for("orders.cart"))

@admin.route("/")
def dashboard():
    return "Admin dashboard - coming soon"

app.register_blueprint(main)
app.register_blueprint(auth)
app.register_blueprint(food)
app.register_blueprint(orders)
app.register_blueprint(ai)
app.register_blueprint(admin)

with app.app_context():
    db.create_all()

    db_file_path = os.path.join(basedir, "database", "restaurant.db")
    if os.path.exists(db_file_path):
        try:
            conn = sqlite3.connect(db_file_path)
            cursor = conn.cursor()
            cursor.execute("ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255);")
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            pass

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
