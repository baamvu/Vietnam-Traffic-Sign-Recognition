## 4. Tech Stack

### 4.1. Demo hiện tại

| Component | Lựa chọn | RAM |
|---|---|---|
| Backend | Python 3.11 + FastAPI | ~150MB |
| LLM | gpt-4o-mini qua TokenRouter API | 0MB (API) |
| Embedding | paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers, local) | ~500MB |
| Vector DB | Qdrant (Docker) | ~200MB |
| Structured DB | PostgreSQL 16 (Docker) | ~100MB |
| Hybrid search | Dense + BM25 sparse → Qdrant RRF fusion | — |
| Reranker | FlashRank MultiBERT-L-12 (ONNX, local) | ~500MB |
| Web UI | FastAPI serve HTML/JS | — |
| Admin Portal | FastAPI serve HTML/JS | — |

---

### 4.2. System Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["Browser<br/>Chat UI"]
        AdminUI["Browser<br/>Admin Portal"]
    end

    subgraph FastAPI["FastAPI Application (port 8000)"]
        direction TB
        ChatAPI["POST /api/chat<br/>POST /api/chat/stream"]
        HealthAPI["GET /api/health"]
        AdminAPI["Admin API<br/>/admin/upload, /admin/reindex<br/>/admin/structured/*"]
        StaticFiles["Static Files<br/>index.html, admin.html"]

        subgraph Pipeline["RAG Pipeline"]
            direction TB
            GuardPre["GuardrailPipeline<br/>Pre-retrieval"]
            Classifier["QueryClassifier<br/>Intent: price/specs/<br/>comparison/unstructured"]
            AdaptiveRet["AdaptiveRetriever"]
            HybridRet["HybridRetriever<br/>Dense + BM25 → RRF"]
            Reranker["FlashRank Reranker<br/>MultiBERT-L-12"]
            GuardPost["GuardrailPipeline<br/>Post-retrieval"]
            PromptBuilder["PromptBuilder"]
            LLMGen["LLMGenerator<br/>gpt-4o-mini"]
        end

        subgraph Services["Core Services"]
            Embedding["LocalEmbedding<br/>MiniLM-L12-v2<br/>(singleton, 384-dim)"]
            BM25["BM25Index<br/>Sparse Vectors"]
            ConvStore["InMemoryConversation<br/>Store (TTL 30min)"]
            SparseUtil["SparseVector<br/>Encoder"]
        end
    end

    subgraph DataPipeline["Data Pipeline"]
        direction LR
        Fetcher["Web Fetcher<br/>BeautifulSoup"]
        Ingestion["Ingestion<br/>Structured/Unstructured<br/>Split"]
        Chunking["Chunking<br/>Specs/FAQ/Price/Guide"]
        Indexer["Indexer<br/>Full + Incremental"]
        ReindexSched["ReindexScheduler<br/>Debounce 15s"]
    end

    subgraph Storage["Data Stores"]
        direction TB
        Qdrant[("Qdrant<br/>vinfast_docs<br/>Dense + Sparse vectors<br/>~56 unstructured chunks")]
        PostgreSQL[("PostgreSQL<br/>vinfast_rag<br/>prices, specs tables")]
        FileStore[("File System<br/>data/raw/*.json<br/>data/processed/chunks.json<br/>data/processed/bm25_index.json")]
    end

    subgraph External["External Services"]
        TokenRouter["TokenRouter API<br/>gpt-4o-mini"]
    end

    Browser --> ChatAPI
    AdminUI --> AdminAPI

    ChatAPI --> GuardPre
    GuardPre -->|passed| Classifier
    Classifier -->|structured| AdaptiveRet
    Classifier -->|unstructured| AdaptiveRet
    AdaptiveRet -->|price/specs/comparison| PostgreSQL
    AdaptiveRet -->|unstructured| HybridRet
    HybridRet --> Embedding
    HybridRet --> BM25
    HybridRet --> Qdrant
    HybridRet --> Reranker
    AdaptiveRet --> GuardPost
    GuardPost --> PromptBuilder
    PromptBuilder --> LLMGen
    LLMGen --> TokenRouter
    ChatAPI --> ConvStore

    AdminAPI --> FileStore
    AdminAPI --> PostgreSQL
    AdminAPI --> ReindexSched
    ReindexSched --> Indexer
    Fetcher --> FileStore
    FileStore --> Ingestion
    Ingestion --> Chunking
    Chunking --> Indexer
    Indexer --> Embedding
    Indexer --> BM25
    Indexer --> Qdrant

    style Client fill:#e1f5fe,stroke:#0288d1
    style FastAPI fill:#fff3e0,stroke:#f57c00
    style Storage fill:#e8f5e9,stroke:#388e3c
    style External fill:#fce4ec,stroke:#c62828
    style DataPipeline fill:#f3e5f5,stroke:#7b1fa2
