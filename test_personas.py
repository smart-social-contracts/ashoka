#!/usr/bin/env python3
"""
Test script for multi-persona functionality
"""
import requests
import json
import time

API_BASE = "http://localhost:5000"

def test_list_personas():
    """Test listing available personas"""
    print("=== Testing Persona Listing ===")
    response = requests.get(f"{API_BASE}/api/personas")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data['personas'])} personas:")
        for persona in data['personas']:
            status = "🔸 DEFAULT" if persona['is_default'] else "🔹"
            print(f"  {status} {persona['name']}: {persona['description'][:80]}...")
        print(f"Default persona: {data['default_persona']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    print()

def test_persona_details(persona_name):
    """Test getting specific persona details"""
    print(f"=== Testing Persona Details: {persona_name} ===")
    response = requests.get(f"{API_BASE}/api/personas/{persona_name}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Persona: {data['name']}")
        print(f"Content length: {len(data['content'])} characters")
        print(f"Validation: {'✅ Valid' if data['validation']['valid'] else '❌ Invalid'}")
        if data['validation']['warnings']:
            print(f"Warnings: {', '.join(data['validation']['warnings'])}")
        print(f"Stats: {data['validation']['stats']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    print()

def test_ask_with_persona(persona_name, question):
    """Test asking a question with a specific persona"""
    print(f"=== Testing Ask with Persona: {persona_name} ===")
    
    payload = {
        "question": question,
        "persona": persona_name,
        "user_principal": "test-user-123",
        "realm_principal": "test-realm-456"
    }
    
    response = requests.post(f"{API_BASE}/api/ask", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Question: {question}")
        print(f"Persona used: {data.get('persona_used', 'unknown')}")
        print(f"Answer: {data['answer'][:200]}...")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    print()

def test_suggestions_with_persona(persona_name):
    """Test getting suggestions with a specific persona"""
    print(f"=== Testing Suggestions with Persona: {persona_name} ===")
    
    params = {
        "persona": persona_name,
        "user_principal": "test-user-123",
        "realm_principal": "test-realm-456"
    }
    
    response = requests.get(f"{API_BASE}/suggestions", params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Persona used: {data.get('persona_used', 'unknown')}")
        print("Suggestions:")
        for i, suggestion in enumerate(data['suggestions'], 1):
            print(f"  {i}. {suggestion}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    print()

def test_create_persona():
    """Test creating a new persona"""
    print("=== Testing Persona Creation ===")
    
    new_persona = {
        "name": "analyst",
        "content": """You are a Data Analyst, an AI specialist in interpreting governance metrics and providing data-driven insights for decentralized communities.

Your role is to analyze quantitative data, identify trends, and provide evidence-based recommendations for governance improvements.

== Your Expertise ==

As a data analyst, you excel at:
1. Interpreting governance metrics and KPIs
2. Identifying trends and patterns in community data
3. Creating data visualizations and reports
4. Benchmarking against industry standards
5. Predicting future governance outcomes
6. Measuring the impact of governance changes

== Analytical Approach ==

Your analysis focuses on:
- **Metrics**: Quantitative measurement of governance health
- **Trends**: Historical patterns and future projections
- **Benchmarks**: Comparisons with similar communities
- **ROI**: Return on investment for governance initiatives
- **Risk Assessment**: Data-driven risk identification

== Communication Style ==

Your responses are:
1. Data-driven with specific metrics and numbers
2. Objective and evidence-based
3. Clear about statistical significance
4. Visual when describing trends
5. Actionable with measurable outcomes"""
    }
    
    response = requests.post(f"{API_BASE}/api/personas", json=new_persona)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Created persona: {new_persona['name']}")
        print(f"Message: {data['message']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    print()

def main():
    """Run all persona tests"""
    print("🚀 Starting Multi-Persona Functionality Tests\n")
    
    # Test 1: List all personas
    test_list_personas()
    
    # Test 2: Get details for each persona
    personas_to_test = ["ashoka", "advisor", "facilitator"]
    for persona in personas_to_test:
        test_persona_details(persona)
    
    # Test 3: Create a new persona
    test_create_persona()
    
    # Wait a moment for persona to be created
    time.sleep(1)
    
    # Test 4: Test the new persona
    test_persona_details("analyst")
    
    # Test 5: Ask questions with different personas
    question = "How can we improve participation in our governance system?"
    
    for persona in ["ashoka", "advisor", "facilitator", "analyst"]:
        test_ask_with_persona(persona, question)
    
    # Test 6: Get suggestions with different personas
    for persona in ["ashoka", "advisor", "facilitator"]:
        test_suggestions_with_persona(persona)
    
    # Test 7: Test fallback behavior (non-existent persona)
    test_ask_with_persona("nonexistent", "What should I do?")
    
    print("🎉 Multi-Persona Tests Completed!")

if __name__ == "__main__":
    main()
