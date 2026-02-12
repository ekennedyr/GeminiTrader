import os
import google.generativeai as genai
from flask import Flask, request
from dotenv import load_dotenv

# Configuração Básica
load_dotenv()
app = Flask(__name__)

# Configura Gemini
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"Erro API: {e}")

# Rota para verificar pelo navegador se o server está online
@app.route('/')
def home():
    return "Servidor Online! Use o endpoint /teste para o MT5.", 200

# Rota de Teste para o MT5
@app.route('/teste', methods=['POST'])
def teste_conexao():
    try:
        dados = request.get_json()
        mensagem_mt5 = dados.get('mensagem', 'Nada recebido')
        
        print(f"Recebido do MT5: {mensagem_mt5}")
        
        # Pede ao Gemini uma resposta curta
        prompt = f"O usuário enviou este teste de conexão: '{mensagem_mt5}'. Responda com uma frase curta, engraçada e motivacional para um trader."
        
        response = model.generate_content(prompt)
        resposta_texto = response.text.strip()
        
        return resposta_texto, 200

    except Exception as e:
        return f"Erro no processamento: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

