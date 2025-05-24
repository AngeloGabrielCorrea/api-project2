import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
import unicodedata
from datetime import datetime

BASE_URL = "https://animefire.plus/animes-atualizados"

# Cabeçalhos simulando um navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/112.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://animefire.plus/'
}

# Cria um cloudscraper que mantém sessão e contorna proteções
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
    delay=10
)

def gerar_slug(nome):
    nome = unicodedata.normalize('NFKD', nome).encode('ascii','ignore').decode('utf-8')
    nome = re.sub(r'[^\w\s-]', '', nome.lower())
    return re.sub(r'[-\s]+', '-', nome).strip('-_')

def get(url, **kwargs):
    """Wrapper para sempre usar nossos HEADERS e cloudscraper."""
    return scraper.get(url, headers=HEADERS, **kwargs)

def get_video_url(ep_url):
    try:
        res = get(ep_url, timeout=10)
        if res.status_code != 200:
            return {}
        soup = BeautifulSoup(res.content, "html.parser")
        video_tag = soup.find('video', id='my-video')
        if not video_tag:
            return {}
        json_url = video_tag.get('data-video-src')
        if not json_url:
            return {}

        json_data = get(json_url, timeout=10).json()
        video_options = json_data.get("data", [])
        qualidade_links = {}
        for option in video_options:
            label = option.get("label", "").lower()
            src = option.get("src")
            if "360" in label:
                qualidade_links["360p"] = src
            elif "720" in label:
                qualidade_links["720p"] = src
            elif "1080" in label:
                qualidade_links["1080p"] = src
        return qualidade_links
    except Exception as e:
        print(f"Erro ao extrair vídeo de {ep_url}: {e}")
        return {}

def get_anime_details(anime_url):
    try:
        res = get(anime_url, timeout=15)
        if res.status_code != 200:
            print(f"Erro detalhes {anime_url}: status {res.status_code}")
            return {}
        soup = BeautifulSoup(res.content, "html.parser")
        def find_info(label):
            tag = soup.find(string=re.compile(label))
            return tag.find_next().text.strip() if tag else ""
        nome = soup.find("h1").text.strip() if soup.find("h1") else ""
        sinopse_tag = soup.find("div", class_="divSinopse")
        sinopse = sinopse_tag.text.strip() if sinopse_tag else ""
        genero_tags = soup.select('a.spanAnimeInfo.spanGeneros.spanGenerosLink')
        generos = [g.text.strip() for g in genero_tags if not g['href'].startswith('/top-animes?')]
        episodio_tags = soup.select("div.div_video_list a.lEp.epT")
        episodios_links = [a['href'] for a in episodio_tags if a.has_attr('href')]
        episodios = []
        for link in episodios_links:
            num = None
            m = re.search(r'/(\d+)$', link)
            if m: num = int(m.group(1))
            episodios.append({"episodio": num, "videos": get_video_url(link)})
        return {
            "nome": nome,
            "sinopse": sinopse,
            "generos": generos,
            "temporada": find_info("Temporada:"),
            "estudio": find_info("Estúdios:"),
            "audio": find_info("Áudio:"),
            "episodios": find_info("Episódios:"),
            "status": find_info("Status do Anime:"),
            "dia_lancamento": find_info("Dia de Lançamento:"),
            "ano": find_info("Ano:"),
            "link": anime_url,
            "episodios_links": episodios
        }
    except Exception as e:
        print(f"❌ Erro ao acessar {anime_url}: {e}")
        return {}

def extract_rating_and_class(texto):
    m = re.search(r'(\d{1,2}\.\d{2})\s+(A\d{2})', texto)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'N/A\s+(A\d{2})', texto)
    if m:
        return "N/A", m.group(1)
    return "", ""

def get_all_animes():
    animes = []
    seen = set()
    print("📄 Lendo página 1...")
    res = get(BASE_URL, timeout=30)
    if res.status_code != 200:
        print(f"❌ Falha ao acessar {BASE_URL}: status {res.status_code}")
        return animes
    soup = BeautifulSoup(res.content, "html.parser")
    for sel in ('.owl-carousel', '.col-12.col-lg-2-5'):
        for el in soup.select(sel):
            el.decompose()
    cards = soup.select("div.divCardUltimosEps")
    for card in cards:
        a = card.find('a')
        if not a: continue
        link = a['href']
        if link in seen: continue
        seen.add(link)
        title = a.get('title') or a.text.strip()
        img = card.find('img')
        thumb = img.get('src') or img.get('data-src') if img else ""
        rating, cls = extract_rating_and_class(title)
        detalhes = get_anime_details(link)
        animes.append({
            "nome": detalhes.get("nome", title),
            "link": link,
            "thumbnail": thumb,
            "rating": rating,
            "classificacao_indicativa": cls,
            **detalhes,
            "slug": gerar_slug(detalhes.get("nome", title))
        })
        print(f"🎮 Adicionado: {title}")
        time.sleep(0.5)
    print(f"✅ {len(animes)} animes extraídos.")
    return animes

