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
            api_key=settings.tavily_api_key,
            num_results=5,
            topic="general",
            include_answers=True,
            include_raw_content=True,
        )
    return _web_search

def route_question(state:AgentState):
    
    router_llm = llm().with_structured_output(RouteDecision)

    question = state["question"]

    decision = router_llm.invoke(f'''
You are a router for an Agentic RAG assistant.

Route to "kb" if the user asks about:
- Agentic RAG
- LangGraph Agentic RAG workflow
- retrieval grading
- query rewriting
- RAG architecture
- retriever tools
- web fallback in RAG

Route to "direct" only for greetings, thanks, or very simple conversation.

Question: {question}
''')

    print("[ROUTER]")

    return {
        "current_query":question,
        "source_used":decision.route
    }


def route_after_routing(state:AgentState) -> Literal["retrieve_kb","direct_answer"]:
    if state["source_used"] == "kb":
        return "retrieve_kb"
    return "direct_answer"

def retrieve_kb(state:AgentState):

    query = state["current_query"]
    docs = get_retriever().invoke(query)
    print("[KB DOCS]")
    return {"kb_docs":docs}



def grade_kb_evidence(state:AgentState):
    
    kb_grader_llm = llm().with_structured_output(EvidenceGrade)

    question = state["question"]
    context = ""

    for doc in state["kb_docs"]:
        context += f"Source:{doc.metadata.get('source')}\nContent:{doc.page_content} " + "\n\n"

    grade = kb_grader_llm.invoke(f'''
You are an evidence grader.

Question:
{question}

Private KB evidence:
{context}

Can this private KB evidence answer the question?
Return "good" if it can answer.
Return "weak" if it cannot answer or is incomplete.

''')

    print("[KB EVIDENCE ROUTER]")

    return {
        "kb_grade":grade.grade
    }


def decide_after_kb_grade(state:AgentState) -> Literal["generate_from_kb","search_web"]:
    if state["kb_grade"] == "good":
        return "generate_from_kb"
    return "search_web"

def search_web(state: AgentState):

    query = state["current_query"]

    result = web_search_tool().invoke({"query":query})

    web_results = []

    for item in result.get("results", []):
        web_results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", "")
        })

    return {
        "web_results":web_results,
        "source_used":"web"
    }



def grade_web_evidence(state:AgentState):

    web_grader_llm = llm().with_structured_output(EvidenceGrade)

    question = state["question"]
    web_results = state["web_results"]

    grade = web_grader_llm.invoke(f'''
You are an evidence grader.

Question:
{question}

Web Search evidence:
{web_results}

Can this Web evidence answer the question?
Return "good" if it can answer.
Return "weak" if it cannot answer or is incomplete.

''')

    print("[WEB EVIDENCE ROUTER]")

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
    question = state["question"]
    retry_count = state["retry_count"] + 1

    rewritten = llm().invoke(f"""
Rewrite the question for better retrieval and web search.

Rules:
- Preserve original intent.
- Make it specific and search-friendly.
- Do not answer.
- Return only the rewritten query.

Original question:
{question}
""").content.strip()

    print("[REWRITTEN QUERY]")

    return {
        "current_query":rewritten,
        "retry_count":retry_count
    }

def generate_from_kb(state:AgentState):
    question = state["question"]

    context = ""
    
    for doc in state["kb_docs"]:
        context += f"Source:{doc.metadata.get('source')}\nContent:{doc.page_content} " + "\n\n"

    answer = llm().invoke(f"""
You are a technical instructor.

Answer using ONLY the private KB context.

Rules:
- Beginner-friendly explanation.
- Do not invent unsupported details.
- Mention that the answer is based on the private KB.
- Include source type: Private KB.

Question:
{question}

Private KB context:
{context}
""").content.strip()

    return {
        "answer":answer,
        "source_used":"private_kb"
    }

def generate_from_web(state:AgentState):

    question = state["question"]
    web_context = state["web_results"]

    answer = llm().invoke(f"""
You are a technical instructor.

The private KB was insufficient, so web search was used.

Answer using ONLY the web search context.

Rules:
- Beginner-friendly explanation.
- Do not invent unsupported details.
- Mention that the answer is based on Tavily web search.
- Include source type: Web Search.
- If URLs are present in the context, include the most useful URLs.

Question:
{question}

Web search context:
{web_context}
""").content.strip()

    return {"answer":answer,"source_used":"web"}

def direct_answer(state:AgentState):

    question = state["question"]

    answer = llm().invoke(f"Respond Briefly and naturally.\n Message:{question}").content

    return {
        "answer":answer,
        "source_used":"direct"
    }

def answer_insufficient(state: AgentState):
    answer = (
        "I could not find enough reliable evidence in the private knowledge base "
        "or the web search results to answer this confidently. "
        "Please provide more specific documents or rephrase the question."
    )

    return {
        "answer": answer,
        "source_used": "insufficient_evidence",
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

agent = build_graph()

def ask(question:str):
    initial_state = {
        "question":question,
        "current_query":"",
        "kb_docs":[],
        "web_results":"",
        "kb_grade":"",
        "web_grade":"",
        "answer":"",
        "source_used":"",
        "retry_count":0,
        "citations":[]
    }

    final_state = agent.run(initial_state)
    return final_state