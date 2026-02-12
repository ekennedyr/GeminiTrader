import os
import json
import logging
from flask import Flask, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. ESTRUTURA GLOBAL ---
app = Flask(__name__)

# Configuração da API Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

if not GEMINI_API_KEY:
    logger.error("ERRO: GEMINI_API_KEY não encontrada nas variáveis de ambiente.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_trading_decision(market_data):
    """
    Constrói o prompt Chain-of-Thought e consulta o Gemini.
    """
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # System Prompt Baseado na Estratégia SMC/Híbrida
        system_instruction = """
        Você é um Gestor de Risco e Trader Institucional Sênior. Sua prioridade máxima é a preservação de capital.
        Você analisa dados de Forex baseando-se estritamente em Price Action (SMC) e Estrutura de Mercado.
        
        Siga este Chain-of-Thought (Raciocínio Passo-a-Passo):
        1. ANÁLISE MACRO (H4): Identifique a tendência principal e zonas de liquidez (FVG/Order Blocks). O preço está acima/abaixo da EMA 200?
        2. GATILHO MICRO (H1): Procure por Market Structure Shift (MSS) ou rejeição em FVG.
        3. INDICADORES:
           - EMA 20/50/200: Alinhamento de tendência.
           - RSI: Há divergência entre preço e indicador? (Sinal de reversão).
           - ATR: O mercado está volátil? (Ajuste a cautela).
        4. DECISÃO: Com base na confluência H4 + H1.
        
        Responda APENAS com um objeto JSON cru (sem formatação Markdown ```json):
        {"decision": "BUY", "reason": "Breve explicação", "stop_loss_bias": "tight ou wide"}
        
        Possíveis decisões: "BUY", "SELL", "HOLD". Se houver dúvida ou sinais mistos, responda "HOLD".
        """

        prompt = f"""
        {system_instruction}
        
        DADOS DO MERCADO RECEBIDOS:
        {json.dumps(market_data, indent=2)}
        """

        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        # Limpeza de Markdown caso o modelo insira
        if text_response.startswith("```"):
            text_response = text_response.replace("```json", "").replace("```", "")
        
        return text_response

    except Exception as e:
        logger.error(f"Erro na IA: {e}")
        return json.dumps({"decision": "HOLD", "reason": "Erro interno na IA"})

# --- 4. ENDPOINT ---
@app.route('/analisar', methods=['POST'])
def analisar():
    data = request.get_json()
    
    # --- TESTE DE CONEXÃO (Solicitado no Step 2/Teste) ---
    if data and data.get("action") == "TEST_CONNECTION":
        return jsonify({"status": "success", "message": "Conexão Coolify <-> Gemini Operacional"})

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Processar decisão via Gemini
    ai_response_str = generate_trading_decision(data)
    
    try:
        # Tenta fazer o parse para garantir que é JSON válido antes de devolver
        ai_response_json = json.loads(ai_response_str)
        return jsonify(ai_response_json)
    except json.JSONDecodeError:
        # Fallback se a IA retornar texto sujo
        return jsonify({"decision": "HOLD", "reason": "Resposta invalida da IA"})

# --- 3. INICIALIZAÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
