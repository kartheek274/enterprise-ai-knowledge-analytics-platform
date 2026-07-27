import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any
from src.common.errors.exceptions import ResourceNotFoundError, ValidationError

@dataclass
class Document:
    """
    Unified container representing a single raw document and its system metadata.
    """
    content: str
    filename: str
    filepath: Path
    sha256: str
    file_size: int
    created_at: float
    modified_at: float
    metadata: Dict[str, Any]


class DocumentLoader:
    """
    Service responsible for loading, parsing, and calculating file metrics.
    Supports txt, md, and pdf formats.
    """

    @staticmethod
    def calculate_sha256(filepath: Path) -> str:
        """
        Calculates SHA-256 hash of a file's content to act as a unique checksum.
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            raise ValidationError(
                message=f"Failed to calculate checksum for file: {filepath}",
                original_exception=e
            )

    @classmethod
    def load(cls, filepath: Path) -> Document:
        """
        Loads document contents and builds unified metadata tags.
        Supports .txt, .md, and .pdf formats.
        """
        if not filepath.exists():
            raise ResourceNotFoundError(
                message=f"Ingestion source file does not exist at: {filepath}"
            )
            
        suffix = filepath.suffix.lower()
        if suffix not in [".txt", ".md", ".pdf"]:
            raise ValidationError(
                message=f"Unsupported file format '{suffix}'. Supported types: .txt, .md, .pdf"
            )

        stat = filepath.stat()
        file_size = stat.st_size
        created_at = stat.st_ctime
        modified_at = stat.st_mtime
        sha256 = cls.calculate_sha256(filepath)
        filename = filepath.name

        content = ""
        if suffix in [".txt", ".md"]:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                raise ValidationError(
                    message=f"Failed to read text file content from {filepath}: {str(e)}",
                    original_exception=e
                )
        elif suffix == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(filepath)
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")
                content = "\n".join(text_parts)
            except ImportError as imp_err:
                raise ValidationError(
                    message="Missing PDF parsing dependency. Please install 'pypdf' package.",
                    original_exception=imp_err
                )
            except Exception as e:
                raise ValidationError(
                    message=f"Failed to extract text from PDF file at {filepath}: {str(e)}",
                    original_exception=e
                )

        # Standardized metadata block
        metadata = {
            "filename": filename,
            "filepath": str(filepath.resolve()),
            "sha256": sha256,
            "file_size": file_size,
            "created_at": created_at,
            "modified_at": modified_at
        }

        return Document(
            content=content,
            filename=filename,
            filepath=filepath,
            sha256=sha256,
            file_size=file_size,
            created_at=created_at,
            modified_at=modified_at,
            metadata=metadata
        )
