import os
import json
from flask import Flask, jsonify, send_from_directory, request, abort

# 1) Garante que a pasta data/ exista
os.makedirs("data", exist_ok=True)

app = Flask(__name__, static_folder="static")

# 2) Segredo para proteger o scheduler
SCHEDULER_TOKEN = os.getenv("SCHEDULER_TOKEN", "SENHA")

# 3) Importa funções do scraper
from scraper import (
    get_all_animes,
    salvar_episodios_recentes_home,
    salvar_em_lancamento,
    salvar_destaques_semana
)

# 4) Endpoint para disparar o scheduler externamente
@app.route("/run-scheduler")
def run_scheduler_endpoint():
    token = request.args.get("token", "")
    if token != SCHEDULER_TOKEN:
        abort(401, "Token inválido")

    # Executa todo o fluxo de atualização
    todos_animes = get_all_animes()
    with open("data/todos-animes.json", "w", encoding="utf-8") as f:
        json.dump(todos_animes, f, indent=2, ensure_ascii=False)

    salvar_episodios_recentes_home()
    salvar_em_lancamento()
    salvar_destaques_semana()

    return jsonify({"status": "ok"})

# 5) Função de leitura com erro claro se faltar arquivo
def carrega(path):
    file_path = os.path.join("data", f"{path}.json")
    if not os.path.isfile(file_path):
        abort(404, description=f"{path}.json não encontrado.")
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)

# 6) Rotas da API
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
    return jsonify(carrega("todos-animes"))

# 7) Servir front-end estático
@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def site(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
