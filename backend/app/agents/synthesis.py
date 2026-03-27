from app.services.llm import llm_router
from typing import List, Dict

class SynthesisAgent:
    """
    Takes all disparate signals and structures them into a coherent daily intelligence report.
    """
    
    def generate_daily_report(self, country: str, signals: List[Dict]) -> str:
        prompt = f"Synthesize these intelligence signals for {country} into a unified Executive Brief. Signals: {signals}"
        system = "You are an Elite Intelligence Synthesis Operative. Use markdown, formal tone, extreme precision."
        
        return llm_router.generate(prompt=prompt, system_prompt=system, model="anthropic/claude-3-opus")

synthesis_agent = SynthesisAgent()
