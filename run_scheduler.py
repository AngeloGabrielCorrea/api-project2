import schedule
import time
import logging
import json
import os
from scraper import (
    get_all_animes,
    salvar_episodios_recentes_home,
    salvar_em_lancamento,
    salvar_destaques_semana
)
from notifier import enviar_telegram, escape_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

ARQUIVO_ANIMES = "data/todos-animes.json"  # corrigido para usar hífen

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

    try:
        # Atualiza os JSONs usando as funções de salvar do scraper
        salvar_episodios_recentes_home()
        salvar_em_lancamento()
        salvar_destaques_semana()
        logging.info("Arquivos de episódios recentes, em lançamento e destaques salvos.")

        # Atualiza e salva todos os animes
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

        # Carregar dados para mensagem de Telegram
        with open("data/episodios-recentes.json", encoding="utf-8") as f:
            episodios = json.load(f)
        with open("data/destaques-semana.json", encoding="utf-8") as f:
            destaques = json.load(f)
        with open("data/em-lancamento.json", encoding="utf-8") as f:
            lancamentos = json.load(f)

        partes.append(formatar_bloco_episodios(episodios))
        partes.append(formatar_bloco_destaques(destaques))
        partes.append(formatar_bloco_lancamentos(lancamentos))

    except Exception as e:
        logging.error("Erro na atualização completa", exc_info=e)
        partes.append("<b>❌ Erro durante a atualização completa.</b>")

    mensagem = "<b>✅ Atualização concluída com sucesso!</b>\n\n" + "\n\n".join(partes)
    enviar_telegram(mensagem)

if __name__ == "__main__":
    schedule.every(1).minutes.do(job_full)
    logging.info("🤖 Scheduler iniciado.")
    job_full()  # executa imediatamente

    while True:
        schedule.run_pending()
        time.sleep(30)
