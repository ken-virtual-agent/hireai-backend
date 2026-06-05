#!/usr/bin/env python3
"""
Create HireAI webhook workflow in n8n
This workflow handles hire requests and AI agent chat messages
"""

import requests
import json
import sys

N8N_BASE = 'https://dongle036-n8n.dochelper.org'
N8N_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyYTRiOWU3Ni02MWM5LTQyYjQtYTRjNy0zMmQ5MTgyY2I0OTEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiY2RkNmE0NGYtNDdkMS00ZTVkLWExMzQtN2U5MDZmYzcxNjE3IiwiaWF0IjoxNzc5NzIxMDI0fQ.iZTfyMptTGEzqAF_TAd-tfRi9PFRmIndOxRL-EOiM5A'

HEADERS = {
    'Authorization': f'Bearer {N8N_TOKEN}',
    'Content-Type': 'application/json'
}

def list_workflows():
    """List existing workflows"""
    print("=== Listing existing workflows ===")
    resp = requests.get(f'{N8N_BASE}/rest/workflows', headers=HEADERS)
    print(f"Status: {resp.status_code}")
    print(f"Response type: {type(resp.text)}")
    print(f"First 500 chars: {resp.text[:500]}")
    return resp.json()

def create_hireai_workflow():
    """Create the HireAI webhook workflow"""
    
    workflow = {
        'name': 'HireAI - Handle hire requests & AI chat',
        'active': True,
        'nodes': [
            {
                'parameters': {
                    'httpMethod': 'POST',
                    'path': 'hireai',
                    'responseMode': 'responseNode',
                    'options': {}
                },
                'name': 'Webhook',
                'type': 'n8n-nodes-base.webhook',
                'typeVersion': 2,
                'position': [240, 300],
                'id': 'webhook-1'
            },
            {
                'parameters': {
                    'conditions': {
                        'string': [
                            {
                                'value1': '={{ $json.type }}',
                                'operation': 'equals',
                                'value2': 'hire'
                            }
                        ]
                    }
                },
                'name': 'Check Request Type',
                'type': 'n8n-nodes-base.if',
                'typeVersion': 2,
                'position': [480, 300],
                'id': 'if-1'
            },
            {
                'parameters': {
                    'mode': 'manual',
                    'functionCode': '// Handle hire request\nconst hireData = {
    id: Date.now().toString(),
    agent: $input.item.json.agent,
    user: $input.item.json.user,
    timestamp: new Date().toISOString(),
    status: "active"
};

// In production, you would save this to a database
// For now, just return the hire confirmation
return {
    json: {
        success: true,
        message: "AI agent hired successfully!",
        hireId: hireData.id,
        agent: hireData.agent.name,
        nextSteps: [
            "Check your email for setup instructions",
            "Your AI agent will be ready in 5 minutes",
            "You can start chatting immediately"
        ]
    }
};'
                },
                'name': 'Process Hire',
                'type': 'n8n-nodes-base.function',
                'typeVersion': 2,
                'position': [720, 200],
                'id': 'function-hire'
            },
            {
                'parameters': {
                    'mode': 'manual',
                    'functionCode': '// Handle chat message\nconst agentName = $input.item.json.agent ? $input.item.json.agent.name : "AI Agent";
const message = $input.item.json.message;

// In production, you would call an LLM API here
// For now, return a simulated AI response
const responses = [
    "Hi! I'm " + agentName + ", your AI employee. How can I help you today?",
    "I'd be happy to help with that! As your " + agentName + ", I'm here to make your business run smoother.",
    "Great question! Let me assist you with that right away."
];

return {
    json: {
        success: true,
        response: responses[Math.floor(Math.random() * responses.length)],
        agent: agentName
    }
};'
                },
                'name': 'Process Chat',
                'type': 'n8n-nodes-base.function',
                'typeVersion': 2,
                'position': [720, 400],
                'id': 'function-chat'
            },
            {
                'parameters': {
                    'responseMode': 'lastNode',
                    'options': {}
                },
                'name': 'Respond',
                'type': 'n8n-nodes-base.respondToWebhook',
                'typeVersion': 1,
                'position': [960, 300],
                'id': 'respond-1'
            }
        ],
        'connections': {
            'Webhook': {
                'main': [
                    [{'node': 'Check Request Type'}]
                ]
            },
            'Check Request Type': {
                'main': [
                    [{'node': 'Process Hire'}],  // True branch
                    [{'node': 'Process Chat'}]   // False branch
                ]
            },
            'Process Hire': {
                'main': [
                    [{'node': 'Respond'}]
                ]
            },
            'Process Chat': {
                'main': [
                    [{'node': 'Respond'}]
                ]
            }
        }
    }
    
    print("\n=== Creating HireAI workflow ===")
    resp = requests.post(
        f'{N8N_BASE}/rest/workflows',
        headers=HEADERS,
        json=workflow
    )
    
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\n✅ Workflow created successfully!")
        print(f"   ID: {data.get('id')}")
        print(f"   Name: {data.get('name')}")
        return True
    else:
        print(f"\n❌ Failed to create workflow")
        return False

if __name__ == '__main__':
    # First list existing workflows
    try:
        list_workflows()
    except Exception as e:
        print(f"Error listing workflows: {e}")
    
    # Create the HireAI workflow
    success = create_hireai_workflow()
    sys.exit(0 if success else 1)