def tempo_decorrido(data_str):
    try:
        dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - dt
        if delta.days > 0:
            return f"há {delta.days} dia{'s' if delta.days>1 else ''}"
        hrs = delta.seconds // 3600
        if hrs > 0:
            return f"há {hrs} hora{'s' if hrs>1 else ''}"
        mins = delta.seconds // 60
        if mins > 0:
            return f"há {mins} minuto{'s' if mins>1 else ''}"
        return "há poucos segundos"
    except:
        return "erro"

def get_episodios_recentes_home(limite=999999, max_paginas=1):
    episodios = []
    page = 1
    while page <= max_paginas and len(episodios) < limite:
        url = f"https://animefire.plus/home/{page}"
        res = get(url, timeout=15)
        if res.status_code != 200:
            print(f"Erro ao acessar home/{page}: status {res.status_code}")
            break
        soup = BeautifulSoup(res.content, "html.parser")
        cards = soup.select("div.divCardUltimosEpsHome")
        if not cards:
            print(f"Nenhum episódio na página {page}")
            break
        for card in cards:
            if len(episodios) >= limite:
                break
            a = card.find("a")
            if not a: continue
            link = a.get("href","")
            img = a.find("img")
            thumb = img.get("src") or img.get("data-src") if img else ""
            title = a.get("title") or (a.find("h3",class_="animeTitle").text if a.find("h3",class_="animeTitle") else "")
            m = re.search(r"(.+?)\s*-\s*Episódio\s*(\d+)", title)
            if not m: continue
            nome, num = m.group(1).strip(), int(m.group(2))
            span = card.select_one("span.ep-dateModified")
            post = tempo_decorrido(span["data-date-modified"]) if span else "?"
            episodios.append({
                "slug": gerar_slug(nome),
                "nome": nome,
                "thumbnail": thumb,
                "episodio": num,
                "postado_ha": post,
                "link": link
            })
        page += 1
    print(f"✅ {len(episodios)} episódios recentes extraídos.")
    return episodios

def get_animes_em_lancamento(limite=9999, max_paginas=10):
    animes = []
    page = 1
    while page <= max_paginas and len(animes) < limite:
        url = f"https://animefire.plus/em-lancamento/{page}"
        res = get(url, timeout=15)
        if res.status_code != 200:
            print(f"Erro em-lancamento/{page}: status {res.status_code}")
            break
        soup = BeautifulSoup(res.content, "html.parser")
        cards = soup.select("div.divCardUltimosEps")
        if not cards:
            print(f"Nenhum lançamento na página {page}")
            break
        for card in cards:
            a = card.find("a")
            if not a: continue
            link = a.get("href","")
            title = a.get("title") or a.text.strip()
            nome = re.sub(r'\s*\d+(\.\d+)?\s*A\d{1,2}$','', title).strip()
            img = card.find("img")
            thumb = img.get("src") or img.get("data-src") if img else ""
            animes.append({
                "nome": nome,
                "link": link,
                "thumbnail": thumb,
                "slug": gerar_slug(nome)
            })
        page += 1
    print(f"✅ {len(animes)} animes em lançamento extraídos.")
    return animes

def get_destaques_semana():
    try:
        res = get("https://animefire.plus/", timeout=15)
        if res.status_code != 200:
            print(f"Erro destaques: status {res.status_code}")
            return []
        soup = BeautifulSoup(res.content, "html.parser")
        carousel = soup.find("div", class_="owl-carousel-l_dia")
        if not carousel:
            print("❌ Carrossel não encontrado.")
            return []
        destaques = []
        for art in carousel.select("div.divArticleLancamentos"):
            a = art.find("a", class_="item")
            if not a: continue
            link = a.get("href","")
            img = a.find("img")
            thumb = img.get("data-src") or img.get("src") if img else ""
            title = a.find("h3", class_="animeTitle")
            nome = title.text.strip() if title else ""
            destaques.append({
                "nome": nome,
                "link": link,
                "thumbnail": thumb,
                "slug": gerar_slug(nome)
            })
        print(f"✅ {len(destaques)} destaques da semana extraídos.")
        return destaques
    except Exception as e:
        print(f"❌ Erro destaques: {e}")
        return []

def salvar_destaques_semana():
    destaques = get_destaques_semana()
    with open("data/destaques-semana.json", "w", encoding="utf-8") as f:
        json.dump(destaques, f, indent=2, ensure_ascii=False)


def salvar_em_lancamento():
    em_lancamento = get_animes_em_lancamento()
    with open("data/em-lancamento.json", "w", encoding="utf-8") as f:
        json.dump(em_lancamento, f, indent=2, ensure_ascii=False)

def salvar_json(obj):
    with open("data/anime_detalhes.json", 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)

def salvar_episodios_recentes_home():
    recentes = get_episodios_recentes_home()
    with open("data/episodios-recentes.json", "w", encoding="utf-8") as f:
        json.dump(recentes, f, indent=2, ensure_ascii=False)

# Parte final para executar o script inteiro
if __name__ == "__main__":
    print("🚀 Iniciando extração de dados...")
    todos_animes = get_all_animes()
    salvar_json(todos_animes)
    salvar_episodios_recentes_home()
    salvar_em_lancamento()
    salvar_destaques_semana()
    print("\n✅ Concluído com sucesso!")
