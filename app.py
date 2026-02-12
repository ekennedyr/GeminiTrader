import os
import json
import logging
from flask import Flask, request, jsonify
import google.generativeai as genai
import pandas as pd
import pandas_ta as ta
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# --- 1. CONFIGURAÇÃO GERAL E VARIÁVEIS ---
API_KEY = os.getenv('GEMINI_API_KEY')
MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
PORT = int(os.environ.get("PORT", 5000))

# Configuração de Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração do Gemini
if not API_KEY:
    logger.error("GEMINI_API_KEY não encontrada!")
else:
    genai.configure(api_key=API_KEY)

# Instância Global do Flask (Requisito Obrigatório)
app = Flask(__name__)

# --- 2. FUNÇÕES AUXILIARES E INDICADORES ---
def calculate_indicators(df):
    """Calcula indicadores técnicos usando pandas-ta."""
    # Garante que os dados estão na ordem correta (mais antigo primeiro)
    df = df.sort_values(by='time', ascending=True)
    
    # EMAs
    df['ema_20'] = ta.ema(df['close'], length=20)
    df['ema_50'] = ta.ema(df['close'], length=50)
    df['ema_200'] = ta.ema(df['close'], length=200)
    
    # RSI (14)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    # ATR (14)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    return df

def safety_guardrails(decision, df_h4, df_h1):
    """
    Camada de Segurança (Hard-Coded) para evitar alucinações.
    Retorna a decisão filtrada ou 'HOLD' se violar regras.
    """
    last_h4 = df_h4.iloc[-1]
    last_h1 = df_h1.iloc[-1]
    
    signal = decision.get('action', 'HOLD').upper()
    
    # 1. Filtro de Tendência Macro (EMA 200 no H4)
    # Se preço < EMA200 (H4), PROIBIDO COMPRAR (apenas setups de reversão extrema permitidos pela IA, mas aqui somos rígidos)
    if signal == 'BUY' and last_h4['close'] < last_h4['ema_200']:
        logger.warning("Guardrail: Compra bloqueada. Preço abaixo da EMA200 no H4.")
        return "HOLD"

    if signal == 'SELL' and last_h4['close'] > last_h4['ema_200']:
        logger.warning("Guardrail: Venda bloqueada. Preço acima da EMA200 no H4.")
        return "HOLD"
        
    # 2. Filtro RSI Extremo (H1)
    if signal == 'BUY' and last_h1['rsi'] > 70:
        logger.warning("Guardrail: Compra bloqueada. RSI H1 em sobrecompra (>70).")
        return "HOLD"
        
    if signal == 'SELL' and last_h1['rsi'] < 30:
        logger.warning("Guardrail: Venda bloqueada. RSI H1 em sobrevenda (<30).")
        return "HOLD"

    return signal

def generate_prompt(df_h4, df_h1):
    """Gera o System Prompt com Chain-of-Thought."""
    
    # Dados recentes para contexto
    last_h4 = df_h4.tail(3).to_dict(orient='records')
    last_h1 = df_h1.tail(5).to_dict(orient='records')
    
    current_atr = df_h1.iloc[-1]['atr']
    
    system_instruction = f"""
    VOCÊ É UM GESTOR DE RISCO E TRADER INSTITUCIONAL SÊNIOR (Forex/Indices).
    Sua prioridade máxima é a PRESERVAÇÃO DE CAPITAL. Você opera Swing Trades curtos (24-48h).
    
    ESTRATÉGIA (Top-Down):
    1. H4 (Contexto): Identifique a tendência (EMA 20/50/200) e Zonas de Liquidez (FVG).
    2. H1 (Gatilho): Procure Market Structure Shift (MSS) e Divergências de RSI.
    3. ATR ({current_atr:.5f}): Use para calibrar volatilidade.
    
    DADOS FORNECIDOS (OHLC + Indicadores):
    - H4 (Últimas 3 velas): {json.dumps(last_h4)}
    - H1 (Últimas 5 velas): {json.dumps(last_h1)}
    
    TAREFA:
    Analise passo-a-passo. Pense sobre a estrutura de mercado.
    Retorne APENAS um JSON estrito no seguinte formato (sem markdown):
    {{
        "thought_process": "Breve explicação do raciocínio (máx 20 palavras)",
        "action": "BUY", "SELL" ou "HOLD",
        "confidence": 0 a 100
    }}
    """
    return system_instruction

# --- 3. ROTAS ---

@app.route('/', methods=['GET'])
def health_check():
    """Rota para teste de conexão simples."""
    return jsonify({"status": "online", "model": MODEL_NAME}), 200

@app.route('/analisar', methods=['POST'])
def analisar():
    try:
        data = request.get_json()
        
        # Verifica se é apenas um ping de teste do EA
        if data.get('test_connection') == True:
             return jsonify({"status": "connected", "message": "Conexão IA Estabelecida"}), 200

        # Processamento de Dados
        raw_h4 = data.get('h4', [])
        raw_h1 = data.get('h1', [])
        
        if not raw_h4 or not raw_h1:
            return jsonify({"error": "Dados insuficientes"}), 400

        # Converter para DataFrame
        df_h4 = pd.DataFrame(raw_h4)
        df_h1 = pd.DataFrame(raw_h1)
        
        # Calcular Indicadores
        df_h4 = calculate_indicators(df_h4)
        df_h1 = calculate_indicators(df_h1)
        
        # Gerar Prompt
        prompt = generate_prompt(df_h4, df_h1)
        
        # Chamar Gemini
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        
        # Limpar resposta (remover markdown json se houver)
        text_response = response.text.strip().replace('```json', '').replace('```', '')
        
        try:
            ai_decision = json.loads(text_response)
        except json.JSONDecodeError:
            # Fallback se a IA não retornar JSON puro
            logger.error(f"Erro ao decodificar JSON da IA: {text_response}")
            return "HOLD", 200

        # Aplicar Guardrails (Filtro Final)
        final_action = safety_guardrails(ai_decision, df_h4, df_h1)
        
        # Log para debug no Coolify
        logger.info(f"IA: {ai_decision.get('action')} | Confiança: {ai_decision.get('confidence')} | Final: {final_action}")

        # Retorna string limpa conforme regra 5
        return final_action, 200

    except Exception as e:
        logger.error(f"Erro no servidor: {str(e)}")
        return "HOLD", 200

# --- 4. INICIALIZAÇÃO ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
