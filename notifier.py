import json
import html
import requests
import time
import os
from scraper import get_all_animes, get_episodios_recentes_home, get_destaques_semana, get_animes_em_lancamento

TELEGRAM_TOKEN = "7729721572:AAGn_ASg3WXEAfPG9_1U1gTCQCwihcayc98"
CHAT_ID = "-1002593094484"

# --- Arquivos para armazenar dados ---
ARQ_TODOS_ANIMES = "data/todos_animes.json"
ARQ_EPISODIOS_RECENTES = "data/episodios-recentes.json"
ARQ_DESTAQUES_SEMANA = "data/destaques-semana.json"
ARQ_EM_LANCAMENTO = "data/em-lancamento.json"

# --- Funções para JSON ---

def carregar_json(caminho):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_json(dados, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

# --- Escapa texto para HTML ---

def escape_html(texto):
    return html.escape(str(texto), quote=True)

# --- Trunca mensagem para evitar erro 400 do Telegram (máx 4096 caracteres, deixando margem) ---

def truncar_mensagem(mensagem, limite=3900):
    if len(mensagem) > limite:
        return mensagem[:limite] #+ "\n... (mensagem truncada)"
    return mensagem

# --- Salvar e detectar novos itens ---

def detectar_novos(caminho, atuais, chave_link='link'):
    antigos = carregar_json(caminho)
    antigos_links = {item[chave_link] for item in antigos}
    novos = [item for item in atuais if item[chave_link] not in antigos_links]

    if novos:
        salvar_json(atuais, caminho)
    return novos

# --- Função para detectar novos animes pelo nome (no arquivo todos_animes.json) ---

def detectar_novos_animes(novos, antigos):
    nomes_antigos = {a["nome"] for a in antigos}
    return [a for a in novos if a["nome"] not in nomes_antigos]

# --- Formata a mensagem com HTML ---

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

# --- Envia mensagem para Telegram com retry ---

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

# --- Main ---

if __name__ == "__main__":
    print("🔄 Extraindo dados...")

    # Todos animes atuais e antigos
    animes_atuais = get_all_animes()
    animes_antigos = carregar_json(ARQ_TODOS_ANIMES)

    # Detectar animes novos
    novos_animes = detectar_novos_animes(animes_atuais, animes_antigos)

    # Salvar lista completa atualizada
    salvar_json(animes_atuais, ARQ_TODOS_ANIMES)

    # Detectar novos episódios, destaques e lançamentos
    novos_episodios = detectar_novos(ARQ_EPISODIOS_RECENTES, get_episodios_recentes_home())
    novos_destaques = detectar_novos(ARQ_DESTAQUES_SEMANA, get_destaques_semana())
    novos_lancamentos = detectar_novos(ARQ_EM_LANCAMENTO, get_animes_em_lancamento())

    # Montar mensagem
    mensagem = formatar_mensagem(
        episodios=novos_episodios,
        destaques=novos_destaques,
        lancamentos=novos_lancamentos,
        novos_animes=novos_animes
    )

    # Enviar só se houver alguma novidade
    if novos_animes or novos_episodios or novos_destaques or novos_lancamentos:
        enviar_telegram(mensagem)
    else:
        print("ℹ️ Nenhuma novidade para enviar.")

    print("\n📊 Processo concluído.")
