from app.services.llm import llm_router

class ScenarioAgent:
    """
    Generates 'What-If' projections strictly bounded by the Report's reality vector.
    """
    
    def simulate_what_if(self, existing_report_markdown: str, user_variable: str) -> str:
        system = "You are a restricted Scenario Simulator. You may ONLY use the context of the provided report to guess outcomes. DO NOT hallucinate external world knowledge."
        prompt = f"REPORT CONTEXT:\n{existing_report_markdown}\n\nUSER VARIABLE:\n{user_variable}\n\nCalculate risk trajectory."
        
        return llm_router.generate(prompt, system, model="meta-llama/llama-3-70b-instruct")

class ContributorIntakeAgent:
    """
    Chatbot agent for processing voluntary public signals.
    """
    def process_intake(self, user_message: str, chat_history: list) -> str:
        system = "You are an Intake Operative. Maintain a professional, sterile, deeply psychological tone. Extract Country, Category, and Entities. Only ask for phone number if they opt to be verified."
        prompt = f"History: {chat_history}\nUser: {user_message}\nRespond:"
        
        return llm_router.generate(prompt, system, model="anthropic/claude-3-haiku")
