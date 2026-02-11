# Usamos a imagem COMPLETA (não a slim) para garantir compatibilidade máxima
# Com 16GB de RAM, não precisamos economizar espaço aqui.
FROM python:3.11

WORKDIR /app

# 1. Atualiza pip e ferramentas de instalação
RUN pip install --upgrade pip setuptools wheel

# 2. O GRANDE TRUQUE: Instalamos o Numpy antigo (antes da versão 2.0)
# O pandas-ta quebra se usar o Numpy 2.0+
RUN pip install "numpy<2.0.0"

# 3. Instalamos o pandas (ele vai respeitar o numpy antigo)
RUN pip install pandas

# 4. Agora sim instalamos o pandas-ta (sem cache para evitar lixo antigo)
RUN pip install --no-cache-dir pandas_ta

# 5. Restante das dependências
RUN pip install google-generativeai schedule

# 6. Copia o script
# ATENÇÃO: Confirme se no seu GitHub o arquivo se chama brain.py ou main.py
# Se for main.py, mude nas duas linhas abaixo!
COPY brain.py .

# 7. Cria diretório de troca
RUN mkdir -p /mnt/mt5_data

# 8. Executa
CMD ["python", "brain.py"]
