from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class DocumentChunk:
    """
    Represents a single chunk of text parsed from a larger source file,
    carrying lineage metadata.
    """
    content: str
    metadata: Dict[str, Any]


class RecursiveCharacterTextSplitter:
    """
    Recursively splits text into chunks of predefined sizes, keeping sentences
    and paragraphs intact by testing separators in order of semantic significance.
    """
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, separators: List[str] = None) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Delimiters listed by preference: paragraphs -> sentences -> words -> characters
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """
        Core recursive splitting logic that divides string content dynamically.
        """
        final_chunks: List[str] = []
        
        # Pick current separator and set remaining pool
        separator = separators[0] if separators else ""
        next_separators = separators[1:] if len(separators) > 1 else []
        
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)
            
        current_chunk = ""
        for part in splits:
            part_len = len(part)
            
            # If a single part exceeds the chunk size, split it recursively
            if part_len > self.chunk_size:
                if current_chunk:
                    final_chunks.append(current_chunk)
                    current_chunk = ""
                if next_separators:
                    recursed_parts = self._split_text(part, next_separators)
                    final_chunks.extend(recursed_parts)
                else:
                    final_chunks.append(part)
            else:
                # Check target size with separator and the new part
                if current_chunk:
                    potential_len = len(current_chunk) + len(separator) + part_len
                else:
                    potential_len = part_len
                    
                if potential_len <= self.chunk_size:
                    if current_chunk:
                        current_chunk += separator + part
                    else:
                        current_chunk = part
                else:
                    if current_chunk:
                        final_chunks.append(current_chunk)
                    
                    # Apply sliding overlap window from the end of the previous chunk
                    if self.chunk_overlap > 0 and current_chunk:
                        overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                        current_chunk = current_chunk[overlap_start:] + separator + part
                    else:
                        current_chunk = part
                        
        if current_chunk:
            final_chunks.append(current_chunk)
            
        return final_chunks

    def split_document(self, document_content: str, base_metadata: Dict[str, Any], document_id: int) -> List[DocumentChunk]:
        """
        Slices a document's content into multiple chunks, appending lineage metrics.
        """
        raw_chunks = self._split_text(document_content, self.separators)
        chunk_count = len(raw_chunks)
        document_chunks = []
        
        for index, chunk_text in enumerate(raw_chunks):
            # Construct distinct metadata copies for each chunk to preserve references
            chunk_metadata = base_metadata.copy()
            chunk_metadata.update({
                "document_id": document_id,
                "chunk_index": index,
                "chunk_count": chunk_count,
            })
            document_chunks.append(
                DocumentChunk(
                    content=chunk_text,
                    metadata=chunk_metadata
                )
            )
            
        return document_chunks
