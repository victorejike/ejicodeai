"""RAG router - Knowledge base indexing, document upload, and semantic search."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel

from agents.tools.tools import ChromaDBTool
from backend.app.security import get_current_active_user, User

router = APIRouter()
chroma_tool = ChromaDBTool()


class DocumentUploadRequest(BaseModel):
    collection: str = "company_research"
    text: str
    metadata: Optional[Dict[str, Any]] = None
    chunk: bool = True


class QueryRequest(BaseModel):
    collection: str = "ejicode_profile"
    query: str
    n_results: int = 3
    filter_metadata: Optional[Dict[str, Any]] = None


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def add_document(data: DocumentUploadRequest, current_user: User = Depends(get_current_active_user)):
    """Upload and vectorize a document into ChromaDB."""
    doc = {
        "text": data.text,
        "metadata": {**(data.metadata or {}), "uploaded_by": current_user.username},
    }
    added = await chroma_tool.add_documents(data.collection, [doc], chunk=data.chunk)
    return {"status": "indexed", "collection": data.collection, "chunks_indexed": added}


@router.post("/query")
async def query_knowledge_base(data: QueryRequest, current_user: User = Depends(get_current_active_user)):
    """Semantic vector search across knowledge base."""
    results = await chroma_tool.query(
        collection=data.collection,
        query_text=data.query,
        n_results=data.n_results,
        where=data.filter_metadata,
    )
    return {"collection": data.collection, "query": data.query, "results": results}


@router.post("/reindex")
async def reindex_all(current_user: User = Depends(get_current_active_user)):
    """Rebuild default company profile and case studies."""
    counts = await chroma_tool.reindex_knowledge_base()
    return {"status": "reindexed", "collections": counts}
