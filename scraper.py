from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
import os
import unicodedata

# 🚀 Inicia o navegador Playwright
playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=True)  # Mude para False para ver o navegador
context = browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)
page = context.new_page()

def close_browser():
    page.close()
    context.close()
    browser.close()
    playwright.stop()

# 🔧 Função auxiliar para acessar páginas com timeout maior, captura de screenshot e HTML
def get_html(url, wait_selector=None):
    try:
        print(f"🌐 Acessando: {url}")
        page.goto(url, timeout=60000, wait_until="networkidle")

        # Se for passado seletor, aguarda até estar disponível, mas com timeout generoso
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=15000)

        # Espera extra para garantir carregamento de conteúdo dinâmico
        page.wait_for_timeout(4000)

        # Salva screenshot e html para debug
        page.screenshot(path="debug.png", full_page=True)
        html = page.content()
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("📸 Screenshot salva como debug.png")
        print("📝 HTML salvo como debug.html")
        return html
    except Exception as e:
        print(f"⚠️ Erro ao acessar {url}: {e}")
        try:
            page.screenshot(path="debug.png", full_page=True)
            print("📸 Screenshot salva como debug.png")
        except:
            pass
        return ""

def normalize(text):
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower()

def get_video_url(ep_url):
    html = get_html(ep_url, "iframe")
    soup = BeautifulSoup(html, 'html.parser')
    iframe = soup.find('iframe')
    if iframe:
        return iframe.get('src')
    return None

def get_anime_details(url):
    html = get_html(url, ".anime__title")
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

def get_all_animes(paginas=2):
    animes = []
    for page_num in range(1, paginas + 1):
        url = f"https://animefire.plus/animes?pagina={page_num}"
        html = get_html(url, ".animes__grid .anime-card")
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select(".animes__grid .anime-card")

        for card in cards:
            link_tag = card.select_one("a")
            if not link_tag:
                continue
            link = link_tag.get("href")
            nome_tag = card.select_one(".anime-card__title")
            nome = nome_tag.text.strip() if nome_tag else ""
            img_tag = card.select_one("img")
            imagem = img_tag.get("src") if img_tag else ""
            animes.append({
                "nome": nome,
                "link": link,
                "imagem": imagem
            })
    return animes

def get_episodios_recentes():
    html = get_html("https://animefire.plus/", ".episodes__item")
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

def get_em_lancamento():
    html = get_html("https://animefire.plus/", ".highlight__slider .highlight__item")
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

def get_destaques():
    html = get_html("https://animefire.plus/", ".highlight__destaque .highlight__item")
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

# 💾 Salvamento
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

# 🚦 Execução
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
