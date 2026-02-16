from flask import Flask, request
import json
import requests
import os
from telegram import Bot

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(BOT_TOKEN)


@app.route("/")
def home():
    return "Bot is running"


def load_users():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_users(data):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_payments():
    try:
        with open("payments.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_payments(data):
    with open("payments.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/tetra_callback", methods=["POST"])
def tetra_callback():
    data = request.json
    print("Callback:", data)

    status = data.get("status")
    hashid = data.get("hashid")
    authority = data.get("authority")

    if status != 100:
        return "FAILED", 400

    verify_url = "https://api.tetra98.ir/api/PaymentVerification"
    payload = {"hashid": hashid, "authority": authority}

    try:
        verify_response = requests.post(verify_url, json=payload, timeout=40)
        verify_response.raise_for_status()
        verify_data = verify_response.json()
    except Exception as e:
        print("VERIFY ERROR:", e)
        return "VERIFY FAILED", 400

    if verify_data.get("Status") != 100:
        return "NOT VERIFIED", 400

    try:
        payments = load_payments()
        users = load_users()

        parts = hashid.split("_")
        user_id = parts[1]

        payment = payments.get(hashid)
        if not payment:
            return "PAYMENT NOT FOUND", 400

        if payment.get("status") == "approved":
            return "ALREADY DONE", 200

        amount_toman = payment["amount"]

        users.setdefault(user_id, {"balance": 0})
        users[user_id]["balance"] += amount_toman

        payment["status"] = "approved"

        save_users(users)
        save_payments(payments)

        bot.send_message(
            chat_id=int(user_id),
            text=f"✅ پرداخت با موفقیت انجام شد\n💰 {amount_toman:,} تومان به کیف پول شما اضافه شد."
        )

        return "OK", 200

    except Exception as e:
        print("FINAL ERROR:", e)
        return "ERROR", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
