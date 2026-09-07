from flask import Flask, jsonify, render_template

app = Flask(__name__)


@app.get("/")
def home():
    return render_template(
        "index.html",
        title="Home",
        pipeline_ok=True,
    )


@app.get("/pipeline")
def pipeline():
    return render_template("pipeline.html", title="Pipeline")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "test-webapp"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
