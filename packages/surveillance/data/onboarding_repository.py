import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..application.auth import AuthSession
from ..domain.models import Detection, IncidentContext, RetrievedEvidence
from ..domain.onboarding import KnowledgeDocument, Organization
from ..knowledge.embeddings import LocalHashEmbedding
from .models import (
    CameraRow,
    KnowledgeChunkRow,
    KnowledgeDocumentRow,
    OrganizationRow,
    SessionRow,
    UserRow,
)


class OnboardingRepository:
    def __init__(self, sessions: sessionmaker[Session], session_ttl_hours: int = 12) -> None:
        self.sessions = sessions
        self.embeddings = LocalHashEmbedding()
        self.session_ttl = timedelta(hours=session_ttl_hours)

    def create_account(self, organization: Organization, email: str, password_hash: str) -> AuthSession:
        token = secrets.token_urlsafe(32)
        created_at = datetime.now(UTC)
        expires_at = created_at + self.session_ttl
        with self.sessions.begin() as session:
            session.add(OrganizationRow(**organization.__dict__))
            user = UserRow(user_id=secrets.token_hex(18), organization_id=organization.organization_id, email=email.lower(), password_hash=password_hash)
            session.add(user)
            session.add(SessionRow(token_hash=self._token_hash(token), user_id=user.user_id, organization_id=organization.organization_id, created_at=created_at, expires_at=expires_at))
        return AuthSession(token, user.user_id, organization.organization_id, expires_at)

    def find_user(self, email: str) -> UserRow | None:
        with self.sessions() as session:
            return session.scalar(select(UserRow).where(UserRow.email == email.lower()))

    def create_session(self, user: UserRow) -> AuthSession:
        token = secrets.token_urlsafe(32)
        created_at = datetime.now(UTC)
        expires_at = created_at + self.session_ttl
        with self.sessions.begin() as session:
            session.add(SessionRow(token_hash=self._token_hash(token), user_id=user.user_id, organization_id=user.organization_id, created_at=created_at, expires_at=expires_at))
        return AuthSession(token, user.user_id, user.organization_id, expires_at)

    def session_for_token(self, token: str) -> AuthSession | None:
        with self.sessions() as session:
            row = session.get(SessionRow, self._token_hash(token))
            if row is None:
                return None
            expires_at = row.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= datetime.now(UTC):
                session.delete(row)
                session.commit()
                return None
            return AuthSession(token, row.user_id, row.organization_id, expires_at)

    def revoke_session(self, token: str) -> None:
        with self.sessions.begin() as session:
            row = session.get(SessionRow, self._token_hash(token))
            if row is not None:
                session.delete(row)

    def configure(self, organization_id: str, camera_id: str, camera_name: str, location: str, emergency_contact: str, preference: str, key_fingerprint: str, key_last_four: str) -> None:
        with self.sessions.begin() as session:
            organization = session.get(OrganizationRow, organization_id)
            if organization is None:
                raise LookupError("Organization not found")
            organization.emergency_contact = emergency_contact
            organization.notification_preference = preference
            organization.api_key_fingerprint = key_fingerprint
            organization.api_key_last_four = key_last_four
            session.add(CameraRow(camera_id=camera_id, organization_id=organization_id, name=camera_name, location=location))

    def save_document(self, document: KnowledgeDocument, chunks: list[str]) -> None:
        with self.sessions.begin() as session:
            session.add(KnowledgeDocumentRow(**document.__dict__))
            session.add_all(
                KnowledgeChunkRow(
                    document_id=document.document_id,
                    organization_id=document.organization_id,
                    position=index,
                    content=content,
                    embedding=self.embeddings.embed(content),
                )
                for index, content in enumerate(chunks)
            )

    def retrieve(self, detection: Detection) -> IncidentContext:
        if not detection.organization_id:
            return IncidentContext(("Default verified-accident response policy",), ("demo-emergency-dispatch",), ("Confirm location",), 0, ("Prefer voice alerts",))
        query = (
            f"road accident severity matrix critical high emergency response {detection.location} "
            f"confidence {detection.confidence:.2f} impact score {detection.impact_score:.2f} "
            f"vehicle count {detection.vehicle_count} stopped vehicle {detection.stopped_vehicle}"
        )
        query_embedding = self.embeddings.embed(query)
        with self.sessions() as session:
            organization = session.get(OrganizationRow, detection.organization_id)
            chunks = list(session.scalars(select(KnowledgeChunkRow).where(KnowledgeChunkRow.organization_id == detection.organization_id)))
            documents = {
                item.document_id: item
                for item in session.scalars(
                    select(KnowledgeDocumentRow).where(
                        KnowledgeDocumentRow.organization_id == detection.organization_id
                    )
                )
            }
        scored = sorted(
            (
                (self.embeddings.similarity(query_embedding, chunk.embedding or []), chunk)
                for chunk in chunks
            ),
            key=lambda item: item[0],
            reverse=True,
        )[:5]
        evidence = tuple(
            RetrievedEvidence(
                document_id=chunk.document_id,
                filename=documents[chunk.document_id].filename,
                chunk_position=chunk.position,
                score=round(score, 4),
                excerpt=chunk.content,
            )
            for score, chunk in scored
        )
        policies = tuple(item.excerpt for item in evidence) or ("Default verified-accident response policy",)
        contacts = (organization.emergency_contact,) if organization and organization.emergency_contact else ()
        preferences = (organization.notification_preference,) if organization else ()
        return IncidentContext(policies, contacts, policies[:1], 0, preferences, evidence)

    def summary(self, organization_id: str) -> dict[str, object]:
        with self.sessions() as session:
            organization = session.get(OrganizationRow, organization_id)
            cameras = list(session.scalars(select(CameraRow).where(CameraRow.organization_id == organization_id)))
            documents = list(session.scalars(select(KnowledgeDocumentRow).where(KnowledgeDocumentRow.organization_id == organization_id)))
        if organization is None:
            raise LookupError("Organization not found")
        return {
            "organization": {
                "organization_id": organization.organization_id,
                "name": organization.name,
                "emergency_contact": organization.emergency_contact,
                "notification_preference": organization.notification_preference,
                "api_key_last_four": organization.api_key_last_four,
            },
            "cameras": [{"camera_id": item.camera_id, "name": item.name, "location": item.location} for item in cameras],
            "documents": [{"document_id": item.document_id, "filename": item.filename, "page_count": item.page_count, "chunk_count": item.chunk_count} for item in documents],
            "onboarding_complete": bool(cameras and documents and organization.api_key_fingerprint),
        }

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
