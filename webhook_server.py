# webhook_server.py
from flask import Flask, request, jsonify
import asyncio
import importlib.util
import threading
import os

# Dynamically import bot.py if it exists
BOT_MODULE_NAME = "bot"
BOT_FILENAME = "bot.py"

spec = importlib.util.spec_from_file_location(BOT_MODULE_NAME, BOT_FILENAME)
if spec is None or not os.path.exists(BOT_FILENAME):
    raise ImportError(f"Cannot find module '{BOT_FILENAME}'")

bot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_module)

app = Flask(__name__)

# Run the bot in a background thread
def run_discord_bot():
    asyncio.run(bot_module.main())

threading.Thread(target=run_discord_bot, daemon=True).start()

@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    username = data.get('username')
    user_id = data.get('discord_id')
    cart = data.get('cart', [])
    total = data.get('total', "0.00")

    if not username or not user_id:
        return jsonify({"error": "Missing data"}), 400

    future = asyncio.run_coroutine_threadsafe(
        bot_module.handle_checkout(username, user_id, cart, total),
        bot_module.bot_loop
    )
    try:
        future.result()
        return jsonify({"message": "Checkout processed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/set_lang', methods=['POST'])
def set_lang():
    data = request.json
    lang = data.get('lang', 'ar')
    if lang not in ['ar', 'en']:
        return jsonify({"error": "Invalid language"}), 400
    bot_module.current_lang = lang
    return jsonify({"message": f"Language set to {lang}"}), 200

if __name__ == '__main__':
    app.run(port=5040)
