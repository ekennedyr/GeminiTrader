# Atualizado para Python 3.12 conforme exigido pelos logs
FROM python:3.12-slim

WORKDIR /app

# Instala o GIT (necessário para baixar o pandas_ta atualizado)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Atualiza o pip e ferramentas de build
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8000

CMD ["python", "main.py"]
