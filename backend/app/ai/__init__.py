"""
AI Layer for the Fraud Early-Warning System.

Exposes:
- explanation_engine.explain_risk(...)      -> human-readable "why is this customer risky"
- recommendation_engine.get_recommendations(...) -> ranked action list for credit officers
- assistant.ask_assistant(...)              -> free-form Q&A over a customer's risk profile
- gemini_client.GeminiClient                -> thin wrapper around Gemini API with offline fallback
"""
