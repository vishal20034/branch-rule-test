from flask import Flask
app = Flask(__name__)

@app.get("/")
def home():
    return "GoCD deploy OK - test-webapp"

@app.get("/health")
def health():
    return {"status": "ok"}
