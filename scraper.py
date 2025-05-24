import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
import pandas as pd
import unicodedata
from datetime import datetime

BASE_URL = "https://animefire.plus/animes-atualizados"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# Cria scraper que contorna Cloudflare/WAF
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
)

def gerar_slug(nome):
    nome = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode('utf-8')
    nome = re.sub(r'[^\w\s-]', '', nome.lower())
    nome = re.sub(r'[-\s]+', '-', nome).strip('-_')
    return nome

def get_video_url(ep_url):
    try:
        res = scraper.get(ep_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        video_tag = soup.find('video', id='my-video')
        if not video_tag:
            return {}

        json_url = video_tag.get('data-video-src')
        if not json_url:
            return {}

        json_data = scraper.get(json_url, headers=HEADERS, timeout=10).json()
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
        response = scraper.get(anime_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        def find_info(label):
            tag = soup.find(string=re.compile(label))
            return tag.find_next().text.strip() if tag else ""

        nome = soup.find("h1").text.strip() if soup.find("h1") else ""
        sinopse_tag = soup.find("div", class_="divSinopse")
        sinopse = sinopse_tag.text.strip() if sinopse_tag else ""

        genero_tags = soup.select('a.spanAnimeInfo.spanGeneros.spanGenerosLink')
        generos = [tag.text.strip() for tag in genero_tags if not tag['href'].startswith('/top-animes?')]

        trailer_tag = soup.find('div', id='iframe-trailer')
        trailer_iframe = trailer_tag.find('iframe') if trailer_tag else None
        trailer_link = trailer_iframe.get('data-src') or trailer_iframe.get('src') if trailer_iframe else ""

        episodio_tags = soup.select("div.div_video_list a.lEp.epT")
        episodios_links = [a['href'] for a in episodio_tags if a.has_attr('href')]

        print(f"⏳ Extraindo vídeos de {nome}...")
        episodios_video_urls = []
        for link in episodios_links:
            match = re.search(r'/(\d+)$', link)
            num_ep = int(match.group(1)) if match else None
            video_por_qualidade = get_video_url(link)
            episodios_video_urls.append({"episodio": num_ep, "videos": video_por_qualidade})

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
            "trailer": trailer_link,
            "link": anime_url,
            "episodios_links": episodios_video_urls
        }
    except Exception as e:
        print(f"❌ Erro ao acessar {anime_url}: {e}")
        return {}

def extract_rating_and_class(texto):
    match = re.search(r'(\d{1,2}\.\d{2})\s+(A\d{2})', texto)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r'N/A\s+(A\d{2})', texto)
    if match:
        return "N/A", match.group(1)
    return "", ""

def get_all_animes():
    animes = []
    links_processados = set()

    for page in range(1, 2):
        print(f"📄 Lendo página {page}...")
        url = f"{BASE_URL}/{page}" if page > 1 else BASE_URL
        try:
            res = scraper.get(url, headers=HEADERS, timeout=50)
            soup = BeautifulSoup(res.content, "html.parser")

            for carrossel in soup.select('.owl-carousel'):
                carrossel.decompose()
            for bloco in soup.select('.col-12.col-lg-2-5'):
                bloco.decompose()

            cards = soup.select("div.divCardUltimosEps")
            for card in cards:
                a_tag = card.find('a')
                if not a_tag:
                    continue
                link = a_tag.get('href')
                if not link or link in links_processados:
                    continue

                links_processados.add(link)
                nome_completo = a_tag.get('title') or a_tag.text.strip()

                img_tag = card.find('img')
                if img_tag:
                    thumbnail = img_tag.get('src') or img_tag.get('data-src') or ""
                    thumbnail_large = thumbnail.replace('.webp', '-large.webp')
                else:
                    thumbnail = thumbnail_large = ""

                rating, classificacao = extract_rating_and_class(nome_completo)
                detalhes = get_anime_details(link)

                animes.append({
                    "nome": detalhes.get("nome", nome_completo),
                    "link": link,
                    "thumbnail": thumbnail,
                    "thumbnail-large": thumbnail_large,
                    "rating": rating,
                    "classificacao_indicativa": classificacao,
                    "sinopse": detalhes.get("sinopse"),
                    "generos": detalhes.get("generos"),
                    "temporada": detalhes.get("temporada"),
                    "estudio": detalhes.get("estudio"),
                    "audio": detalhes.get("audio"),
                    "episodios": detalhes.get("episodios"),
                    "status": detalhes.get("status"),
                    "dia_lancamento": detalhes.get("dia_lancamento"),
                    "ano": detalhes.get("ano"),
                    "trailer": detalhes.get("trailer"),
                    "episodios_links": detalhes.get("episodios_links"),
                    "slug": gerar_slug(detalhes.get("nome", nome_completo))
                })
                print(f"🎮 Adicionado: {animes[-1]['nome']}")
                time.sleep(0.5)
        except Exception as e:
            print(f"❌ Erro na página {page}: {e}")
            continue
    return animes

