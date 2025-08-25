# OPTIM Finance Chatbot

An intelligent document-based chatbot system developed for OPTIM Finance, a startup that provides financial services to freelancers and small businesses. This project implements a RAG (Retrieval-Augmented Generation) architecture to answer client questions using company documents and knowledge base.

## About the Project

This chatbot was developed during an internship at OPTIM Finance to improve client support and information accessibility. The system allows the company to upload their internal documents, policies, and FAQs, then provides intelligent responses to client inquiries based on this knowledge base.

### Key Features

- **Document Management**: Upload and process various document formats (PDF, Word, TXT, etc.)
- **Smart Search**: Combines semantic search with traditional keyword matching
- **AI-Powered Responses**: Uses Mistral AI to generate natural, contextual answers
- **Web Integration**: Embeddable chat widget for the company website
- **Admin Interface**: Easy-to-use panel for content management
- **Vector Database**: ChromaDB for efficient document storage and retrieval

### Technology Stack

- **Backend**: FastAPI (Python)
- **AI/ML**: Mistral AI API, Sentence Transformers
- **Database**: ChromaDB (Vector Database)
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Deployment**: Docker, Docker Compose

## How It Works

1. **Document Upload**: Administrators upload company documents through a web interface
2. **Processing**: Documents are split into chunks and converted to vector embeddings
3. **Storage**: Embeddings are stored in ChromaDB for efficient similarity search
4. **User Query**: Clients ask questions through the chat widget
5. **Retrieval**: System finds the most relevant document chunks
6. **Generation**: Mistral AI generates answers based on retrieved context
7. **Response**: Natural language answer is returned to the client

## Installation and Setup

### Prerequisites

