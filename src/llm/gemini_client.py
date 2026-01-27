"""
Gemini LLM Integration for Real Estate RAG
Handles communication with Google's Gemini API
"""
import os
import google.generativeai as genai
from typing import Optional

class GeminiLLM:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize Gemini LLM
        
        Args:
            api_key: Google Cloud API Key
            model_name: Model to use (default: gemini-2.5-flash)
        """
        self.api_key = api_key
        self.model_name = model_name
        self.model = None
        self.available = False
        
        # Usage tracking
        self.usage_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_input_chars': 0,
            'total_output_chars': 0,
            'estimated_input_tokens': 0,
            'estimated_output_tokens': 0,
            'session_start': None
        }
        
        if not api_key:
            print("WARNING: Gemini API Key not provided")
            return
            
        try:
            genai.configure(api_key=api_key)
            
            # Verify model availability
            print(f"Connecting to Gemini ({model_name})...")
            self.model = genai.GenerativeModel(model_name)
            
            # Simple test generation to verify connection
            # We won't run it here to avoid latency during init, 
            # but we assume it works if no immediate error
            self.available = True
            
            # Set session start time
            from datetime import datetime
            self.usage_stats['session_start'] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"WARNING: Gemini API Error: {str(e)}")
            self.available = False

    def is_available(self) -> bool:
        """Check if Gemini is available"""
        return self.available

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate response from Gemini
        
        Args:
            prompt: User query/prompt
            system_prompt: Optional system context (Gemini supports this via system_instruction in newer versions, 
                         or we can prepend it)
                         
        Returns:
            Generated text response
        """
        if not self.available or not self.model:
            return "Gemini is not available."
        
        self.usage_stats['total_requests'] += 1
            
        try:
            # Construct the full prompt
            full_prompt = prompt
            if system_prompt:
                # For simplicity and compatibility, we'll prepend the system prompt
                # Newer Gemini API supports system_instruction in constructor, but we initialized already
                full_prompt = f"{system_prompt}\n\nUser Query: {prompt}"
            
            # Track input
            input_chars = len(full_prompt)
            self.usage_stats['total_input_chars'] += input_chars
            self.usage_stats['estimated_input_tokens'] += input_chars // 4  # Rough estimate: 4 chars per token
            
            response = self.model.generate_content(full_prompt)
            text = response.text
            
            # Track output
            output_chars = len(text)
            self.usage_stats['total_output_chars'] += output_chars
            self.usage_stats['estimated_output_tokens'] += output_chars // 4
            self.usage_stats['successful_requests'] += 1
            
            # Clean up Markdown formatting (stars) if requested
            text = text.replace('**', '').replace('__', '')
            
            # Remove emojis from response using Unicode categories
            # 'So' = Symbol, Other (includes emojis)
            # This preserves all language characters (including Marathi) while removing emojis
            import unicodedata
            text = ''.join(c for c in text if unicodedata.category(c)[0:2] != 'So')
            
            return text
            
        except Exception as e:
            print(f"ERROR: Gemini Generation Error: {str(e)}")
            self.usage_stats['failed_requests'] += 1
            return f"Error generating response: {str(e)}"
    
    def get_usage_stats(self) -> dict:
        """Get current usage statistics"""
        from datetime import datetime
        stats = self.usage_stats.copy()
        stats['model'] = self.model_name
        stats['is_available'] = self.available
        stats['current_time'] = datetime.now().isoformat()
        return stats
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        from datetime import datetime
        self.usage_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_input_chars': 0,
            'total_output_chars': 0,
            'estimated_input_tokens': 0,
            'estimated_output_tokens': 0,
            'session_start': datetime.now().isoformat()
        }

    def multilingual_answer(self, query: str, context: str) -> str:
        """
        Generate a multilingual answer based on context
        
        Args:
            query: User question
            context: Retrieved document context
            
        Returns:
            Answer string
        """
        system_prompt = """You are analyzing multiple real estate documents together. Based on the user's question, you can:

1. CHECK COMPLIANCE: If asked about compliance, check if user documents comply with MahaRERA regulations, circulars, orders, or SOPs. Identify any violations, missing clauses, or non-compliant terms.

2. COMPARE DOCUMENTS: If asked to compare, analyze differences and similarities between documents.

3. ANSWER QUESTIONS: Provide comprehensive answers using information from all selected documents.

4. Do every thing user asks but in just provided context.

Always:
- Use simple, easy-to-understand English. Avoid complex legal jargon or difficult words.
- Write short sentences. Keep explanations clear and direct.
- Be specific and reference which document each point comes from
- For compliance checks, clearly state what is compliant and what is not
- Cite specific clauses, sections, or requirements
- Provide actionable recommendations if non-compliance is found

Answer in PLAIN TEXT without markdown formatting.
        """
        
        prompt = f"""Context:
        {context}
        
        Question: {query}
        
        Answer:"""
        
        return self.generate(prompt, system_prompt)
