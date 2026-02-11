import os
import json
import time
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from datetime import datetime

# CONFIGURAÇÕES
API_KEY = os.getenv("GEMINI_API_KEY")
SHARED_DIR = "/mnt/mt5_data/NeuroData" # Caminho dentro do container Python
DATA_FILE = os.path.join(SHARED_DIR, "market_data.json")
CMD_FILE = os.path.join(SHARED_DIR, "commands.json")

# Configuração Gemini
genai.configure(api_key=API_KEY)
# Usando Flash para triagem rápida conforme PDF 
model = genai.GenerativeModel('gemini-1.5-flash') 

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data['candles'])
        # Conversão de tipos
        cols = ['o', 'h', 'l', 'c']
        df[cols] = df[cols].astype(float)
        return df, data['bid'], data['ask'], data['symbol']
    except Exception as e:
        print(f"Erro ao ler dados: {e}")
        return None, 0, 0, ""

def calculate_indicators(df):
    # Indicadores conforme PDF 
    df['EMA_50'] = ta.ema(df['c'], length=50)
    df['EMA_200'] = ta.ema(df['c'], length=200)
    df['RSI'] = ta.rsi(df['c'], length=14)
    df['ATR'] = ta.atr(df['h'], df['l'], df['c'], length=14)
    return df.tail(50) # Enviar apenas as ultimas 50 para a IA para economizar tokens

def generate_prompt(df, symbol):
    # Serializa dados para a IA
    csv_data = df.to_csv(index=False)
    
    # Prompt de Engenharia (Chain-of-Thought) 
    prompt = f"""
    Atue como um Trader Institucional de Forex focado em SMC (Smart Money Concepts).
    Par: {symbol}
    Dados Recentes (H1):
    {csv_data}
    
    Sua tarefa:
    1. Analise a Tendência (EMA 50 vs 200).
    2. Identifique Fair Value Gaps (FVG) recentes e quebras de estrutura.
    3. Verifique o RSI para divergências.
    4. Decida se há uma oportunidade de SWING TRADE para as próximas 24h.
    
    Regras de Risco:
    - Só compre se Preço > EMA 200 (Preferencialmente).
    - Stop Loss deve ser técnico (abaixo/acima do último swing).
    
    Retorne APENAS um JSON estrito neste formato, sem markdown:
    {{
        "decision": "BUY" | "SELL" | "HOLD",
        "confidence": 0-100,
        "stop_loss": preço_float,
        "take_profit": preço_float,
        "reason": "resumo curto"
    }}
    """
    return prompt

def execute_logic():
    print(f"[{datetime.now()}] Iniciando ciclo de análise...")
    
    if not os.path.exists(DATA_FILE):
        print("Aguardando dados do MT5...")
        return

    df, bid, ask, symbol = load_data()
    if df is None: return

    df = calculate_indicators(df)
    
    # Lógica de Pré-Filtro (Python Hard-Coded) 
    # Economiza chamadas de API se o mercado estiver lateral
    atr = df['ATR'].iloc[-1]
    if atr < 0.0005: # Exemplo: volatilidade muito baixa
        print("Volatilidade muito baixa, pulando IA.")
        return

    # Consulta IA
    response = model.generate_content(generate_prompt(df, symbol))
    
    try:
        # Limpeza básica do JSON retornado pela IA
        clean_json = response.text.replace("```json", "").replace("```", "")
        decision_data = json.loads(clean_json)
        
        print(f"IA Decisão: {decision_data['decision']} ({decision_data['confidence']}%)")
        
        # Filtro de Confiança e Execução 
        if decision_data['decision'] in ["BUY", "SELL"] and decision_data['confidence'] > 85:
            
            # Cálculo de Lote (Gestão de Risco) 
            # Simplificado: 0.01 fixo para testes, implemente lógica de % saldo depois
            volume = 0.01 
            
            command = {
                "action": decision_data['decision'],
                "sl": decision_data['stop_loss'],
                "tp": decision_data['take_profit'],
                "volume": volume,
                "timestamp": time.time()
            }
            
            # Escreve comando para o MT5
            with open(CMD_FILE, 'w') as f:
                json.dump(command, f)
            print("Comando enviado para MT5!")
            
    except Exception as e:
        print(f"Erro ao processar resposta da IA: {e}")

if __name__ == '__main__':
    # O Coolify/Docker geralmente passa a porta via variável de ambiente PORT
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host='0.0.0.0', port=port)

