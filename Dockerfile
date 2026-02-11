# Alterado de 3.9-slim para 3.11-slim para compatibilidade moderna
FROM python:3.11-slim

WORKDIR /app

# Instala ferramentas básicas de build que às vezes faltam no slim
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8000

CMD ["python", "main.py"]
