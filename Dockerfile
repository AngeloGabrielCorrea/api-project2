# Imagem base oficial do Python
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia arquivos do projeto
COPY . .

# Instala dependências do sistema necessárias para o Playwright
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libxss1 \
    libxtst6 \
    libgbm1 \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala dependências do Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Instala os navegadores do Playwright
RUN playwright install --with-deps

# Define variáveis de ambiente para produção
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Porta usada pelo Render (Render usa a variável $PORT automaticamente)
ENV PORT=10000
EXPOSE 10000

# Comando para rodar o servidor com Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
