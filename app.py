from flask import Flask, render_template, Blueprint, redirect, url_for
from flask_login import LoginManager, UserMixin, current_user

app = Flask(__name__)

#CHANGE LATER
app.config["SECRET_KEY"] = "secret-key"


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


class User(UserMixin):
    def __init__(self, id, username, role="customer"):
        self.id = id
        self.username = username
        self.role = role


@login_manager.user_loader
def load_user(user_id):
    # Temporary
    return None


main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("main/index.html")


auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.route("/login")
def login():
    return render_template("auth/login.html")


@auth.route("/register")
def register():
    return render_template("auth/register.html")


@auth.route("/logout")
def logout():
    return redirect(url_for("main.index"))


@auth.route("/profile")
def profile():
    return "Profile page - coming soon"


food = Blueprint("food", __name__, url_prefix="/food")


@food.route("/menu")
def menu():
    return "Menu page - coming soon"


delivery = Blueprint("delivery", __name__, url_prefix="/delivery")


@delivery.route("/")
def delivery_page():
    return "Delivery page - coming soon"

orders = Blueprint("orders", __name__, url_prefix="/orders")


@orders.route("/history")
def history():
    return "Order history - coming soon"


@orders.route("/cart")
def cart():
    return "Cart page - coming soon"



ai = Blueprint("ai", __name__, url_prefix="/ai")


@ai.route("/assistant")
def assistant():
    return "AI Assistant - coming soon"



admin = Blueprint("admin", __name__, url_prefix="/admin")


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


if __name__ == "__main__":
    app.run(debug=True)
