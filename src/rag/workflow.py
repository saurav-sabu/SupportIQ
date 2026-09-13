from pathlib import Path
import logfire
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from typing import Literal
from langgraph.graph import StateGraph, START, END
from src.rag.state import AgentState, RouteDecision, EvidenceGrade
from src.rag.vectorstore import get_retriever
from src.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = None
_web_search = None

def llm():
    global _llm
    if _llm is None:
        if not settings.groq_model or not settings.groq_api_key:
            raise ValueError("Groq model and API key must be set in the environment variables.")
        _llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.0,
        )

    return _llm

def web_search_tool():
    global _web_search
    if _web_search is None:
        if not settings.tavily_api_key:
            raise ValueError("Tavily API key must be set in the environment variables.")
        _web_search = TavilySearch(
            tavily_api_key=settings.tavily_api_key,
            max_results=5,
            topic="general",
            include_answer=True,
            include_raw_content=True,
        )
    return _web_search

def route_question(state:AgentState):
    with logfire.span("rag.route_question", question=state["question"]) as span:
        router_llm = llm().with_structured_output(RouteDecision)

        question = state["question"]

        decision = router_llm.invoke(f"""
You are the primary IT Service Desk Triage & Routing Engine for SupportIQ.
Your role is to classify user inquiries into the appropriate resolution pathway.

Route to "kb" if the user inquiry is about:
- Technical troubleshooting (hardware, software, OS, network, peripherals, printers, displays, docking stations, BIOS).
- Enterprise networking (Wi-Fi, Ethernet, DNS, IP addressing, VPN connectivity, default gateway, proxy).
- Identity & Access Management (Active Directory, Azure AD / Entra ID, password resets, account lockouts, MFA, SSO, permissions).
- Microsoft 365 & SaaS tools (Outlook, Exchange, Teams, OneDrive sync, Office apps, SharePoint).
- Endpoint security & compliance (BitLocker recovery keys, antivirus, malware quarantine, security incident triage).
- IT Service Desk policies, SLA tiers, escalation runbooks, standard operating procedures, software requests.

Route to "direct" ONLY for:
- Conversational greetings or casual remarks (e.g., "hi", "hello", "good morning", "how are you").
- Politeness or thank you messages (e.g., "thanks", "thank you so much").
- Meta-questions about SupportIQ itself (e.g., "what can you do?", "who are you?").

Inquiry: {question}
""")

        print("[ROUTER]")
        span.set_attribute("route_decision", decision.route)

        return {
            "current_query":question,
            "source_used":decision.route
        }


def route_after_routing(state:AgentState) -> Literal["retrieve_kb","direct_answer"]:
    if state["source_used"] == "kb":
        return "retrieve_kb"
    return "direct_answer"

def retrieve_kb(state:AgentState):
    with logfire.span("rag.retrieve_kb", query=state["current_query"]) as span:
        query = state["current_query"]
        docs = get_retriever().invoke(query)
        span.set_attribute("docs_count", len(docs))
        print("[KB DOCS]")
        return {"kb_docs":docs}



def grade_kb_evidence(state:AgentState):
    with logfire.span("rag.grade_kb_evidence", question=state["question"]) as span:
        kb_grader_llm = llm().with_structured_output(EvidenceGrade)

        question = state["question"]
        context = ""

        for doc in state["kb_docs"]:
            context += f"Source:{doc.metadata.get('source')}\nContent:{doc.page_content} " + "\n\n"

        grade = kb_grader_llm.invoke(f"""
You are a Senior IT Quality Assurance Engineer grading retrieved knowledge base runbooks.
Your task is to evaluate whether the provided private enterprise runbooks contain sufficient, actionable technical evidence to solve the user's issue.

User Incident / Question:
{question}

Retrieved Private KB Runbook Context:
{context}

Evaluation Criteria:
- Return "good" if the context contains relevant technical guidance, diagnostic steps, configuration procedures, or runbook instructions that directly address or resolve the user's incident.
- Return "weak" if the context is missing, irrelevant, lacks actionable troubleshooting steps, or fails to cover the specific error code, application, or platform.

Determine evidence sufficiency:
""")

        print("[KB EVIDENCE ROUTER]")
        span.set_attribute("kb_grade", grade.grade)

        return {
            "kb_grade":grade.grade
        }


def decide_after_kb_grade(state:AgentState) -> Literal["generate_from_kb","search_web"]:
    if state["kb_grade"] == "good":
        return "generate_from_kb"
    return "search_web"

def search_web(state: AgentState):
    with logfire.span("rag.search_web", query=state["current_query"]) as span:
        query = state["current_query"]

        result = web_search_tool().invoke({"query":query})

        web_results = []

        for item in result.get("results", []):
            web_results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")
            })

        span.set_attribute("web_results_count", len(web_results))

        return {
            "web_results":web_results,
            "source_used":"web"
        }



