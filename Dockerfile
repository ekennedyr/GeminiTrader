# Usamos Python 3.10, que é mais estável para libs financeiras antigas
FROM python:3.10

WORKDIR /app

# 1. Atualiza ferramentas de build
RUN pip install --upgrade pip setuptools wheel

# 2. A "MÁQUINA DO TEMPO":
# Instalamos versões antigas específicas que sabemos que funcionam com o pandas-ta.
# O pandas-ta quebra com o Pandas 2.0+, então forçamos uma versão 1.5.x
RUN pip install "numpy<1.26.0"
RUN pip install "pandas<2.0.0"

# 3. Agora instalamos o pandas-ta (Usando hífen, que é o padrão do PyPI)
RUN pip install pandas-ta

# 4. Outras dependências
RUN pip install google-generativeai schedule

# 5. Copia o script 
# (IMPORTANTE: Verifique se no seu GitHub o arquivo se chama 'brain.py' ou 'main.py')
# Se for main.py, mude nas duas linhas abaixo!
COPY brain.py .

# 6. Cria diretório de troca
RUN mkdir -p /mnt/mt5_data

# 7. Executa
CMD ["python", "brain.py"]
