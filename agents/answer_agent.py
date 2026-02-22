import os
import re
from typing import Dict, Any, List, Tuple

from agents.base_agent import BaseAgent
from infrastructure.message_queue import MessageQueue
from agents.retrieval_agent import RetrievalAgent

# We assume standard Groq library is installed as per requirements.txt
try:
    from groq import AsyncGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

class AnswerAgent(BaseAgent):
    """
    The orchestrator for user queries. Takes a query, calls RetrievalAgent for context,
    and formats a strict prompt for the LLM to generate an answer without hallucinations.
    """
    def __init__(self, mq: MessageQueue, retrieval_agent: RetrievalAgent):
        super().__init__(mq, "AnswerAgent")
        self.retrieval_agent = retrieval_agent
        
        if HAS_GROQ:
            api_key = os.environ.get("GROQ_API_KEY", "mock_key")
            self.client = AsyncGroq(api_key=api_key)
        else:
            self.client = None

    def get_listen_topic(self) -> str:
        return None

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        formatted = []
        for i, chunk in enumerate(chunks):
            meta = chunk.get("metadata", {})
            text = meta.get("text", "")
            url = meta.get("url", "unknown_source")
            formatted.append(f"--- Source [{i+1}] ({url}) ---\n{text}\n")
        return "\n".join(formatted)

    def _extract_citations(self, response: str) -> List[str]:
        """Simple regex to extract URL citations if we asked LLM to append them in a specific format"""
        # Look for [http...]
        urls = re.findall(r'\[(https?://[^\]]+)\]', response)
        return list(set(urls))

    async def answer_query(self, query: str) -> Tuple[str, List[str]]:
        print(f"[AnswerAgent] Processing query: '{query}'")
        
        # 1. Retrieve Context
        context_chunks = await self.retrieval_agent.retrieve(query, top_k=5)
        
        if not context_chunks:
            return "I could not find sufficient information in the retrieved context to answer your question.", []

        # 2. Build Generation Prompt
        context_str = self._format_context(context_chunks)
        
        prompt = f"""
        You are a strictly factual AI search assistant.
        Answer the user's question USING ONLY the provided context.
        Cite your sources inline using [Source X] format.
        If you cannot fully answer the question from the context alone, state exactly what is missing.
        Do not hallucinate external information.
        
        Context:
        {context_str}
        
        Question: {query}
        """
        
        if self.client and os.environ.get("GROQ_API_KEY"):
            print("[AnswerAgent] Calling Groq LLM...")
            try:
                completion = await self.client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1024,
                )
                answer = completion.choices[0].message.content
                
                # Extract citation URLs based on the Source mappings
                urls = []
                for chunk in context_chunks:
                     url = chunk.get("metadata", {}).get("url")
                     if url and url not in urls:
                         urls.append(url)
                         
                return answer, urls
                
            except Exception as e:
                print(f"[AnswerAgent] LLM Generation failed: {e}")
                return f"[Error] LLM Generation failed: {e}", []
        else:
            # Mock Answer
            print("[AnswerAgent] API Key missing or Groq not installed. Returning Mock Answer.")
            mock_answer = f"Based on the retrieved context, this is a mock answer for '{query}'.\n\nContext excerpt: {context_chunks[0]['metadata']['text'][:100]}...\n\n[Source 1]"
            urls = [c.get("metadata", {}).get("url") for c in context_chunks if "url" in c.get("metadata", {})]
            return mock_answer, list(set(urls))

    async def process_message(self, message: Dict[str, Any]):
        pass