- Python 3.11 or higher
- Mistral AI API key ([Get one here](https://console.mistral.ai/))
- Git

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/optim-finance-chatbot
   cd optim-finance-chatbot
   ```

2. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```bash
   MISTRAL_API_KEY=your_mistral_api_key_here
   ```

3. **Start the application**
   ```bash
   docker-compose build 
   docker-compose up -d
   ```

4. **Access the services**
   - **Chat Widget**: http://localhost (Main interface)
   - **Admin Panel**: http://localhost:8001 (Document management)
   - **API Documentation**: http://localhost:8000/docs (FastAPI docs)

### Option 2: Local Development

1. **Clone and navigate**
   ```bash
   git clone https://github.com/yourusername/optim-finance-chatbot
   cd optim-finance-chatbot
   ```

2. **Backend setup**
   ```bash
   cd Implementation
   pip install -r requirements.txt
   export MISTRAL_API_KEY="your_mistral_api_key_here"
   python api/app.py
   ```
   The backend will run on http://localhost:8000

3. **Frontend setup** (in a new terminal)
   ```bash
   cd chat-widget
   npm install
   npm start
   ```
   The frontend will run on http://localhost:3000

## Usage Guide

### For Administrators

1. **Upload Documents**
   - Navigate to http://localhost:8001
   - Click "Upload Documents"
   - Select files (PDF, DOCX, TXT, JSON, CSV, MD)
   - Wait for processing to complete

2. **Manage Knowledge Base**
   - View all uploaded documents
   - Delete outdated or incorrect files
   - Monitor system status

### For End Users

1. **Ask Questions**
   - Open the chat widget on the website
   - Type your question in natural language
   - Receive AI-generated answers based on company documents

2. **Example Queries**
   - "What are your pricing plans?"
   - "How do I submit my invoices?"
   - "What documents do I need for onboarding?"


## Configuration

### Environment Variables

Create a `.env` file with these variables:

```bash
# Required
MISTRAL_API_KEY=your_mistral_api_key

# API Configuration (optional)
API_HOST=0.0.0.0
API_PORT=8000
ADMIN_API_PORT=8001

# Model Settings (optional)
LLM_MODEL=mistral-small
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
TOP_K_RESULTS=3

# File Upload Settings (optional)
MAX_FILE_SIZE=52428800  # 50MB
DEFAULT_CHUNK_SIZE=1000
DEFAULT_OVERLAP=100
```

### Supported File Formats

- **PDF**: `.pdf`
- **Microsoft Word**: `.docx`, `.doc`
- **Text files**: `.txt`, `.md`
- **Data files**: `.json`, `.csv`

## Project Structure

```
optim-finance-chatbot/
├── Implementation/              # Python backend
│   ├── api/
│   │   └── app.py              # Main FastAPI application
│   ├── admin/
├   │   ├──data/                # Data storage
│   │   ├   ├──chromadb/        # Vector database files
│   │   ├   ├──uploads/         # Uploaded documents
│   │   ├── admin_api.py        # Admin interface API
│   │   ├── chromadb_manager.py # Vector database management
│   │   └── file_processor.py   # Document processing logic
│   ├── src/
│   │   ├── chatbot.py          # Core chatbot functionality
│   │   ├── llm_integration.py  # Mistral AI integration
│   │   └── search.py           # Search and retrieval logic
│   ├── config.py               # Configuration management
│   └── requirements.txt        # Python dependencies
├── chat-widget/                # Frontend application
│   ├── front-end/
│   │   ├── index.html          # Main UI
│   │   ├── script.js           # Frontend logic
│   │   └── style.css           # Styling
│   └── package.json            # Node.js dependencies
├── docker/                     # Docker configuration
│   ├── Dockerfile.backend      # Backend container
│   └── Dockerfile.frontend     # Frontend container
├── docker-compose.yml          # Container orchestration
└── README.md                  # This file
```

## Development Notes

### Key Components

- **ChromaDB Manager**: Handles vector storage and similarity search
- **File Processor**: Extracts text and creates document chunks
- **LLM Integration**: Manages communication with Mistral AI API
- **Search Module**: Implements hybrid search functionality
- **Chat Widget**: Provides user interface for interactions

### Adding New Features

1. **New Document Types**: Extend `file_processor.py`
2. **Custom Search Logic**: Modify `search.py`
3. **UI Improvements**: Update files in `chat-widget/front-end/`
4. **API Endpoints**: Add routes in `api/app.py`

## Troubleshooting

### Common Issues

**ChromaDB Connection Error**
```bash
# Solution: Ensure data directory exists
mkdir -p Implementation/admin/data/chromadb
```

**Mistral API Authentication Failed**
```bash
# Solution: Check your API key
echo $MISTRAL_API_KEY
# Make sure it's valid and has sufficient credits
```

**File Upload Not Working**
- Check file size (max 50MB by default)
- Ensure file format is supported
- Verify upload directory permissions

**Docker Issues**
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs backend
docker-compose logs frontend

# Restart services
docker-compose restart
```

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
```

## Performance Considerations

- **Document Size**: Large documents are automatically chunked for optimal processing
- **Response Time**: First query may be slower due to model initialization
- **Memory Usage**: ChromaDB requires adequate RAM for large document collections
- **API Limits**: Mistral AI has rate limits; consider implementing request queuing for high traffic

## Security Notes

- Keep your Mistral API key secure and never commit it to version control
- In production, restrict CORS origins to your domain
- Consider implementing authentication for the admin interface
- Regularly update dependencies to patch security vulnerabilities

## About OPTIM Finance

OPTIM Finance is a financial technology startup that provides comprehensive financial services and tools specifically designed for freelancers, consultants, and small business owners. Their services help independent professionals manage their finances, track expenses, handle invoicing, and optimize their tax situations.

## License

This project was developed as part of an internship at OPTIM Finance. Please contact the company for licensing information.

## Contact

For questions about this implementation:
- **OPTIM Finance**: contact@optim-finance.com
- **Phone**: +33 1 59 06 80 86

---

*This project was developed during a software engineering internship at OPTIM Finance, focusing on implementing modern AI solutions for customer support automation.*