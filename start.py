import subprocess
import sys
import time

print("="*60)
print("🧠 Launching Multi-Timeframe Trading Bot Suite on Liara Cloud 🧠")
print("="*60)

# 1. Start the trading bot scanner in the background
print("[System] Launching bot.py background market scanner...")
bot_process = subprocess.Popen([sys.executable, "bot.py"])

# Give the bot a moment to start and write initial status
time.sleep(2)

# 2. Start the Streamlit web dashboard in the foreground
# Binding to port 8000 (Liara's default proxy port)
print("[System] Launching dashboard.py Streamlit UI on Port 8000...")
try:
    subprocess.run([
        "streamlit", "run", "dashboard.py",
        "--server.port", "8000",
        "--server.address", "0.0.0.0",
        "--server.headless", "true"
    ])
except KeyboardInterrupt:
    print("[System] Shutting down services...")
    bot_process.terminate()