```

### 4.3. Request Flow (Chat)

```mermaid
flowchart TD
    A["User: POST /api/chat"] --> B["Pre-retrieval Guardrails"]
    B -->|blocked| B1["Return rejection message<br/>needs_human=true"]
    B -->|passed| C["QueryClassifier.classify()"]
    C --> D{Intent?}

    D -->|price / specs / comparison| E["StructuredLookup<br/>→ PostgreSQL"]
    E --> E1{PG has data?}
    E1 -->|yes| F["Format structured data<br/>as context"]
    E1 -->|no| G["Fallback → Qdrant search"]

    D -->|unstructured / inventory| G["HybridRetriever.hybrid_search()"]
    G --> G1["embed_query → dense vector"]
    G --> G2["BM25.encode → sparse vector"]
    G --> G3["Detect VF model filter<br/>from query text"]
    G1 & G2 & G3 --> G4["Qdrant query_points<br/>Dense + Sparse → RRF"]
    G4 --> G5["FlashRank Reranker<br/>top-20 → top-5"]
    G5 --> H["Post-retrieval Guardrails<br/>Confidence check (threshold=0.3)"]

    H -->|low confidence| H1["Return fallback message<br/>needs_human=true"]
    H -->|passed| I["PromptBuilder.build_prompt()"]
    F --> I

    I --> I1["System prompt (Vietnamese)<br/>+ Context chunks / Structured data<br/>+ Conversation history (3 turns)<br/>+ User question"]
    I1 --> J["LLMGenerator<br/>→ TokenRouter API<br/>→ gpt-4o-mini"]
    J --> K["Return ChatResponse<br/>+ Store in conversation"]

    style A fill:#bbdefb
    style B1 fill:#ffcdd2
    style H1 fill:#ffcdd2
    style K fill:#c8e6c9
```

### 4.4. Data Pipeline & Indexing

```mermaid
flowchart LR
    subgraph Sources["Data Sources"]
        URLs["URLs (urls.txt)"]
        Upload["Admin Upload<br/>(JSON/TXT/PDF/DOCX/XLSX)"]
    end

    subgraph Ingest["Ingestion"]
        Fetch["Web Fetcher<br/>BeautifulSoup"]
        ReadFile["File Reader"]
    end

    subgraph Process["Processing"]
        Split["Structured /<br/>Unstructured Split"]
        Chunk["Chunking Strategies<br/>• SpecsChunker (1 chunk/doc)<br/>• FAQChunker (Q&A split)<br/>• PriceChunker (by version)<br/>• GuideChunker (sliding window)"]
        Hash["Content Hash<br/>SHA256 per chunk"]
    end

    subgraph Store["Storage"]
        direction TB
        PG[("PostgreSQL<br/>prices, specs")]
        QD[("Qdrant<br/>dense + sparse vectors")]
        BM["BM25 Index<br/>bm25_index.json"]
        PROC["chunks.json"]
    end

    subgraph Schedule["Scheduling"]
        Debounce["ReindexScheduler<br/>Debounce 15s"]
        Manual["Manual<br/>/admin/reindex"]
    end

    URLs --> Fetch
    Upload --> ReadFile
    Fetch --> Split
    ReadFile --> Split
    Split -->|structured| PG
    Split -->|unstructured| Chunk
    Chunk --> Hash
    Hash -->|new/updated| QD
    Hash -->|new/updated| BM
    Hash --> PROC

    Debounce -->|incremental| Hash
    Manual -->|full or incremental| Hash

    style Sources fill:#e3f2fd
    style Process fill:#fff9c4
    style Store fill:#e8f5e9
    style Schedule fill:#f3e5f5
```

### 4.5. Deployment Architecture (Production)

```mermaid
graph TB
    subgraph Internet["Internet"]
        Users["Users"]
    end

    subgraph DockerCompose["Docker Compose"]
        Nginx["Nginx<br/>Load Balancer<br/>port 80"]

        subgraph AppInstances["FastAPI Replicas"]
            App1["App Instance 1<br/>uvicorn :8000"]
            App2["App Instance 2<br/>uvicorn :8000"]
            App3["App Instance 3<br/>uvicorn :8000"]
        end

        Qdrant[("Qdrant<br/>port 6333")]
        PG[("PostgreSQL 16<br/>port 5432")]
        PGAdmin["pgAdmin<br/>port 5050"]
    end

    Users --> Nginx
    Nginx --> App1 & App2 & App3
    App1 & App2 & App3 --> Qdrant
    App1 & App2 & App3 --> PG
    PGAdmin --> PG

    style Internet fill:#e1f5fe
    style DockerCompose fill:#fff3e0
    style AppInstances fill:#e8f5e9
```

### 4.6. Component Dependencies

```mermaid
graph LR
    subgraph Core["app/core/"]
        chunking["chunking.py<br/>4 strategies"]
        embedding["embedding.py<br/>LocalEmbedding<br/>(singleton)"]
        retrieval["retrieval.py<br/>HybridRetriever"]
        sparse["sparse.py<br/>BM25Index"]
        reranker["reranker.py<br/>FlashRank"]
        adaptive["adaptive_retrieval.py<br/>AdaptiveRetriever"]
        classifier["query_classifier.py<br/>QueryClassifier"]
        structured["structured_lookup.py<br/>StructuredLookup"]
        guardrails["guardrails.py<br/>3-stage pipeline"]
        prompt["prompt_builder.py"]
        generation["generation.py<br/>LLMGenerator"]
        conversation["conversation.py<br/>InMemoryStore"]
    end

    subgraph Data["app/data/"]
        fetcher["fetcher.py"]
        ingestion["ingestion.py"]
        indexer["indexer.py"]
        reindex["reindex_scheduler.py"]
    end

    subgraph DB["app/db/"]
        connection["connection.py<br/>SQLAlchemy"]
        models["models.py<br/>Price, Spec"]
    end

    adaptive --> classifier
    adaptive --> retrieval
    adaptive --> structured
    retrieval --> embedding
    retrieval --> sparse
    retrieval --> reranker
    structured --> connection
    connection --> models
    indexer --> embedding
    indexer --> sparse
    indexer --> chunking
    ingestion --> chunking
    reindex --> indexer
    fetcher --> ingestion