import json
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

def carrega(path):
    with open(f"data/{path}.json", encoding="utf-8") as f:
        return json.load(f)

@app.route("/api/episodios-recentes")
def api_episodios():
    return jsonify(carrega("episodios-recentes"))

@app.route("/api/em-lancamento")
def api_lancamento():
    return jsonify(carrega("em-lancamento"))

@app.route("/api/destaques-semana")
def api_destaques():
    return jsonify(carrega("destaques-semana"))

@app.route("/api/animes")
def api_animes():
    return jsonify(carrega("anime_detalhes"))

# servir arquivos estáticos (HTML/CSS/JS) na pasta `static/`
@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def site(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
