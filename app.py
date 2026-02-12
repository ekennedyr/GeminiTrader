import os
import json
import logging
from flask import Flask, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import pandas as pd
import pandas_ta as ta

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. ESTRUTURA GLOBAL (Conforme Regra 1)
app = Flask(__name__)

# 2. CONFIGURAÇÃO GEMINI E VARIÁVEIS
API_KEY = os.getenv('GEMINI_API_KEY')
# Fallback para 1.5 Flash se não especificado, mas pronto para 2.0
MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash') 

if not API_KEY:
    logger.error("ERRO: GEMINI_API_KEY não encontrada.")
else:
    genai.configure(api_key=API_KEY)

# Função auxiliar para calcular indicadores técnicos (Hard Data)
def calcular_indicadores(dados_json):
    try:
        # Converter JSON para DataFrame
        df = pd.DataFrame(dados_json)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['open'] = df['open'].astype(float)
        
        # Calcular Indicadores usando pandas_ta
        # EMAs
        df['ema_20'] = ta.ema(df['close'], length=20)
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        # RSI (14 períodos)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # ATR (14 períodos) para volatilidade
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Pegar os dados da última vela fechada (penúltima da lista, pois a última é a atual em aberto)
        last = df.iloc[-2]
        current = df.iloc[-1]
        
        return {
            "price_close": last['close'],
            "ema_20": last['ema_20'],
            "ema_50": last['ema_50'],
            "ema_200": last['ema_200'],
            "rsi": last['rsi'],
            "atr": last['atr'],
            "trend_ema": "ALTA" if last['close'] > last['ema_200'] else "BAIXA",
            "current_price": current['close'] # Preço atual para Sanity Check
        }
    except Exception as e:
        logger.error(f"Erro ao calcular indicadores: {e}")
        return None

@app.route('/analisar', methods=['POST'])
def analisar():
    try:
        data = request.get_json()
        
        # Recebe dados de H1 e H4 do MT5
        candles_h1 = data.get('candles_h1', [])
        candles_h4 = data.get('candles_h4', [])
        
        if not candles_h1 or not candles_h4:
            return jsonify({"decision": "HOLD", "reason": "Dados insuficientes"}), 400

        # Processar Indicadores (Hard Data para evitar alucinação)
        tech_h1 = calcular_indicadores(candles_h1)
        tech_h4 = calcular_indicadores(candles_h4)
        
        if not tech_h1 or not tech_h4:
            return jsonify({"decision": "HOLD", "reason": "Erro no calculo de indicadores"}), 500

        # Construção do System Prompt (SMC + Contexto)
        system_instruction = """
        Você é um Gestor de Risco e Trader Institucional Sênior (SMC).
        Sua prioridade é preservação de capital.
        Analise os dados fornecidos na seguinte ordem:
        1. Identificar Tendência Macro no H4 (Price Action + EMA 200).
        2. Identificar Zonas de Liquidez (FVG/Order Blocks) nos dados OHLC recentes.
        3. Validar Gatilho no H1 (RSI Divergencia, Quebra de Estrutura).
        4. Checar Volatilidade (ATR).
        
        REGRAS RÍGIDAS (Hard Guardrails):
        - Se o preço H4 está ABAIXO da EMA 200, PROIBIDO COMPRAR (BUY), exceto reversão clara.
        - Se o preço H4 está ACIMA da EMA 200, PROIBIDO VENDER (SELL), exceto reversão clara.
        - Retorne APENAS um JSON cru, sem formatação Markdown.
        Format: {"decision": "BUY" | "SELL" | "HOLD", "sl": price, "tp": price, "reason": "short explanation"}
        """

        prompt_user = f"""
        CONTEXTO DE MERCADO:
        H4 (Macro):
        - Preço Fechamento: {tech_h4['price_close']}
        - EMA 200: {tech_h4['ema_200']}
        - Tendência EMA: {tech_h4['trend_ema']}
        - RSI: {tech_h4['rsi']}
        
        H1 (Gatilho):
        - Preço Atual: {tech_h1['current_price']}
        - ATR (Volatilidade): {tech_h1['atr']}
        - RSI: {tech_h1['rsi']}
        
        DADOS OHLC RECENTES H1 (Para analise de FVG/Candles):
        {json.dumps(candles_h1[-5:])}
        
        Com base na estratégia SMC e nos indicadores acima, qual a decisão?
        """

        # Chamada ao Gemini
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_instruction,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response = model.generate_content(prompt_user)
        
        # Limpeza e retorno
        resposta_texto = response.text.strip()
        # Remove markdown se o modelo insistir em colocar (ex: ```json ... ```)
        if resposta_texto.startswith("```"):
            resposta_texto = resposta_texto.replace("```json", "").replace("```", "")
            
        return getattr(response, 'text', '{"decision": "HOLD", "reason": "Erro API"}')

    except Exception as e:
        logger.error(f"Erro interno: {e}")
        return jsonify({"decision": "HOLD", "reason": str(e)}), 500

# 3. INICIALIZAÇÃO DO SERVIDOR (Conforme Regra 3)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
