from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "atm_secret"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="bank_system"
)

# ---------------- HOME ----------------


@app.route("/")
def login():
    return render_template("login.html")


# ---------------- REGISTER ----------------

@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/create_account", methods=["POST"])
def create_account():

    name = request.form["name"]
    username = request.form["username"]
    password = request.form["password"]
    confirm = request.form["confirm_password"]

    if password != confirm:
        return "Password not match"

    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO users(name,username,password) VALUES(%s,%s,%s)",
        (name, username, password)
    )

    db.commit()

    return redirect(url_for("login"))


# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def do_login():

    username = request.form["username"]
    password = request.form["password"]

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, password)
    )

    user = cursor.fetchone()

    if user:
        session["user_id"] = user["id"]
        return redirect(url_for("dashboard"))

    return "Login Failed"


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    # user
    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (session["user_id"],)
    )
    user = cursor.fetchone()

    # accounts
    cursor.execute(
        "SELECT * FROM accounts WHERE user_id=%s",
        (session["user_id"],)
    )
    accounts = cursor.fetchall()

    # total money (เฉพาะ user)
    cursor.execute(
        "SELECT SUM(balance) AS total FROM accounts WHERE user_id=%s",
        (session["user_id"],)
    )
    total_money = cursor.fetchone()["total"] or 0

    # transactions
    cursor.execute("""
        SELECT * FROM transactions
        WHERE account_number IN
        (SELECT account_number FROM accounts WHERE user_id=%s)
        ORDER BY time DESC
    """, (session["user_id"],))

    transactions = cursor.fetchall()

    return render_template(
        "dashboard.html",
        user=user,
        accounts=accounts,
        total_money=total_money,
        transactions=transactions
    )


# ---------------- CREATE BANK ACCOUNT ----------------

@app.route("/create_bank_account", methods=["POST"])
def create_bank_account():

    account_number = request.form["account_number"]

    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO accounts(account_number,user_id,balance) VALUES(%s,%s,0)",
        (account_number, session["user_id"])
    )

    db.commit()

    return redirect(url_for("dashboard"))


# ---------------- DEPOSIT ----------------

@app.route("/deposit", methods=["POST"])
def deposit():

    account = request.form["account"]
    amount = request.form["amount"]

    # ตรวจสอบว่าเป็นตัวเลข
    if not amount.isdigit():
        return redirect(url_for("dashboard"))

    amount = int(amount)

    if amount <= 0:
        return redirect(url_for("dashboard"))

    cursor = db.cursor()

    cursor.execute(
        "UPDATE accounts SET balance=balance+%s WHERE account_number=%s",
        (amount, account)
    )

    cursor.execute(
        "INSERT INTO transactions(account_number,type,amount) VALUES(%s,'deposit',%s)",
        (account, amount)
    )

    db.commit()

    return redirect(url_for("dashboard"))


# ---------------- WITHDRAW ----------------

@app.route("/withdraw", methods=["POST"])
def withdraw():

    account = request.form["account"]
    amount = request.form["amount"]

    if not amount.isdigit():
        return redirect(url_for("dashboard"))

    amount = int(amount)

    if amount <= 0:
        return redirect(url_for("dashboard"))

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT balance FROM accounts WHERE account_number=%s",
        (account,)
    )

    result = cursor.fetchone()

    if not result:
        return redirect(url_for("dashboard"))

    balance = result["balance"]

    if balance >= amount:

        cursor = db.cursor()

        cursor.execute(
            "UPDATE accounts SET balance=balance-%s WHERE account_number=%s",
            (amount, account)
        )

        cursor.execute(
            "INSERT INTO transactions(account_number,type,amount) VALUES(%s,'withdraw',%s)",
            (account, amount)
        )

        db.commit()

    return redirect(url_for("dashboard"))


# ---------------- TRANSFER ----------------

@app.route("/transfer", methods=["POST"])
def transfer():

    source = request.form["source_account"]
    target = request.form["target_account"]
    amount = request.form["amount"]

    if not amount.isdigit():
        return redirect(url_for("dashboard"))

    amount = int(amount)

    if amount <= 0:
        return redirect(url_for("dashboard"))

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT balance FROM accounts WHERE account_number=%s",
        (source,)
    )

    result = cursor.fetchone()

    if not result:
        return redirect(url_for("dashboard"))

    balance = result["balance"]

    if balance >= amount:

        cursor = db.cursor()

        cursor.execute(
            "UPDATE accounts SET balance=balance-%s WHERE account_number=%s",
            (amount, source)
        )

        cursor.execute(
            "UPDATE accounts SET balance=balance+%s WHERE account_number=%s",
            (amount, target)
        )

        cursor.execute("""
            INSERT INTO transactions(account_number,type,amount,target_account)
            VALUES(%s,'transfer',%s,%s)
        """, (source, amount, target))

        db.commit()

    return redirect(url_for("dashboard"))


# ---------------- DELETE ACCOUNT ----------------

@app.route("/delete_account/<account>")
def delete_account(account):

    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM accounts WHERE account_number=%s",
        (account,)
    )

    db.commit()

    return redirect(url_for("dashboard"))


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
