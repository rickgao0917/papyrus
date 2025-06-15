#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify
import markdown2
import re
import requests
import json

app = Flask(__name__)

# Gemini API configuration
GEMINI_API_KEY = 'AIzaSyDPTPoMcdtMztnh34o8YGvZYm81NqP7oCg'

def send_to_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
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


def escape_html(text):
    """Simple HTML escaping"""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#039;'))

def process_other_markdown(content):
    """Process other markdown elements while preserving nested code blocks"""
    # Bold
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    
    # Italic
    content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
    
    # Headers
    content = re.sub(r'^### (.*$)', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.*$)', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^# (.*$)', r'<h1>\1</h1>', content, flags=re.MULTILINE)
    
    # Links
    content = re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', content)
    
    # Inline code
    content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
    
    # Line breaks
    content = content.replace('\n', '<br>')
    
    return content

def process_custom_block_content(content):
    """Process content inside llm blocks with proper nested code block handling"""
    print(f"[DEBUG] Processing custom block content: {content[:100]}...")
    
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        code_block_match = re.match(r'^```(\w+)$', line)
        
        if code_block_match:
            # Found start of nested code block
            language = code_block_match.group(1)
            print(f"[DEBUG] Found nested code block: {language}")
            code_content = []
            i += 1  # Skip the opening line
            
            # Collect all lines until we find the closing ```
            while i < len(lines) and lines[i].strip() != '```':
                code_content.append(lines[i])
                i += 1
            
            print(f"[DEBUG] Code content lines: {len(code_content)}")
            if code_content:
                print(f"[DEBUG] First line: {code_content[0][:50]}")
            
            code_html = escape_html('\n'.join(code_content))
            result.append(f'<div class="nested-code-block">\n<pre><code class="language-{language}">{code_html}</code></pre>\n</div>')
            
            if i < len(lines):
                i += 1  # Skip the closing ``` if we found it
        else:
            # Regular line in custom block
            result.append(line)
            i += 1
    
    # Process other markdown in the result
    processed = '\n'.join(result)
    processed = process_other_markdown(processed)
    
    print(f"[DEBUG] Final processed content: {processed[:200]}...")
    return processed

def parse_nested_code_blocks(markdown):
    """Parse markdown with nested code blocks for llm_r and llm_p"""
    lines = markdown.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if line in ['```llm_r', '```llm_p']:
            block_type = line[3:]  # Remove ```
            custom_content = []
            i += 1  # Skip the opening line
            
            # Keep track of nested code block state
            in_nested_code_block = False
            
            while i < len(lines):
                current_line = lines[i]
                
                # Check if this is a code block delimiter
                if current_line.strip() == '```':
                    if in_nested_code_block:
                        # This closes a nested code block
                        in_nested_code_block = False
                        custom_content.append(current_line)
                        i += 1
                    else:
                        # This closes the main llm block
                        break
                elif re.match(r'^```\w+$', current_line.strip()):
                    # This opens a nested code block
                    in_nested_code_block = True
                    custom_content.append(current_line)
                    i += 1
                else:
                    custom_content.append(current_line)
                    i += 1
            
            # Process the content inside the custom block
            raw_content = '\n'.join(custom_content)
            print(f"[DEBUG] Raw content for {block_type}: {raw_content[:200]}...")
            processed_content = process_custom_block_content(raw_content)
            
            # Create the styled container
            css_class = 'llm-response' if block_type == 'llm_r' else 'llm-prompt'
            result.append(f'<div class="{css_class}">\n{processed_content}\n</div>')
            
            i += 1  # Skip the closing ```
        else:
            # Regular markdown line
            result.append(line)
            i += 1
    
    return '\n'.join(result)

def process_special_blocks(text):
    """Process llm_r and llm_p code blocks using the nested parser"""
    # Use the nested parser for special blocks
    parsed_text = parse_nested_code_blocks(text)
    
    # Render the remaining markdown (non-special blocks)
    html = markdown2.markdown(parsed_text, extras=['fenced-code-blocks', 'tables', 'strike', 'task_list'])
    
    return html

@app.route('/')
def index():
    return render_template('editor.html')

@app.route('/render', methods=['POST'])
def render_markdown():
    markdown_text = request.json.get('markdown', '')
    
    # First process special blocks
    processed_text = process_special_blocks(markdown_text)
    
    # Then render the remaining markdown
    html = markdown2.markdown(processed_text, extras=['fenced-code-blocks', 'tables', 'strike', 'task_list'])
    
    return jsonify({'html': html})

@app.route('/gemini', methods=['POST'])
def call_gemini():
    prompt = request.json.get('prompt', '')
    print(f"[DEBUG] Received prompt: {prompt[:100]}...")
    print(f"[DEBUG] Calling Gemini API...")
    response = send_to_gemini(prompt)
    print(f"[DEBUG] Gemini response: {response[:100]}...")
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True, port=5000)