def grade_web_evidence(state:AgentState):
    with logfire.span("rag.grade_web_evidence", question=state["question"]) as span:
        web_grader_llm = llm().with_structured_output(EvidenceGrade)

        question = state["question"]
        web_results = state["web_results"]

        grade = web_grader_llm.invoke(f"""
You are a Senior IT Systems Engineer validating external web search results for enterprise troubleshooting.

User Incident / Question:
{question}

Retrieved Web Evidence:
{web_results}

Evaluation Criteria:
- Return "good" if the search results provide credible, technically sound, and actionable troubleshooting steps or verified vendor workarounds (e.g., Microsoft KB, Cisco, official documentation, known bug fixes).
- Return "weak" if the search results are unhelpful, spammy, irrelevant, vague, or lack concrete technical resolution steps.

Determine evidence sufficiency:
""")

        print("[WEB EVIDENCE ROUTER]")
        span.set_attribute("web_grade", grade.grade)

        return {
            "web_grade":grade.grade
        }


def decide_after_web_grade(state:AgentState) -> Literal["generate_from_web","rewrite_query","answer_insufficient"]:
    if state["web_grade"] == "good":
        return "generate_from_web"

    if state["retry_count"] < settings.max_retries:
        return "rewrite_query"

    return "answer_insufficient"

def rewrite_query(state:AgentState):
    with logfire.span("rag.rewrite_query", question=state["question"], retry_count=state["retry_count"]) as span:
        question = state["question"]
        retry_count = state["retry_count"] + 1

        rewritten = llm().invoke(f"""
You are an Enterprise IT Search Optimization Specialist.
Your task is to rephrase the user's inquiry into a high-precision, search-optimized technical query for vector and web knowledge bases.

Rules:
- Identify and isolate key technical entities: operating system, vendor (e.g., Microsoft, Cisco, Dell), software (e.g., Outlook, GlobalProtect), error codes (e.g., 0x80070005, Error 800), and specific symptoms.
- Strip conversational filler ("please help", "my laptop is broken", "why does it do this").
- Use standard enterprise IT troubleshooting terminology (e.g., "DNS flush", "Credential Manager clear", "IKEv2 tunnel negotiation failure").
- Do NOT attempt to answer the question. Return ONLY the refined search string.

Original user inquiry:
{question}
""").content.strip()

        print("[REWRITTEN QUERY]")
        span.set_attribute("rewritten_query", rewritten)

        return {
            "current_query":rewritten,
            "retry_count":retry_count
        }

def generate_from_kb(state:AgentState):
    with logfire.span("rag.generate_from_kb", question=state["question"]) as span:
        question = state["question"]

        context = ""
        
        for doc in state["kb_docs"]:
            context += f"Source:{doc.metadata.get('source')}\nContent:{doc.page_content} " + "\n\n"

        answer = llm().invoke(f"""
You are SupportIQ, an expert Enterprise IT Tier-2 Support Specialist.
Provide an authoritative, clear, and grounded troubleshooting response based EXCLUSIVELY on the verified internal IT runbooks provided.

Response Guidelines:
1. **Summary / Cause**: Briefly explain the likely root cause according to internal policy.
2. **Step-by-Step Resolution**: Provide numbered, precise instructions with bold action items.
3. **Commands / Configurations**: Format all PowerShell, cmd, bash, file paths, and registry keys in clean code blocks with clear warnings.
4. **Safety & Prerequisites**: Mention any admin privileges or backup requirements.
5. **Verification**: State how the user can verify the fix succeeded.
6. **Escalation Note**: Advise on when to escalate to Tier-3 or submit a priority ticket if the steps do not resolve the issue.

Strict Constraints:
- Rely strictly on the provided runbook context; do not invent undocumented organizational policies or passwords.
- Maintain a professional, supportive, and reassuring enterprise tone.

User Incident:
{question}

Verified Internal Runbook Context:
{context}
""").content.strip()

        citations = []
        for doc in state.get("kb_docs", []):
            src_path = doc.metadata.get("source", "")
            file_name = Path(src_path).name if src_path else "Internal IT Runbook"
            page = doc.metadata.get("page", 1)
            snippet = doc.page_content[:260].strip() + ("..." if len(doc.page_content) > 260 else "")
            citations.append({
                "source": file_name,
                "page": page,
                "snippet": snippet
            })

        span.set_attribute("citations_count", len(citations))

        return {
            "answer": answer,
            "source_used": "private_kb",
            "citations": citations
        }

