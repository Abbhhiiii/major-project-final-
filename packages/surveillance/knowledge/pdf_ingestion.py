import re
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from ..domain.onboarding import KnowledgeDocument


class PolicyPdfIngestor:
    def __init__(self, root: Path, chunk_words: int = 180) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.chunk_words = chunk_words

    def ingest(self, organization_id: str, filename: str, source) -> tuple[KnowledgeDocument, list[str]]:
        if not filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF policy documents are supported")
        document_id = str(uuid4())
        stored_name = f"{document_id}.pdf"
        path = self.root / stored_name
        with path.open("xb") as destination:
            while chunk := source.read(1024 * 1024):
                destination.write(chunk)
        try:
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            words = re.findall(r"\S+", text)
            chunks = [" ".join(words[index:index + self.chunk_words]) for index in range(0, len(words), self.chunk_words)]
            if not chunks:
                raise ValueError("The PDF contains no extractable text")
            document = KnowledgeDocument(
                organization_id=organization_id,
                filename=Path(filename).name,
                stored_name=stored_name,
                page_count=len(reader.pages),
                chunk_count=len(chunks),
                document_id=document_id,
            )
            return document, chunks
        except Exception:
            path.unlink(missing_ok=True)
            raise