def tempo_decorrido(data_str):
    try:
        data_postagem = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - data_postagem
        dias, segundos = delta.days, delta.seconds
        if dias > 0:
            return f"há {dias} dia{'s' if dias > 1 else ''}"
        if segundos >= 3600:
            return f"há {segundos // 3600} hora{'s' if segundos // 3600 > 1 else ''}"
        if segundos >= 60:
            return f"há {segundos // 60} minuto{'s' if segundos // 60 > 1 else ''}"
        return "há poucos segundos"
    except:
        return "erro ao calcular tempo"

def get_episodios_recentes_home(limite=999999999, max_paginas=1):
    episodios = []
    base_url = "https://animefire.plus/home/{}"
    pagina = 1
    try:
        while len(episodios) < limite and pagina <= max_paginas:
            url = base_url.format(pagina)
            res = scraper.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                print(f"Erro ao acessar página {pagina}: status {res.status_code}")
                break
            soup = BeautifulSoup(res.content, "html.parser")
            cards = soup.select("div.divCardUltimosEpsHome")
            if not cards:
                print(f"Nenhum episódio encontrado na página {pagina}")
                break
            for card in cards:
                if len(episodios) >= limite:
                    break
                a_tag = card.find("a")
                if not a_tag:
                    continue
                link = a_tag.get("href", "")
                img_tag = a_tag.find("img")
                thumb = img_tag.get("src") or img_tag.get("data-src") if img_tag else ""
                titulo = a_tag.get("title") or (a_tag.find("h3", class_="animeTitle").text if a_tag.find("h3", class_="animeTitle") else "")
                match = re.search(r"(.+?)\s*-\s*Episódio\s*(\d+)", titulo)
                if not match:
                    continue
                nome, numero = match.group(1).strip(), int(match.group(2))
                slug = gerar_slug(nome)
                data_span = card.select_one("span.ep-dateModified")
                postado_ha = tempo_decorrido(data_span["data-date-modified"]) if data_span else "Data não encontrada"
                episodios.append({
                    "slug": slug,
                    "nome": nome,
                    "thumbnail": thumb,
                    "episodio": numero,
                    "postado_ha": postado_ha,
                    "link": link
                })
            pagina += 1
        print(f"✅ {len(episodios)} episódios recentes extraídos.")
        return episodios
    except Exception as e:
        print(f"❌ Erro ao buscar episódios recentes: {e}")
        return []

def limpar_nome_anime(nome):
    return re.sub(r'\s*\d+(\.\d+)?\s*A\d{1,2}$', '', nome).strip()

def get_animes_em_lancamento(limite=9999, max_paginas=10):
    animes = []
    base_url = "https://animefire.plus/em-lancamento/{}"
    pagina = 1
    try:
        while len(animes) < limite and pagina <= max_paginas:
            url = base_url.format(pagina)
            res = scraper.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                print(f"Erro em lançamento página {pagina}: status {res.status_code}")
                break
            soup = BeautifulSoup(res.content, "html.parser")
            cards = soup.select("div.divCardUltimosEps")
            if not cards:
                print(f"Nenhum anime em lançamento na página {pagina}")
                break
            for card in cards:
                a_tag = card.find("a")
                if not a_tag:
                    continue
                link = a_tag.get("href", "")
                titulo = a_tag.get("title") or a_tag.text.strip()
                titulo_limpo = limpar_nome_anime(titulo)
                img_tag = a_tag.find("img")
                thumb = img_tag.get("src") or img_tag.get("data-src") if img_tag else ""
                slug = gerar_slug(titulo_limpo)
                animes.append({
                    "nome": titulo_limpo,
                    "link": link,
                    "thumbnail": thumb,
                    "slug": slug
                })
            pagina += 1
        print(f"✅ {len(animes)} animes em lançamento extraídos.")
        return animes
    except Exception as e:
        print(f"❌ Erro ao buscar animes em lançamento: {e}")
        return []

def get_destaques_semana():
    try:
        res = scraper.get("https://animefire.plus/", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        carousel = soup.find("div", class_="owl-carousel-l_dia")
        if not carousel:
            print("❌ Carrossel de destaques não encontrado.")
            return []
        destaques = []
        for artigo in carousel.select("div.divArticleLancamentos"):
            a_tag = artigo.find("a", class_="item")
            if not a_tag:
                continue
            link = a_tag.get("href", "")
            img_tag = a_tag.find("img")
            thumb = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
            titulo_tag = a_tag.find("h3", class_="animeTitle")
            nome = titulo_tag.text.strip() if titulo_tag else ""
            slug = gerar_slug(nome)
            destaques.append({
                "nome": nome,
                "link": link,
                "thumbnail": thumb,
                "slug": slug
            })
        print(f"✅ {len(destaques)} destaques da semana extraídos.")
        return destaques
    except Exception as e:
        print(f"❌ Erro ao buscar destaques da semana: {e}")
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
