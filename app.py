from flask import Flask, render_template 
from flask import redirect 

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static"
)


@app.route("/")
def index():
    return render_template("index.html")




@app.route("/menu")
def menu():
    return render_template("menu.html")



@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")
    
    

if __name__ == "__main__":
    app.run(debug=True)
