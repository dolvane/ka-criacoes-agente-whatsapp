"""
KA Criações — Agente de Atendimento WhatsApp com Claude IA
Recebe mensagens do WhatsApp e responde automaticamente usando Claude.
"""
import os, json, requests
from flask import Flask, request, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)
claude = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

WHATSAPP_TOKEN    = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID   = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
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
3. Confirma o pedido e paga 50% de sinal (PIX)
4. Produção em 5 a 7 dias úteis
5. Aprovação da arte antes de produzir
6. Entrega em Uberlândia ou Correios para todo o Brasil

COMO VOCÊ DEVE SE COMPORTAR:
- Seja simpática, acolhedora e use linguagem próxima e carinhosa
- Use emojis com moderação
- Sempre pergunte o nome do cliente ao início
- Quando o cliente quiser comprar, peça: nome para personalização, número/texto desejado, cor preferida
- Informe que o prazo é de 5 a 7 dias úteis
- Para fechar pedido, peça o endereço completo para calcular frete
- Nunca invente preços — diga que vai verificar e confirmar
- Se não souber responder, diga que vai chamar a Katia

SAUDAÇÃO INICIAL:
Quando alguém escrever pela primeira vez, se apresente como assistente da KA Criações e pergunte o nome."""


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
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    return resp.json()


def responder_com_claude(telefone: str, mensagem_cliente: str) -> str:
    """Gera resposta usando Claude com histórico da conversa."""
    if telefone not in conversas:
        conversas[telefone] = []

    conversas[telefone].append({
        "role": "user",
        "content": mensagem_cliente
    })

    # Mantém apenas as últimas 20 mensagens para economizar tokens
    historico = conversas[telefone][-20:]

    resposta = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=SISTEMA,
        messages=historico
    )

    texto = resposta.content[0].text

    conversas[telefone].append({
        "role": "assistant",
        "content": texto
    })

    return texto


@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    """Verificação do webhook pela Meta."""
    mode      = request.args.get('hub.mode')
    token     = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print(f'✅ Webhook verificado!')
        return challenge, 200
    return 'Token inválido', 403


@app.route('/webhook', methods=['POST'])
def receber_mensagem():
    """Recebe mensagens do WhatsApp e responde com Claude."""
    data = request.json

    try:
        entry    = data['entry'][0]
        changes  = entry['changes'][0]
        value    = changes['value']

        if 'messages' not in value:
            return jsonify({'status': 'sem mensagem'}), 200

        msg      = value['messages'][0]
        telefone = msg['from']
        tipo     = msg.get('type', '')

        if tipo == 'text':
            texto = msg['text']['body']
            print(f'📨 [{telefone}]: {texto}')

            resposta = responder_com_claude(telefone, texto)
            enviar_whatsapp(telefone, resposta)

            print(f'🤖 Resposta: {resposta}')

        elif tipo == 'audio':
            enviar_whatsapp(telefone,
                'Oi! Por enquanto só consigo ler mensagens de texto. '
                'Pode escrever o que precisa? 😊')

        elif tipo == 'image':
            enviar_whatsapp(telefone,
                'Recebi sua imagem! Para pedir um produto personalizado, '
                'pode me descrever o que deseja por texto? 😊')

    except (KeyError, IndexError):
        pass

    return jsonify({'status': 'ok'}), 200


@app.route('/status', methods=['GET'])
def status():
    """Verifica se o agente está rodando."""
    return jsonify({
        'status': 'online',
        'empresa': 'KA Criações',
        'conversas_ativas': len(conversas)
    })


if __name__ == '__main__':
    print()
    print('🤖 KA Criações — Agente WhatsApp iniciado!')
    print('📍 Webhook: http://localhost:5000/webhook')
    print('📊 Status:  http://localhost:5000/status')
    print()
    app.run(host='0.0.0.0', port=5000, debug=False)
