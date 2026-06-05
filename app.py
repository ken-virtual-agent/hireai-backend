"""
HireAI Backend Service
Handles hire requests and AI agent chat for hireai.kenagent.xyz
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Configuration
DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
HIRE_FILE = DATA_DIR / 'hires.json'

# AI Agent definitions (backed by n8n workflows)
AI_AGENTS = {
    'Luna': {
        'name': 'Luna',
        'role': 'AI Receptionist',
        'avatar': '🌙',
        'price': '$49/month',
        'description': 'Handles front desk, bookings, pricing & insurance inquiries',
        'system_prompt': 'You are Luna, a professional AI receptionist for businesses. Always be friendly, professional, and helpful.'
    },
    'Max': {
        'name': 'Max',
        'role': 'AI Sales Representative',
        'avatar': '💰',
        'price': '$79/month',
        'description': 'Lead qualification, demos, pricing & closing deals',
        'system_prompt': 'You are Max, a professional AI sales representative. Always be persuasive but never pushy.'
    },
    'Emma': {
        'name': 'Emma',
        'role': 'AI HR Assistant',
        'avatar': '👥',
        'price': '$59/month',
        'description': 'Onboarding, policies, benefits & workplace guidance',
        'system_prompt': 'You are Emma, a professional AI HR assistant. Always be confidential, supportive, and compliant.'
    },
    'Sarah': {
        'name': 'Sarah',
        'role': 'AI Customer Support',
        'avatar': '🎧',
        'price': '$69/month',
        'description': 'Issue resolution, troubleshooting & escalations',
        'system_prompt': 'You are Sarah, a professional AI customer support agent. Always be empathetic, patient, and solution-oriented.'
    },
    'Mike': {
        'name': 'Mike',
        'role': 'AI Marketing Assistant',
        'avatar': '📣',
        'price': '$89/month',
        'description': 'Campaigns, content, social media & analytics',
        'system_prompt': 'You are Mike, a professional AI marketing assistant. Always be creative, data-driven, and results-focused.'
    },
    'Alex': {
        'name': 'Alex',
        'role': 'AI IT Support',
        'avatar': '🖥️',
        'price': '$69/month',
        'description': 'Tech issues, software, network & password resets',
        'system_prompt': 'You are Alex, a professional AI IT support specialist. Always be patient, clear, and step-by-step.'
    },
    'Rachel': {
        'name': 'Rachel',
        'role': 'AI Legal Assistant',
        'avatar': '⚖️',
        'price': '$119/month',
        'description': 'Document review, contracts & compliance guidance',
        'system_prompt': 'You are Rachel, a professional AI legal assistant. Always be precise, thorough, and careful.'
    },
    'David': {
        'name': 'David',
        'role': 'AI Project Manager',
        'avatar': '📋',
        'price': '$99/month',
        'description': 'Task planning, tracking, resources & risk management',
        'system_prompt': 'You are David, a professional AI project manager. Always be organized, proactive, and deadline-focused.'
    },
    'Lisa': {
        'name': 'Lisa',
        'role': 'AI Finance Assistant',
        'avatar': '💵',
        'price': '$99/month',
        'description': 'Budgets, expenses, invoices & financial reporting',
        'system_prompt': 'You are Lisa, a professional AI finance assistant. Always be accurate, detail-oriented, and compliant.'
    },
    'Tom': {
        'name': 'Tom',
        'role': 'AI Training Coordinator',
        'avatar': '🎓',
        'price': '$59/month',
        'description': 'Training programs, scheduling & skill assessments',
        'system_prompt': 'You are Tom, a professional AI training coordinator. Always be encouraging, structured, and results-driven.'
    }
}

def load_hires():
    """Load hire records from file"""
    if HIRE_FILE.exists():
        with open(HIRE_FILE, 'r') as f:
            return json.load(f)
    return []

def save_hires(hires):
    """Save hire records to file"""
    with open(HIRE_FILE, 'w') as f:
        json.dump(hires, f, indent=2)

import json as json_lib
import os

N8N_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'n8n_agents.json')

def _load_n8n_config():
    try:
        with open(N8N_CONFIG_PATH) as f:
            return json_lib.load(f)
    except:
        return {'n8n_base': 'https://dongle036-n8n.dochelper.org', 'agents': {}}

def call_n8n_agent(agent_name, user_message, session_id=None):
    """Call n8n agent webhook - reads URL from n8n_agents.json"""
    config = _load_n8n_config()
    agents = config.get('agents', {})
    agent_cfg = agents.get(agent_name)
    if not agent_cfg:
        print(f"n8n: no config for agent '{agent_name}'")
        return None
    base = config.get('n8n_base', '')
    webhook = agent_cfg.get('webhook', '')
    url = f"{base}{webhook}"
    try:
        response = requests.get(
            url,
            params={'q': user_message, 'sessionId': session_id or 'default'},
            timeout=60
        )
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get('output')
                if isinstance(data, dict):
                    return data.get('output') or data.get('response') or str(data)
                return str(data)
            except:
                return response.text or None
        return None
    except Exception as e:
        print(f"n8n call failed ({url}): {e}")
        return None

def call_llm(messages, model="anthropic/claude-3-haiku"):
    """Fallback: Call LLM via OpenRouter API"""

    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + os.environ.get('OPENROUTER_API_KEY', ''),
                'HTTP-Referer': 'https://hireai.kenagent.xyz',
                'X-Title': 'HireAI Agents'
            },
            json={
                'model': model,
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        print(f"OpenRouter error: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"LLM call failed: {e}")
        return None

def get_persona_response(agent_name, user_message):
    """Generate realistic persona-specific responses when LLM is unavailable"""
    import random
    
    responses = {
        'Luna': [
            f"Hi there! I'm Luna, your AI receptionist. I'd love to help you with that! Let me note down your request and get back to you right away. Is there anything else I can assist with today?",
            f"Welcome! Luna here, ready to help. I've received your message and I'm on it. As your receptionist, I make sure nothing falls through the cracks. What else can I do for you?",
            f"Hello! This is Luna. Thank you for reaching out! I'm handling your request now. In the meantime, is there anything else I can help you with? I'm here 24/7!",
            f"Hi! Luna at your service. I've got your message and I'm working on it. As your AI receptionist, I'm here to make sure you get the help you need. What else can I assist with?"
        ],
        'Atlas': [
            f"Hey! Atlas here, your content creator. I love that idea! Let me brainstorm some creative angles for this. I'll have some fresh content ready for you shortly. What's the vibe you're going for?",
            f"Great request! I'm Atlas and I'm already thinking about how to make this pop. Content is my passion. Give me a moment and I'll come back with something awesome. Any specific tone or style you prefer?",
            f"Love it! Atlas reporting in. I'm on board with this and I can already see some great directions we could take. I'll draft something up for you. What platform are we targeting?",
            f"This is right up my alley! I'm Atlas, your AI content creator. I'm excited about this project. Let me put together some options for you. Any brand guidelines I should follow?"
        ],
        'Cleo': [
            f"Hi! Cleo here, your scheduling expert. I've got your request logged and I'm checking availability right now. I'll find the perfect time slot for you. Do you have any preferences for date or time?",
            f"Hello! This is Cleo. I'm already looking at the calendar to find the best option for you. I make sure there are no conflicts. What day works best for you?",
            f"Hey there! Cleo at your service. I'm organizing your schedule now. I'll make sure everything is coordinated perfectly. Any specific time you'd prefer?",
            f"Hi! I'm Cleo and I'm on it. Checking all the calendars now to find the ideal slot. I never miss a detail! Do you have any scheduling constraints I should know about?"
        ],
        'Max': [
            f"Hello! Max here, your analytics specialist. I'm pulling the data now and running the analysis. I'll have insights for you shortly. What specific metrics are you most interested in?",
            f"Hi! This is Max. I'm already diving into the numbers. Data doesn't lie, and I'll make sure you get clear, actionable insights. Any particular KPIs you want me to focus on?",
            f"Hey! Max reporting in. I'm crunching the data as we speak. I'll have a comprehensive report ready for you. What time frame should I analyze?",
            f"Hello! I'm Max, your AI analytics expert. I'm processing your request now. I always deliver precise, data-driven insights. What's the priority metric for this analysis?"
        ],
        'Zara': [
            f"Hey! Zara here, your sales champion. I love this opportunity! Let me qualify this lead and get the ball rolling. I'll have a strategy ready for you. What's the budget range we're working with?",
            f"Hi! This is Zara and I'm excited about this. I'm already thinking about how to close this deal. I'll prepare a tailored approach for you. What's the decision timeline?",
            f"Hello! Zara at your service. I'm on it and I can already see the potential here. I'll craft the perfect pitch. What are the key pain points we should address?",
            f"Hey there! I'm Zara, your AI sales rep. I'm fired up about this opportunity. Let me put together a winning strategy. What's the main objection we need to overcome?"
        ],
        'Oliver': [
            f"Hi! Oliver here, your customer support specialist. I'm sorry you're experiencing this issue. I'm looking into it right now and I'll get this resolved for you. Can you tell me a bit more about what's happening?",
            f"Hello! This is Oliver. Thank you for reaching out. I'm already checking on this and I want to make sure we get this sorted for you. How long has this been an issue?",
            f"Hey there! Oliver at your service. I understand your concern and I'm on it. I aim to resolve this quickly. Can you share any error messages or screenshots?",
            f"Hi! I'm Oliver and I'm here to help. I'm investigating this now and I'll make sure you get a proper solution. What's the impact this is having on your work?"
        ]
    }
    
    agent_responses = responses.get(agent_name, [f"Hi! I'm {agent_name}, your AI assistant. I received your message and I'm here to help. How can I assist you today?"])
    return random.choice(agent_responses)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'hireai-backend'})

@app.route('/hire', methods=['POST'])
def handle_hire():
    """Handle new hire request"""
    try:
        data = request.json
        
        if not data or 'agent' not in data or 'user' not in data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        agent_info = data['agent']
        user_info = data['user']
        
        # Validate agent exists
        if agent_info.get('name') not in AI_AGENTS:
            return jsonify({'error': 'Invalid agent'}), 400
        
        # Create hire record
        hire_record = {
            'id': str(uuid.uuid4())[:8],
            'agent': agent_info,
            'user': user_info,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        # Save to file
        hires = load_hires()
        hires.append(hire_record)
        save_hires(hires)
        
        print(f"New hire: {agent_info.get('name')} for {user_info.get('business')}")
        
        return jsonify({
            'success': True,
            'message': 'AI agent hired successfully!',
            'hireId': hire_record['id'],
            'agent': agent_info.get('name'),
            'nextSteps': [
                'Check your email for setup instructions',
                'Your AI agent will be ready in 5 minutes',
                'You can start chatting immediately'
            ]
        })
        
    except Exception as e:
        print(f"Hire error: {e}")
        return jsonify({'error': 'Failed to process hire request'}), 500

@app.route('/chat', methods=['POST'])
def handle_chat():
    """Handle chat message - n8n primary, OpenRouter fallback"""
    try:
        data = request.json
        
        if not data or 'agent' not in data or 'message' not in data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        agent_name = data['agent'].get('name')
        user_message = data['message']
        session_id = data.get('sessionId')
        
        agent = AI_AGENTS.get(agent_name)
        if not agent:
            return jsonify({'error': 'Invalid agent'}), 400
        
        # Primary: n8n
        source = 'n8n'
        response = call_n8n_agent(agent_name, user_message, session_id)
        
        # Fallback: OpenRouter
        if not response:
            source = 'openrouter'
            messages = [
                {'role': 'system', 'content': agent['system_prompt']},
                {'role': 'user', 'content': user_message}
            ]
            response = call_llm(messages)
        
        if response:
            return jsonify({'success': True, 'response': response, 'agent': agent_name, 'source': source})
        else:
            fallback = f"Hi! I'm {agent_name}, your {agent['role']}. I received your message but I'm having trouble connecting right now. Please try again in a moment!"
            return jsonify({'success': True, 'response': fallback, 'agent': agent_name})
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': 'Failed to process chat message'}), 500

@app.route('/agents')
def list_agents():
    """List available AI agents"""
    agents = []
    for name, agent in AI_AGENTS.items():
        agents.append({
            'name': agent['name'],
            'role': agent['role'],
            'avatar': agent['avatar'],
            'price': agent['price']
        })
    return jsonify({'agents': agents})

@app.route('/hires')
def list_hires():
    """List all hire records"""
    hires = load_hires()
    return jsonify({'hires': hires})

if __name__ == '__main__':
    print("Starting HireAI Backend Service...")
    print(f"Data directory: {DATA_DIR}")
    app.run(host='0.0.0.0', port=5000, debug=False)
