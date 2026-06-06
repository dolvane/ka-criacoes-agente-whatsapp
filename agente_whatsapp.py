"""
KA Criações — Agente de Atendimento WhatsApp com Claude IA
"""
import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
WHATSAPP_TOKEN    = os.getenv('WHATSAPP_TOKEN', '')
PHONE_NUMBER_ID   = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
VERIFY_TOKEN      = os.getenv('WEBHOOK_VERIFY_TOKEN', 'kacriacoes2026')

# Memória de conversas por cliente
conversas = {}

SISTEMA = """Você é a assistente virtual da KA Criações, empresa de presentes personalizados de Uberlândia, MG.

SOBRE A KA CRIAÇÕES:
- Presentes personalizados que emocionam
- Produtos: plaquinhas, porta-lápis, topos de bolo, tags de coleira para pets, comedouros, lembrancinhas, decoração personalizada
- Atende: crianças, adultos, pets e datas especiais
- Entrega em todo o Brasil
- Instagram: @katiaa.criacoes
- WhatsApp: (34) 99771-3939

PROCESSO DE PEDIDO:
1. Cliente escolhe o produto
2. Informa nome/personalização desejada
3. Confirma o pedido e paga 50% de sinal via PIX
4. Produção em 5 a 7 dias úteis
5. Aprovação da arte antes de produzir
6. Entrega em Uberlândia ou Correios para todo o Brasil

COMO SE COMPORTAR:
- Seja simpática, acolhedora e use linguagem próxima e carinhosa
- Use emojis com moderação
- Sempre pergunte o nome do cliente ao início
- Para fechar pedido, peça o endereço completo para calcular frete
- Nunca invente preços — diga que vai verificar e confirmar
- Se não souber responder, diga que vai chamar a Katia"""


def responder_com_claude(telefone: str, mensagem: str) -> str:
    """Gera resposta usando a API do Claude diretamente."""
    if telefone not in conversas:
        conversas[telefone] = []

    conversas[telefone].append({"role": "user", "content": mensagem})

    historico = conversas[telefone][-20:]

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": "claude-haiku-4-5",
        "max_tokens": 500,
        "system": SISTEMA,
        "messages": historico
    }

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=body,
        timeout=30
    )

    texto = resp.json()["content"][0]["text"]
    conversas[telefone].append({"role": "assistant", "content": texto})
    return texto


def enviar_whatsapp(telefone: str, mensagem: str):
    """Envia mensagem via WhatsApp Cloud API."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {"body": mensagem}
    }
    requests.post(url, headers=headers, json=body, timeout=15)


@app.route('/', methods=['GET'])
def home():
    return jsonify({'status': 'online', 'servico': 'KA Criações — Agente WhatsApp'})


@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    mode      = request.args.get('hub.mode')
    token     = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print('Webhook verificado!')
        return challenge, 200
    return 'Token inválido', 403


@app.route('/webhook', methods=['POST'])
def receber_mensagem():
    data = request.json
    try:
        msg      = data['entry'][0]['changes'][0]['value']['messages'][0]
        telefone = msg['from']
        tipo     = msg.get('type', '')

        if tipo == 'text':
            texto    = msg['text']['body']
            resposta = responder_com_claude(telefone, texto)
            enviar_whatsapp(telefone, resposta)
        elif tipo == 'audio':
            enviar_whatsapp(telefone, 'Por enquanto só consigo ler mensagens de texto. Pode escrever o que precisa? 😊')
        elif tipo == 'image':
            enviar_whatsapp(telefone, 'Recebi sua imagem! Para pedir um produto, pode me descrever por texto? 😊')
    except (KeyError, IndexError):
        pass

    return jsonify({'status': 'ok'}), 200


@app.route('/status', methods=['GET'])
def status():
    return jsonify({'status': 'online', 'conversas_ativas': len(conversas)})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
