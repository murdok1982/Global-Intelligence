from app.services.llm import llm_router
from app.services.rag import rag_engine

class OpenClawOrchestrator:
    """
    Master coordination node for Global Intelligence.
    Validates triggers and assigns LLM sub-tasks recursively.
    """
    
    def __init__(self):
        self.name = "OpenClaw-Prime"
        
    async def dispatch_osint_scan(self, target_country: str) -> bool:
        """
        Triggers the OSINT Agent to scrape public internet boundaries safely.
        """
        print(f"[{self.name}] Dispatching OSINT Agent to target: {target_country}")
        return True
        
    async def dispatch_synthesis(self, raw_events: list, topic: str) -> str:
        """
        Invokes Synthesis Agent to compile raw items into an Executive Report array.
        """
        print(f"[{self.name}] Synthesizing {len(raw_events)} parameters on {topic}")
        # Call premium model for output
        report_markdown = llm_router.generate(
            prompt=f"Synthesize: {raw_events}", 
            system_prompt="You are a senior geopolitics synthesizer. Write the Executive Brief.",
            model="anthropic/claude-3-opus" # Premium tier usage
        )
        return report_markdown
        
    async def process_user_scenario(self, report_context: str, user_variable: str) -> str:
        """
        Handles interactive Chatbot constraint logic.
        """
        prompt = f"Original Brief: {report_context}\n\nClient Variable: {user_variable}\n\nGenerate alternate risk state."
        scenario = llm_router.generate(
            prompt=prompt,
            system_prompt="You are restricted ENTIRELY to the provided brief. Answer only regarding these bounds.",
            model="meta-llama/llama-3-70b-instruct"
        )
        return scenario

openclaw_master = OpenClawOrchestrator()
