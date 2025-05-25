from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
import re
import os
import unicodedata
from datetime import datetime

# 🚀 Inicia o navegador Playwright
playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=True)
context = browser.new_context()
page = context.new_page()

def close_browser():
    page.close()
    context.close()
    browser.close()
    playwright.stop()

# 🔧 Função auxiliar para acessar páginas
def get_html(url):
    try:
        page.goto(url, timeout=60000)
        return page.content()
    except Exception as e:
        print(f"Erro ao acessar {url}: {e}")
        return ""

def normalize(text):
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower()

# 🔍 Extrai link direto do vídeo do iframe
def get_video_url(ep_url):
    html = get_html(ep_url)
    soup = BeautifulSoup(html, 'html.parser')
    iframe = soup.find('iframe')
    if iframe:
        video_url = iframe.get('src')
        if video_url:
            return video_url
    return None

# 📄 Extrai detalhes de um anime específico
def get_anime_details(url):
    html = get_html(url)
    soup = BeautifulSoup(html, 'html.parser')

    nome = soup.select_one('.anime__title')
    nome = nome.text.strip() if nome else ""

    capa = soup.select_one('.anime__poster img')
    capa_url = capa.get('src') if capa else ""

    descricao = soup.select_one('.anime__description')
    descricao = descricao.text.strip() if descricao else ""

    generos = [g.text.strip() for g in soup.select('.anime__genres a')]

    episodios = []
    ep_items = soup.select('.episodes__list .episodes__item')
    for ep in ep_items:
        numero = ep.select_one('.episodes__number').text.strip()
        link = ep.select_one('a').get('href')
        data = ep.select_one('.episodes__date')
        data = data.text.strip() if data else ""

        video_url = get_video_url(link)
        episodios.append({
            "numero": numero,
            "url": link,
            "data": data,
            "video": video_url
        })

    return {
        "nome": nome,
        "descricao": descricao,
        "generos": generos,
        "capa": capa_url,
        "episodios": episodios
    }

# 📦 Coleta todos os animes da listagem
def get_all_animes(paginas=2):
    animes = []
    for page_num in range(1, paginas + 1):
        url = f"https://animefire.plus/animes?pagina={page_num}"
        html = get_html(url)
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select(".animes__grid .anime-card")

        for card in cards:
            link_tag = card.select_one("a")
            link = link_tag.get("href")
            nome = card.select_one(".anime-card__title").text.strip() if card.select_one(".anime-card__title") else ""
            imagem = card.select_one("img").get("src") if card.select_one("img") else ""
            animes.append({
                "nome": nome,
                "link": link,
                "imagem": imagem
            })

    return animes

# 🕒 Coleta episódios recentes da home
def get_episodios_recentes():
    html = get_html("https://animefire.plus/")
    soup = BeautifulSoup(html, "html.parser")

    lista = []
    for item in soup.select(".episodes__item"):
        nome = item.select_one(".episodes__title").text.strip()
        link = item.select_one("a").get("href")
        episodio = item.select_one(".episodes__number").text.strip()
        imagem = item.select_one("img").get("src")
        video = get_video_url(link)
        lista.append({
            "nome": nome,
            "episodio": episodio,
            "link": link,
            "imagem": imagem,
            "video": video
        })
    return lista

# 🚀 Coleta animes em lançamento
def get_em_lancamento():
    html = get_html("https://animefire.plus/")
    soup = BeautifulSoup(html, "html.parser")

    lista = []
    for item in soup.select(".highlight__slider .highlight__item"):
        nome = item.select_one(".highlight__title").text.strip()
        link = item.select_one("a").get("href")
        imagem = item.select_one("img").get("src")
        lista.append({
            "nome": nome,
            "link": link,
            "imagem": imagem
        })
    return lista

# ⭐ Coleta os destaques da semana
def get_destaques():
    html = get_html("https://animefire.plus/")
    soup = BeautifulSoup(html, "html.parser")

    destaques = []
    for item in soup.select(".highlight__destaque .highlight__item"):
        nome = item.select_one(".highlight__title").text.strip()
        link = item.select_one("a").get("href")
        imagem = item.select_one("img").get("src")
        destaques.append({
            "nome": nome,
            "link": link,
            "imagem": imagem
        })

    return destaques

# 💾 Funções de salvamento
def salvar_json(dados, caminho):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def salvar_episodios_recentes_home():
    print("🔄 Salvando episódios recentes...")
    episodios = get_episodios_recentes()
    salvar_json(episodios, "data/episodios-recentes.json")

def salvar_em_lancamento():
    print("🔄 Salvando animes em lançamento...")
    lancamentos = get_em_lancamento()
    salvar_json(lancamentos, "data/em-lancamento.json")

def salvar_destaques_semana():
    print("🔄 Salvando destaques da semana...")
    destaques = get_destaques()
    salvar_json(destaques, "data/destaques-semana.json")

# 🚦 Execução principal
if __name__ == "__main__":
    print("🚀 Iniciando extração de dados...")
    try:
        todos_animes = get_all_animes()
        salvar_json(todos_animes, "data/todos-animes.json")

        salvar_episodios_recentes_home()
        salvar_em_lancamento()
        salvar_destaques_semana()

        print("\n✅ Concluído com sucesso!")
    finally:
        close_browser()
