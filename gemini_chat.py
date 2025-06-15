#!/usr/bin/env python3
import requests
import json
import sys
import os

def send_to_gemini(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        if 'candidates' in result and len(result['candidates']) > 0:
            content = result['candidates'][0]['content']
            if 'parts' in content and len(content['parts']) > 0:
                return content['parts'][0]['text']
        
        return "No response generated"
        
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"
    except KeyError as e:
        return f"Unexpected response format: {str(e)}"
    except json.JSONDecodeError:
        return "Error: Invalid JSON response"

def main():
    api_key = 'AIzaSyDPTPoMcdtMztnh34o8YGvZYm81NqP7oCg'
    
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        print("Please set it with: export GEMINI_API_KEY='your_api_key'")
        sys.exit(1)
    
    print("Gemini Flash Terminal Interface")
    print("Type 'quit' or 'exit' to end the session")
    print("-" * 40)
    
    while True:
        try:
            prompt = input("\nYour prompt: ").strip()
            
            if prompt.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break
            
            if not prompt:
                print("Please enter a prompt")
                continue
            
            print("\nGemini Flash response:")
            print("-" * 40)
            response = send_to_gemini(prompt, api_key)
            print(response)
            print("-" * 40)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()