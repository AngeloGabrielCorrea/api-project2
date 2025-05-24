import schedule
import time
import logging
import json
import os
from scraper import (
    get_episodios_recentes_home,
    get_animes_em_lancamento,
    get_destaques_semana,
    get_all_animes
)
from notifier import enviar_telegram, escape_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

ARQUIVO_ANIMES = "data/todos_animes.json"

def carregar_animes_antigos():
    if os.path.exists(ARQUIVO_ANIMES):
        with open(ARQUIVO_ANIMES, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_animes(atual):
    with open(ARQUIVO_ANIMES, "w", encoding="utf-8") as f:
        json.dump(atual, f, ensure_ascii=False, indent=2)

def formatar_bloco_animes_novos(novos_animes):
    texto = "<b>📦 Animes Novos:</b>\n"
    for a in novos_animes:
        texto += f"- {escape_html(a['nome'])}\n"
    return texto

def formatar_bloco_episodios(episodios):
    texto = "<b>📺 Episódios Recentes:</b>\n"
    for ep in episodios:
        texto += f"- {escape_html(ep['nome'])} Episódio {escape_html(ep['episodio'])}\n"
    return texto

def formatar_bloco_destaques(destaques):
    texto = "<b>🔥 Destaques da Semana:</b>\n"
    for d in destaques:
        texto += f"- {escape_html(d['nome'])}\n"
    return texto

def formatar_bloco_lancamentos(lancamentos):
    texto = "<b>🚀 Em Lançamento:</b>\n"
    for l in lancamentos:
        texto += f"- {escape_html(l['nome'])}\n"
    return texto

def job_full():
    logging.info("🔄 Iniciando atualização completa...")
    partes = []

    # Novos Animes
    try:
        animes_atual = get_all_animes()
        logging.info(f"Total de animes extraídos: {len(animes_atual)}")

        animes_antigos = carregar_animes_antigos()
        nomes_antigos = set(a["nome"] for a in animes_antigos)
        novos_animes = [a for a in animes_atual if a["nome"] not in nomes_antigos]

        if novos_animes:
            logging.info(f"{len(novos_animes)} animes novos encontrados")
            partes.append(formatar_bloco_animes_novos(novos_animes))
        else:
            logging.info("Nenhum anime novo encontrado.")

        salvar_animes(animes_atual)

    except Exception as e:
        logging.error("Erro ao obter ou salvar todos os animes", exc_info=e)
        partes.append("<b>📦 Animes Novos:</b> erro ao extrair.")

    # Episódios Recentes
    try:
        recentes = get_episodios_recentes_home()
        logging.info(f"Episódios recentes: {len(recentes)}")
        partes.append(formatar_bloco_episodios(recentes))
    except Exception as e:
        logging.error("Erro em episódios recentes", exc_info=e)
        partes.append("<b>📺 Episódios Recentes:</b> erro ao extrair.")

    # Destaques da Semana
    try:
        destaques = get_destaques_semana()
        logging.info(f"Destaques da semana: {len(destaques)}")
        partes.append(formatar_bloco_destaques(destaques))
    except Exception as e:
        logging.error("Erro em destaques da semana", exc_info=e)
        partes.append("<b>🔥 Destaques da Semana:</b> erro ao extrair.")

    # Em Lançamento
    try:
        lancamentos = get_animes_em_lancamento()
        logging.info(f"Animes em lançamento: {len(lancamentos)}")
        partes.append(formatar_bloco_lancamentos(lancamentos))
    except Exception as e:
        logging.error("Erro em em_lancamento", exc_info=e)
        partes.append("<b>🚀 Em Lançamento:</b> erro ao extrair.")

    mensagem = "<b>✅ Atualização concluída com sucesso!</b>\n\n" + "\n\n".join(partes)
    enviar_telegram(mensagem)

if __name__ == "__main__":
    schedule.every(1).minutes.do(job_full)
    logging.info("🤖 Scheduler iniciado.")
    job_full()  # Executa imediatamente

    while True:
        schedule.run_pending()
        time.sleep(30)
