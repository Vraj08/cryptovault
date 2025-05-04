from flask import Flask, request, make_response, redirect, render_template, g, abort, flash
from bin.user_service import get_user_with_credentials, logged_in
from flask_wtf.csrf import CSRFProtect  # Enables CSRF protection for all forms
from account_service import get_balance, do_transfer
from forms import TransferForm  # Secure WTForm with CSRF token and field validation

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursupersecrettokenhere'  # Required for CSRF protection and session security
csrf = CSRFProtect(app)  # Apply CSRF protection globally

@app.route("/", methods=['GET'])
def home():
    # Check if user has valid session (JWT stored in cookie)
    if not logged_in():
        return render_template("login.html")  # Redirect to login if not authenticated
    return redirect('/dashboard')

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    # Authenticate user and issue JWT if credentials are valid
    user = get_user_with_credentials(email, password)

    # User enumeration defense: always return same message for invalid login
    if not user:
        return render_template("login.html", error="Invalid credentials")

    # Set the token in an HTTP-only cookie to mitigate XSS risk
    response = make_response(redirect("/dashboard"))
    response.set_cookie("auth_token", user["token"], httponly=True, secure=False)
    return response, 303

@app.route("/dashboard", methods=['GET'])
def dashboard():
    if not logged_in():
        return render_template("login.html")
    # g.user is populated from the JWT after successful login
    return render_template("dashboard.html", email=g.user)

@app.route("/details", methods=['GET'])
def details():
    if not logged_in():
        return render_template("login.html")

    # Accept account number as a URL query parameter
    account_number = request.args['account']

    # Prevent XSS: all output is escaped by default in Jinja templates
    return render_template(
        "details.html", 
        user=g.user,
        account_number=account_number,
        balance=get_balance(account_number, g.user)  # Only show accounts owned by user
    )

@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    if not logged_in():
        return render_template("login.html")

    form = TransferForm()  # FlaskForm includes CSRF protection

    if form.validate_on_submit():
        source = form.source.data
        target = form.target.data
        amount = form.amount.data

        # Validate that source account belongs to current user
        available_balance = get_balance(source, g.user)
        if available_balance is None:
            form.source.errors.append("Account not found or not yours.")
        elif amount > available_balance:
            form.amount.errors.append("Insufficient funds.")
        elif not do_transfer(source, target, amount):
            form.amount.errors.append("Transfer failed.")
        else:
            flash("Transfer successful!")  # Use flash to provide feedback
            return render_template("transfer_success.html", amount=amount, source=source, target=target)


    return render_template("transfer.html", form=form)

@app.route("/logout", methods=['GET'])
def logout():
    # Clear session cookie
    response = make_response(redirect("/dashboard"))
    response.delete_cookie('auth_token')
    return response, 303

# ---------- Error Handling ----------

@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", message="Bad Request: " + str(e)), 400

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", message="Internal Server Error"), 500
