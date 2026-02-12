import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 1. Configurações Iniciais
load_dotenv()
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')

# 2. Definição Global do App (Evita o NameError)
app = Flask(__name__)

# 3. Configuração do Modelo
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Nota: use 'gemini-1.5-flash' (o 2.5 não existe)
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    print(f"Erro ao configurar o Gemini: {e}")
    model = None

def criar_prompt(dados_json):
    timeframe = dados_json.get('timeframe', 'N/A')
    
    if timeframe == 'PERIOD_M1':
        instrucao_tempo = "para os próximos 5 a 15 minutos"
        instrucao_analista = "Você é um analista de Price Action e Scalper."
    elif timeframe == 'PERIOD_H1':
        instrucao_tempo = "para a próxima hora ou mais"
        instrucao_analista = "Você é um analista de Price Action e Swing Trade."
    else:
        instrucao_tempo = "para o próximo período"
        instrucao_analista = "Você é um analista de Price Action."

    dados_str = f"""
    Ativo: {dados_json.get('ativo', 'N/A')}
    Timeframe: {timeframe}
    Valor do RSI(14): {dados_json.get('rsi_14', 'N/A')}
    Valor da Média Móvel(50): {dados_json.get('media_movel_50', 'N/A')}
    """
    
    if 'velas' in dados_json:
        dados_str += "\nÚltimas Velas (O, H, L, C):\n"
        for vela in dados_json['velas']:
            dados_str += f"  - O:{vela['open']}, H:{vela['high']}, L:{vela['low']}, C:{vela['close']}\n"
    
    prompt_final = f"""
    {instrucao_analista} 
    Sua tarefa é analisar os dados de mercado e tomar uma decisão.
    {dados_str}
    Baseado APENAS nos dados fornecidos, qual é a sua recomendação {instrucao_tempo}?
    Responda APENAS com: 'BUY', 'SELL' ou 'HOLD'.
    """
    return prompt_final

@app.route('/analisar', methods=['POST'])
def analisar_dados():
    if not model:
        return "Erro: API do Gemini não configurada", 500

    try:
        dados_mt5 = request.get_json()
        if not dados_mt5:
            return "Erro: Nenhum dado JSON recebido", 400

        prompt = criar_prompt(dados_mt5)
        response = model.generate_content(prompt)
        decisao = response.text.strip().upper()
        
        if decisao not in ['BUY', 'SELL', 'HOLD']:
             decisao = "HOLD"
        
        print(f"Decisão enviada ao MT5: {decisao}")
        return decisao, 200

    except Exception as e:
        print(f"Erro na análise: {e}")
        return "Erro no servidor", 500

# 4. Inicialização compatível com Coolify/Docker
if __name__ == '__main__':
    # O Coolify define a porta automaticamente através da variável PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
