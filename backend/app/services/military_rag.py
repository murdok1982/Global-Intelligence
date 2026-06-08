from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, String, Text, func, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal


EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIMENSIONS = 768


class MilitaryDocument(Base):
    __tablename__ = "military_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSONB, default=dict)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


async def _get_embedding(text_input: str) -> list[float]:
    async with httpx.AsyncClient(timeout=float(settings.OLLAMA_TIMEOUT)) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text_input},
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]


async def create_military_vector_table(db: AsyncSession) -> None:
    await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await db.execute(
        text("""
        CREATE TABLE IF NOT EXISTS military_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            doc_type VARCHAR(50) NOT NULL,
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            metadata_json JSONB DEFAULT '{}',
            embedding vector(:dim),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """),
        {"dim": EMBEDDING_DIMENSIONS},
    )
    await db.execute(
        text("""
        CREATE INDEX IF NOT EXISTS idx_military_documents_embedding
        ON military_documents USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """)
    )
    await db.commit()


def _build_weapon_text(weapon: dict[str, Any]) -> str:
    parts: list[str] = [
        weapon.get("name", ""),
        weapon.get("designation", ""),
        weapon.get("category", ""),
        weapon.get("origin", ""),
        weapon.get("manufacturer", ""),
        weapon.get("description", ""),
    ]
    specs = weapon.get("technical_specs", {})
    if isinstance(specs, dict):
        for key, val in specs.items():
            parts.append(f"{key}: {val}")
    perf = weapon.get("performance_data", {})
    if isinstance(perf, dict):
        for key, val in perf.items():
            parts.append(f"{key}: {val}")
    return " | ".join(p for p in parts if p)


def _build_transfer_text(transfer: dict[str, Any]) -> str:
    parts: list[str] = [
        transfer.get("supplier_country", ""),
        transfer.get("recipient_country", ""),
        transfer.get("weapon_description", ""),
        transfer.get("weapon_category", ""),
        transfer.get("deal_type", ""),
        transfer.get("status", ""),
        transfer.get("notes", ""),
    ]
    if transfer.get("deal_value_usd"):
        parts.append(f"value: {transfer['deal_value_usd']} USD")
    if transfer.get("quantity"):
        parts.append(f"quantity: {transfer['quantity']}")
    if transfer.get("agreement_year"):
        parts.append(f"year: {transfer['agreement_year']}")
    return " | ".join(p for p in parts if p)


async def index_weapon_system(weapon: dict[str, Any]) -> None:
    embedding_text = _build_weapon_text(weapon)
    embedding = await _get_embedding(embedding_text)

    async with AsyncSessionLocal() as db:
        doc = MilitaryDocument(
            doc_type="weapon_system",
            title=weapon.get("name", "Unknown Weapon"),
            content=embedding_text,
            metadata_json={
                "weapon_id": weapon.get("id"),
                "category": weapon.get("category"),
                "origin": weapon.get("origin"),
                "manufacturer": weapon.get("manufacturer"),
                "designation": weapon.get("designation"),
            },
            embedding=embedding,
        )
        db.add(doc)
        await db.commit()


async def index_arms_transfer(transfer: dict[str, Any]) -> None:
    embedding_text = _build_transfer_text(transfer)
    embedding = await _get_embedding(embedding_text)

    async with AsyncSessionLocal() as db:
        doc = MilitaryDocument(
            doc_type="arms_transfer",
            title=f"{transfer.get('supplier_country', '?')} -> {transfer.get('recipient_country', '?')}: {transfer.get('weapon_description', '')}",
            content=embedding_text,
            metadata_json={
                "transfer_id": transfer.get("id"),
                "supplier_country": transfer.get("supplier_country"),
                "recipient_country": transfer.get("recipient_country"),
                "supplier_iso": transfer.get("supplier_iso"),
                "recipient_iso": transfer.get("recipient_iso"),
                "deal_value_usd": transfer.get("deal_value_usd"),
                "agreement_year": transfer.get("agreement_year"),
            },
            embedding=embedding,
        )
        db.add(doc)
        await db.commit()


async def index_intelligence_report(report: dict[str, Any]) -> None:
    content = report.get("content", "")
    embedding = await _get_embedding(content)

    async with AsyncSessionLocal() as db:
        doc = MilitaryDocument(
            doc_type="intelligence_report",
            title=report.get("title", "Untitled Report"),
            content=content,
            metadata_json={
                "report_id": report.get("id"),
                "country_iso": report.get("country_iso"),
                "classification": report.get("classification", "PUBLIC"),
                "source": report.get("source"),
            },
            embedding=embedding,
        )
        db.add(doc)
        await db.commit()


async def index_conflict_data(conflict: dict[str, Any]) -> None:
    parts: list[str] = [
        conflict.get("name", ""),
        conflict.get("description", ""),
        conflict.get("location", ""),
        conflict.get("parties", ""),
        conflict.get("outcome", ""),
    ]
    content = " | ".join(p for p in parts if p)
    embedding = await _get_embedding(content)

    async with AsyncSessionLocal() as db:
        doc = MilitaryDocument(
            doc_type="conflict_data",
            title=conflict.get("name", "Unknown Conflict"),
            content=content,
            metadata_json={
                "conflict_id": conflict.get("id"),
                "start_year": conflict.get("start_year"),
                "end_year": conflict.get("end_year"),
                "location": conflict.get("location"),
            },
            embedding=embedding,
        )
        db.add(doc)
        await db.commit()


async def search_similar(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    embedding = await _get_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
            SELECT id, doc_type, title, content, metadata_json,
                   1 - (embedding <=> :embedding_vec) AS similarity
            FROM military_documents
            ORDER BY embedding <=> :embedding_vec
            LIMIT :top_k
            """),
            {"embedding_vec": embedding_str, "top_k": top_k},
        )
        rows = result.fetchall()

    return [
        {
            "id": str(row[0]),
            "doc_type": row[1],
            "title": row[2],
            "content": row[3],
            "metadata": row[4],
            "similarity": float(row[5]) if row[5] is not None else 0.0,
        }
        for row in rows
    ]


async def generate_context(query: str) -> str:
    results = await search_similar(query, top_k=5)

    if not results:
        return "No relevant military intelligence documents found for this query."

    context_parts: list[str] = [
        f"Retrieved {len(results)} relevant document(s) for context:\n"
    ]

    for i, doc in enumerate(results, 1):
        header = f"[{i}] {doc['title']} (type: {doc['doc_type']}, similarity: {doc['similarity']:.3f})"
        context_parts.append(header)
        context_parts.append(doc["content"])
        if doc.get("metadata"):
            context_parts.append(f"Metadata: {json.dumps(doc['metadata'], default=str)}")
        context_parts.append("")

    return "\n".join(context_parts)
