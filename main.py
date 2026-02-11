import os
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

# Configuração
app = FastAPI()
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

# Modelo de dados recebido do MT5
class Candle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    tick_volume: int

class MarketData(BaseModel):
    symbol: str
    candles_h1: List[Candle]
    candles_h4: List[Candle]

def calculate_indicators(df):
    # Indicadores "Duros" para evitar alucinação [cite: 82]
    df['EMA_200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    return df

def get_gemini_decision(symbol, df_h1, df_h4):
    last_h1 = df_h1.iloc[-1]
    last_h4 = df_h4.iloc[-1]
    
    # Prompt Engenharia Avançada (Chain-of-Thought) [cite: 102, 105]
    prompt = f"""
    Atue como um Trader Institucional de Forex especialista em Smart Money Concepts (SMC).
    Analise o par {symbol}.
    
    DADOS TÉCNICOS (H4 - Contexto):
    - Preço Atual: {last_h4['close']}
    - EMA 200: {last_h4['EMA_200']:.5f} (Tendência: {"ALTA" if last_h4['close'] > last_h4['EMA_200'] else "BAIXA"})
    
    DADOS TÉCNICOS (H1 - Gatilho):
    - RSI (14): {last_h1['RSI']:.2f}
    - ATR (Volatilidade): {last_h1['ATR']:.5f}
    
    Sua tarefa:
    1. Identifique a estrutura de mercado no H4 (Higher Highs/Lows?).
    2. Procure por Fair Value Gaps (FVG) recentes ou quebras de estrutura (MSS) no H1.
    3. Responda ESTRITAMENTE em JSON.
    
    Regras de Segurança (Hard Filters):
    - NÃO compre se preço < EMA 200 no H4.
    - NÃO venda se preço > EMA 200 no H4.
    
    Formato JSON esperado:
    {{
        "decision": "BUY" ou "SELL" ou "HOLD",
        "sl_pips": 30,
        "tp_pips": 60,
        "confidence": 0 a 100,
        "reasoning": "Explicação breve focada em SMC"
    }}
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash') # Usando Flash para economia e velocidade 
    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
    return response.text

@app.post("/analyze")
async def analyze_market(data: MarketData):
    try:
        # Converter dados para DataFrame
        df_h1 = pd.DataFrame([c.dict() for c in data.candles_h1])
        df_h4 = pd.DataFrame([c.dict() for c in data.candles_h4])
        
        # Calcular indicadores
        df_h1 = calculate_indicators(df_h1)
        df_h4 = calculate_indicators(df_h4)
        
        # Obter decisão da IA
        decision_json = get_gemini_decision(data.symbol, df_h1, df_h4)
        
        return {"status": "success", "analysis": decision_json}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)