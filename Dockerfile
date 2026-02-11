FROM python:3.11-slim

WORKDIR /app

# 1. Instala dependências do sistema operacional (Compiladores básicos)
# Isso evita falhas se o Pandas precisar compilar algo
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Atualiza o pip
RUN pip install --upgrade pip

# 3. Instala bibliotecas UMA POR UMA
# Isso ajuda a não estourar a memória da VPS durante a instalação
RUN pip install --no-cache-dir numpy
RUN pip install --no-cache-dir pandas
RUN pip install --no-cache-dir pandas-ta
RUN pip install --no-cache-dir google-generativeai
RUN pip install --no-cache-dir schedule

# 4. Copia o script (Garanta que no GitHub o nome seja brain.py)
COPY brain.py .

# 5. Cria diretório
RUN mkdir -p /mnt/mt5_data

# 6. Executa
CMD ["python", "brain.py"]
