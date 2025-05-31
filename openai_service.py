import os
import json
import logging
from openai import OpenAI

# The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# Do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    openai_client = None
    logging.warning("OPENAI_API_KEY not found in environment variables")

def explain_quote(quote_text, author):
    """Get an AI explanation of a philosophical quote"""
    if not openai_client:
        return "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
    
    try:
        prompt = f"Explain this philosophical quote in simple, accessible terms. Break down its meaning, context, and relevance to modern life:\n\n\"{quote_text}\" — {author}\n\nProvide a clear, engaging explanation that helps someone understand the deeper meaning."
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a wise philosophy teacher who explains complex philosophical concepts in simple, relatable terms. Your explanations are insightful, accessible, and engaging."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error getting quote explanation: {e}")
        return f"Sorry, I couldn't provide an explanation right now. Error: {str(e)}"

def chat_about_quote(quote_text, author, user_message, conversation_history=None):
    """Continue a conversation about a philosophical quote"""
    if not openai_client:
        return "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
    
    try:
        # Build conversation context
        messages = [
            {
                "role": "system",
                "content": f"You are discussing this philosophical quote with a user: \"{quote_text}\" — {author}. "
                          f"Be thoughtful, engaging, and help them explore the deeper meanings and applications of this philosophy. "
                          f"Keep responses concise but insightful."
            }
        ]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=300,
            temperature=0.8
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error in chat conversation: {e}")
        return f"Sorry, I couldn't respond right now. Error: {str(e)}"
