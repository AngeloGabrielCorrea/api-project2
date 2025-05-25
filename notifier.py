import json
import html
import requests
import time
import os

TELEGRAM_TOKEN = "TOKEN_AQUI"
CHAT_ID = "-1002593094484"

ARQ_TODOS_ANIMES = "data/todos-animes.json"
ARQ_EPISODIOS_RECENTES = "data/episodios-recentes.json"
ARQ_DESTAQUES_SEMANA = "data/destaques-semana.json"
ARQ_EM_LANCAMENTO = "data/em-lancamento.json"

def carregar_json(caminho):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_json(dados, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def escape_html(texto):
    return html.escape(str(texto), quote=True)

def truncar_mensagem(mensagem, limite=3900):
    if len(mensagem) > limite:
        return mensagem[:limite]
    return mensagem

def detectar_novos(caminho, atuais, chave_link='link'):
    antigos = carregar_json(caminho)
    antigos_links = {item[chave_link] for item in antigos}
    novos = [item for item in atuais if item[chave_link] not in antigos_links]

    if novos:
        salvar_json(atuais, caminho)
    return novos

def detectar_novos_animes(novos, antigos):
    nomes_antigos = {a["nome"] for a in antigos}
    return [a for a in novos if a["nome"] not in nomes_antigos]

def formatar_mensagem(episodios=None, destaques=None, lancamentos=None, novos_animes=None):
    mensagem = ""

    if novos_animes:
        mensagem += "<b>📦 Animes Novos:</b>\n"
        for a in novos_animes:
            mensagem += f"- {escape_html(a['nome'])}\n"

    if episodios:
        mensagem += "\n<b>📺 Episódios Recentes:</b>\n"
        for ep in episodios:
            mensagem += f"- {escape_html(ep['nome'])} Episódio {escape_html(ep['episodio'])}\n"

    if destaques:
        mensagem += "\n<b>🔥 Destaques da Semana:</b>\n"
        for d in destaques:
            mensagem += f"- {escape_html(d['nome'])}\n"

    if lancamentos:
        mensagem += "\n<b>🚀 Em Lançamento:</b>\n"
        for l in lancamentos:
            mensagem += f"- {escape_html(l['nome'])}\n"

    if mensagem == "":
        mensagem = "<b>ℹ️ Nenhuma novidade encontrada nesta atualização.</b>"

    return mensagem

def enviar_telegram(mensagem, tentativas=3):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": truncar_mensagem(mensagem),
        "parse_mode": "HTML"
    }

    for tentativa in range(1, tentativas + 1):
        try:
            print(f"📩 Enviando notificação para o Telegram... (Tentativa {tentativa})")
            res = requests.post(url, data=payload)
            res.raise_for_status()
            print("✅ Notificação enviada com sucesso!")
            return True
        except requests.exceptions.HTTPError as e:
            print(f"❌ Erro HTTP (tentativa {tentativa}): {e} - Resposta: {res.text}")
            if res.status_code == 400:
                print("❌ Erro 400 - mensagem possivelmente mal formatada ou chat_id inválido.")
                break
        except Exception as e:
            print(f"❌ Erro ao enviar (tentativa {tentativa}): {e}")
        time.sleep(2)
    print("❌ Todas as tentativas falharam.")
    return False


if __name__ == "__main__":
    print("ℹ️ Este script notifier.py agora deve ser chamado APÓS a atualização dos JSONs (ex: via scheduler)")

    # Exemplo para testar localmente só para conferir os arquivos carregados:
    episodios = carregar_json(ARQ_EPISODIOS_RECENTES)
    destaques = carregar_json(ARQ_DESTAQUES_SEMANA)
    lancamentos = carregar_json(ARQ_EM_LANCAMENTO)
    animes = carregar_json(ARQ_TODOS_ANIMES)

    mensagem = formatar_mensagem(
        episodios=episodios,
        destaques=destaques,
        lancamentos=lancamentos,
        novos_animes=None  # Detecção de novos animes deve ser feita no scheduler, para evitar conflito
    )

    print(mensagem)
