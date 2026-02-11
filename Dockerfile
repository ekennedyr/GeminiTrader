FROM python:3.11-slim

WORKDIR /app

# Instala as bibliotecas DIRETAMENTE aqui (mais seguro)
RUN pip install --no-cache-dir pandas pandas-ta google-generativeai schedule

# Copia o seu script (Se o nome no GitHub for brain.py)
COPY brain.py .

# Cria diretório de troca de dados
RUN mkdir -p /mnt/mt5_data

# Executa o script
CMD ["python", "brain.py"]