def generate_from_web(state:AgentState):
    with logfire.span("rag.generate_from_web", question=state["question"]) as span:
        question = state["question"]
        web_context = state["web_results"]

        answer = llm().invoke(f"""
You are SupportIQ, an expert Enterprise IT Tier-2 Support Specialist.
Internal runbooks did not contain sufficient documentation for this incident, so verified external technical documentation was retrieved via web search.

Response Guidelines:
1. **Notice**: Briefly inform the user that this guidance is compiled from external vendor/community technical documentation.
2. **Diagnosis & Potential Causes**: Explain what typically triggers this error or behavior.
3. **Structured Troubleshooting Plan**: Organize steps logically from easiest/least invasive to advanced.
4. **Command Snippets**: Provide exact CLI, PowerShell, or GUI navigation steps in code blocks.
5. **Safety Warning**: Highlight any risks (e.g., registry changes, service restarts, network disconnects).
6. **Sources & Documentation**: Mention the vendor or documentation references used.

Strict Constraints:
- Use only the provided web search context; do not fabricate unsupported details.
- Maintain an authoritative, professional enterprise IT support standard.

User Incident:
{question}

Retrieved Web Technical Context:
{web_context}
""").content.strip()

        citations = []
        for item in state.get("web_results", []):
            if isinstance(item, dict):
                citations.append({
                    "source": item.get("title") or "Web Source",
                    "url": item.get("url", ""),
                    "snippet": (item.get("content") or "")[:260].strip() + ("..." if len(item.get("content", "")) > 260 else "")
                })

        span.set_attribute("citations_count", len(citations))

        return {
            "answer": answer,
            "source_used": "web",
            "citations": citations
        }

def direct_answer(state:AgentState):
    with logfire.span("rag.direct_answer", question=state["question"]):
        question = state["question"]

        answer = llm().invoke(f"""
You are SupportIQ, an autonomous AI-powered Enterprise IT Support Agent.
Respond to the user in a professional, courteous, and helpful manner.

Guidelines:
- If this is a greeting, welcome the user to SupportIQ and briefly highlight the IT domains you can troubleshoot (e.g., Network & VPN, Active Directory & Identity, Microsoft 365, BitLocker, Hardware & Runbooks).
- If this is a polite thank you or farewell, respond warmly and offer continued assistance.
- Keep the response concise, polished, and enterprise-friendly.

User Message:
{question}
""").content.strip()

        return {
            "answer": answer,
            "source_used": "direct",
            "citations": []
        }

def answer_insufficient(state: AgentState):
    with logfire.span("rag.answer_insufficient", question=state["question"]):
        answer = (
            "### ⚠️ IT Service Desk Advisory: Insufficient Diagnostic Evidence\n\n"
            "SupportIQ could not locate sufficiently grounded evidence in internal enterprise runbooks "
            "or verified technical documentation to resolve this incident with high confidence.\n\n"
            "**Recommended Next Steps:**\n"
            "1. **Refine Details**: Provide additional context such as the exact error code, affected operating system, workstation asset tag, or recent system updates.\n"
            "2. **Escalate Ticket**: Please submit a ticket to the Tier-2 IT Service Desk or contact your system administrator with screenshot attachments of the error."
        )

        return {
            "answer": answer,
            "source_used": "insufficient_evidence",
            "citations": []
        }

def build_graph():

    graph = StateGraph(AgentState)
    graph.add_node("route_question",route_question)
    graph.add_node("retrieve_kb",retrieve_kb)
    graph.add_node("grade_kb_evidence",grade_kb_evidence)
    graph.add_node("search_web",search_web)
    graph.add_node("grade_web_evidence",grade_web_evidence)
    graph.add_node("rewrite_query",rewrite_query)
    graph.add_node("generate_from_kb",generate_from_kb)
    graph.add_node("generate_from_web",generate_from_web)
    graph.add_node("direct_answer",direct_answer)
    graph.add_node("answer_insufficient",answer_insufficient)

    graph.add_edge(START,"route_question")
    graph.add_conditional_edges("route_question",route_after_routing,{"retrieve_kb":"retrieve_kb","direct_answer":"direct_answer"})
    graph.add_edge("retrieve_kb","grade_kb_evidence")
    graph.add_conditional_edges("grade_kb_evidence",decide_after_kb_grade,{"generate_from_kb":"generate_from_kb","search_web":"search_web"})
    graph.add_edge("search_web","grade_web_evidence")
    graph.add_conditional_edges("grade_web_evidence",decide_after_web_grade,{"generate_from_web":"generate_from_web","rewrite_query":"rewrite_query","answer_insufficient":"answer_insufficient"})
    graph.add_edge("rewrite_query","retrieve_kb")
    graph.add_edge("generate_from_kb",END)
    graph.add_edge("generate_from_web",END)
    graph.add_edge("direct_answer",END)
    graph.add_edge("answer_insufficient",END)

    return graph.compile()

agent = build_graph()

def ask(question:str):
    with logfire.span("rag.ask_workflow", question=question) as span:
        initial_state = {
            "question": question,
            "current_query": question,
            "kb_docs": [],
            "web_results": "",
            "kb_grade": "",
            "web_grade": "",
            "answer": "",
            "source_used": "",
            "retry_count": 0,
            "citations": []
        }

        final_state = agent.invoke(initial_state)
        span.set_attribute("source_used", final_state.get("source_used"))
        return final_state