FROM python:3.11-slim

WORKDIR /app

# Instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY brain.py .

# Cria diretório de troca de dados
RUN mkdir -p /mnt/mt5_data

CMD ["python", "brain.py"]
