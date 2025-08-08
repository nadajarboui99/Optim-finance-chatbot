import os
import uuid
import json
import fitz  # PyMuPDF for PDF
import docx
from typing import List, Dict, Any, Optional
import re
from pathlib import Path
import csv

class FileProcessor:
    def __init__(self):
        self.supported_formats = {
            '.pdf': self._process_pdf,
            '.docx': self._process_docx,
            '.doc': self._process_docx,
            '.txt': self._process_txt,
            '.json': self._process_json,
            '.csv': self._process_csv,
            '.md': self._process_markdown
        }
    
    def is_supported_format(self, filename: str) -> bool:
        """Check if file format is supported"""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_formats
    
    def process_file(self, file_path: str, filename: str, category: str = "general", 
                    intent: str = "general", chunk_size: int = 1000, 
                    overlap: int = 100) -> List[Dict[str, Any]]:
        """Process a file and return chunks"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = Path(filename).suffix.lower()
        if ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {ext}")
        
        # Extract text from file
        text_content = self.supported_formats[ext](file_path)
        
        if not text_content.strip():
            raise ValueError("No text content extracted from file")
        
        # Create chunks
        chunks = self._create_chunks(
            text_content, filename, category, intent, 
            chunk_size, overlap, ext
        )
        
        return chunks
    
    def _process_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return self._clean_text(text)
        except Exception as e:
            raise Exception(f"Error processing PDF: {e}")
    
    def _process_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return self._clean_text(text)
        except Exception as e:
            raise Exception(f"Error processing DOCX: {e}")
    
    def _process_txt(self, file_path: str) -> str:
        """Process text file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            return self._clean_text(text)
        except Exception as e:
            raise Exception(f"Error processing TXT: {e}")
    
    def _process_json(self, file_path: str) -> str:
        """Process JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert JSON to readable text
            if isinstance(data, dict):
                text = self._json_to_text(data)
            elif isinstance(data, list):
                text = "\n".join([self._json_to_text(item) if isinstance(item, dict) else str(item) for item in data])
            else:
                text = str(data)
            
            return self._clean_text(text)
        except Exception as e:
            raise Exception(f"Error processing JSON: {e}")
    
    def _process_csv(self, file_path: str) -> str:
        """Process CSV file"""
        try:
            text_rows = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                csv_reader = csv.DictReader(f)
                headers = csv_reader.fieldnames
                
                # Add headers as context
                text_rows.append("Colonnes: " + ", ".join(headers))
                
                # Process rows (limit to avoid huge files)
                for i, row in enumerate(csv_reader):
                    if i >= 1000:  # Limit to 1000 rows
                        break
                    row_text = " | ".join([f"{k}: {v}" for k, v in row.items() if v])
                    text_rows.append(row_text)
            
            return self._clean_text("\n".join(text_rows))
        except Exception as e:
            raise Exception(f"Error processing CSV: {e}")
    
    def _process_markdown(self, file_path: str) -> str:
        """Process Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            # Remove markdown formatting for cleaner text
            text = re.sub(r'#{1,6}\s+', '', text)  # Remove headers
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
            text = re.sub(r'\*(.*?)\*', r'\1', text)  # Remove italic
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Remove links
            text = re.sub(r'`([^`]+)`', r'\1', text)  # Remove inline code
            text = re.sub(r'```[\s\S]*?```', '', text)  # Remove code blocks
            
            return self._clean_text(text)
        except Exception as e:
            raise Exception(f"Error processing Markdown: {e}")
    
    def _json_to_text(self, obj: Dict[str, Any], prefix: str = "") -> str:
        """Convert JSON object to readable text"""
        text_parts = []
        for key, value in obj.items():
            if isinstance(value, dict):
                text_parts.append(f"{prefix}{key}:")
                text_parts.append(self._json_to_text(value, prefix + "  "))
            elif isinstance(value, list):
                text_parts.append(f"{prefix}{key}: {', '.join([str(v) for v in value])}")
            else:
                text_parts.append(f"{prefix}{key}: {value}")
        return "\n".join(text_parts)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.,!?;:()\-€$%]', '', text)
        return text.strip()
    
    def _create_chunks(self, text: str, filename: str, category: str, 
                      intent: str, chunk_size: int, overlap: int, 
                      file_type: str) -> List[Dict[str, Any]]:
        """Create overlapping chunks from text"""
        
        # Split into sentences for better chunking
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk + " " + sentence) > chunk_size and current_chunk:
                # Create chunk
                chunk = self._create_chunk_dict(
                    current_chunk.strip(), filename, category, 
                    intent, chunk_index, file_type
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
                chunk_index += 1
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunk = self._create_chunk_dict(
                current_chunk.strip(), filename, category, 
                intent, chunk_index, file_type
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk_dict(self, content: str, filename: str, category: str, 
                          intent: str, chunk_index: int, file_type: str) -> Dict[str, Any]:
        """Create a chunk dictionary"""
        
        # Generate keywords from content
        keywords = self._extract_keywords(content)
        
        # Create title based on content
        title = self._generate_title(content, filename, chunk_index)
        
        return {
            'id': str(uuid.uuid4()),
            'content': content,
            'title': title,
            'keywords': keywords,
            'category': category,
            'intent': intent,
            'filename': filename,
            'file_type': file_type.replace('.', ''),
            'chunk_index': chunk_index,
            'length': len(content)
        }
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction (can be improved with NLP libraries)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove common stop words (French and English)
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais', 'dans',
            'sur', 'avec', 'par', 'pour', 'que', 'qui', 'ce', 'cette', 'ces', 'est', 'sont'
        }
        
        keywords = [word for word in set(words) if word not in stop_words and len(word) > 3]
        
        # Count frequency and take most common
        word_freq = {}
        for word in words:
            if word in keywords:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [kw[0] for kw in sorted_keywords[:max_keywords]]
    
    def _generate_title(self, content: str, filename: str, chunk_index: int) -> str:
        """Generate a title for the chunk"""
        # Take first sentence or first 100 characters
        first_sentence = content.split('.')[0].strip()
        if len(first_sentence) > 100:
            title = first_sentence[:97] + "..."
        else:
            title = first_sentence
        
        if not title:
            title = f"{filename} - Partie {chunk_index + 1}"
        
        return title