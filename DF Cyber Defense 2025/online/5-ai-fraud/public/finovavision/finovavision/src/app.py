from flask import Flask, render_template, request, jsonify, session, redirect
from biometric_auth import authenticate_user, process_transfer
import secrets
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

IMAGE_CACHE = {}


def load_customer_accounts():
    account_file_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "account.json"
    )
    try:
        with open(account_file_path, "r", encoding="utf-8") as f:
            accounts_data = json.load(f)

        customer_accounts = {}
        for username, account_info in accounts_data.items():
            customer_accounts[username] = {
                "balance": account_info["balance"],
                "name": account_info["name"],
                "id": account_info["id"],
                "image_path": account_info["image_path"],
            }

        return customer_accounts
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {}


CUSTOMER_ACCOUNTS = load_customer_accounts()


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    image_id = session.get("image_id")
    if image_id and image_id in IMAGE_CACHE:
        del IMAGE_CACHE[image_id]
    session.clear()
    return redirect("/")


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    image_data = data.get("image_data")

    if not image_data:
        return jsonify({"success": False, "error": "Authentication required"})

    auth_result = authenticate_user(image_data)

    if auth_result.get("authenticated"):
        user_id = auth_result.get("user_id")
        session["user_id"] = user_id
        session["authenticated"] = True
        
        image_id = str(uuid.uuid4())
        IMAGE_CACHE[image_id] = image_data
        session["image_id"] = image_id

        return jsonify({"success": True, "redirect": "/dashboard"})

    return jsonify({"success": False, "error": "Authentication failed"})


@app.route("/transfer", methods=["POST"])
def process_fund_transfer():
    if not session.get("authenticated"):
        return jsonify({"success": False, "error": "Authentication required"})

    data = request.json
    from_account = data.get("from_account")
    to_account = data.get("to_account")
    amount = data.get("amount", 0)
    image_id = session.get("image_id")
    image_data = IMAGE_CACHE.get(image_id) if image_id else None

    if not all([from_account, to_account]):
        return jsonify({"success": False, "error": "Missing information"})
    
    if not image_data:
        return jsonify({"success": False, "error": "Session expired"})

    if from_account == to_account:
        return jsonify({"success": False, "error": "Cannot transfer to yourself"})

    if not isinstance(amount, int) or amount <= 0:
        return jsonify({"success": False, "error": "Invalid amount"})
    
    from_balance = CUSTOMER_ACCOUNTS.get(from_account, {}).get("balance", 0)
    if amount > from_balance:
        return jsonify({"success": False, "error": "Insufficient funds"})

    transfer_result = process_transfer(from_account, to_account, amount, image_data)

    if transfer_result.get("success"):
        if from_account in CUSTOMER_ACCOUNTS and to_account in CUSTOMER_ACCOUNTS:
            CUSTOMER_ACCOUNTS[from_account]["balance"] -= amount
            CUSTOMER_ACCOUNTS[to_account]["balance"] += amount

        current_balance = CUSTOMER_ACCOUNTS.get(session.get("user_id"), {}).get(
            "balance", 0
        )

        session_user = session.get("user_id")
        flag = ""
        if from_account != session_user:
            flag = os.getenv("FLAG")

        return jsonify(
            {
                "success": True,
                "message": f"Transfer completed: ${amount} sent from {from_account} to {to_account}",
                "new_balance": current_balance,
                "flag": flag,
            }
        )

    return jsonify({"success": False, "error": "Transfer failed"})


@app.route("/account", methods=["GET"])
def get_account_info():
    if not session.get("authenticated"):
        return jsonify({"success": False, "error": "Authentication required"})

    user_id = session.get("user_id")
    
    account_info = CUSTOMER_ACCOUNTS.get(user_id, {})

    if not account_info:
        return jsonify({"success": False, "error": "Account not found"})

    return jsonify(
        {
            "success": True,
            "user_id": user_id,
            "balance": account_info.get("balance", 0),
            "name": account_info.get("name", "Unknown Customer"),
        }
    )


@app.route("/accounts", methods=["GET"])
def list_accounts():
    if not session.get("authenticated"):
        return jsonify({"success": False, "error": "Authentication required"})

    accounts_list = []
    for username, account_info in CUSTOMER_ACCOUNTS.items():
        accounts_list.append({
            "username": username,
            "name": account_info.get("name", "Unknown Customer"),
            "id": account_info.get("id", 0)
        })

    return jsonify({
        "success": True,
        "accounts": accounts_list
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10001)
