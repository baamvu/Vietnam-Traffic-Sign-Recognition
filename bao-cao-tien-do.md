# BÁO CÁO TIẾN ĐỘ: VinFast RAG Chatbot
## Ngày: 21/07/2026

---

## 1. Tổng quan dự án

**Mục tiêu:** Xây dựng chatbot tư vấn xe VinFast sử dụng RAG (Retrieval-Augmented Generation), trả lời chính xác dựa trên tài liệu nội bộ, hỗ trợ hội thoại đa lượt, chịu được tải cao.

**Phạm vi:** Tư vấn thông số kỹ thuật, giá cả, chính sách bảo hành, so sánh các dòng xe VinFast (VF3, VF5, VF6, VF7, VF8, VF9).

---

## 2. Trạng thái hiện tại

### 2.1. Các giai đoạn đã hoàn thành

| Stage | Nội dung | Trạng thái |
|---|---|---|
| Stage 0 | Data Preparation (web fetcher, ingestion, chunking, golden QA) | ✅ Hoàn thành |
| Stage 1 | POC Pipeline (config, embedding, indexer, Qdrant, retrieval, prompt, generation, API, UI) | ✅ Hoàn thành |
| Stage 2 | Advanced Retrieval (query rewriting, metadata filtering, eval pipeline) | ✅ Hoàn thành |
| Stage 3 | Guardrails & Eval (content, injection, confidence guardrails, 64 unit tests) | ✅ Hoàn thành |
| Realtime Index | Incremental index + debounce scheduler + admin portal | ✅ Hoàn thành |
| Stage 5 | Adaptive RAG + PostgreSQL (structured lookup, query classifier) | ✅ Hoàn thành |

### 2.2. Các giai đoạn dự kiến

| Stage | Nội dung | Ưu tiên |
|---|---|---|
| Stage 6 | Traffic Scaling (Redis, Nginx, multi-worker, load testing) | Cao |
| Stage 4 | Context Management (token counting, sliding window, summarization) | Trung bình |

---

## 3. Kiến trúc hệ thống

### 3.1. Kiến trúc tổng quan (Adaptive RAG)

```
User Query
    │
    ▼
┌──────────────────────┐
│ Query Classifier     │  ← Phân loại intent (rule-based, tiếng Việt)
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌────────┐  ┌────────────┐
│Structur│  │Unstructured│
│ed Path │  │   Path     │
├────────┤  ├────────────┤
│Giá     │  │FAQ         │
│Specs   │  │Hướng dẫn   │
│So sánh │  │Chính sách  │
├────────┤  ├────────────┤
│PostgreS│  │Qdrant      │
│QL query│  │hybrid+rerank│
│(ONLY)  │  │(ONLY)      │
└───┬────┘  └─────┬──────┘
    │             │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │Context Merge│ → Prompt → LLM (gpt-4o-mini) → Response + Sources
    └─────────────┘

Data routing:
  Giá/Specs → PostgreSQL ONLY (không embed vào Qdrant)
  FAQ/Guide → Chunk → Embed → Qdrant ONLY (không vào PostgreSQL)
```

### 3.2. Pipeline retrieval chi tiết

```
Query → Preprocessing (Unicode NFC, model name normalize "vf 8" → "VF8")
      → Content Guardrail (chặn so sánh tiêu cực, tư vấn tài chính)
      → Injection Guardrail (chặn prompt injection)
      → Query Classifier:
          ├─ "giá/specs/so sánh" → PostgreSQL lookup (chính xác 100%)
          └─ "FAQ/hướng dẫn/chính sách" → Hybrid Search:
                ├─ Dense embedding (sentence-transformers, 384 dims)
                ├─ BM25 sparse (2298 terms vocabulary)
                └─ Qdrant RRF fusion → 20 candidates
      → Reranker (FlashRank MultiBERT-L-12, ONNX) → top 5
      → Confidence Guardrail (score ≥ 0.3?)
      → Prompt Builder (System + Context + History + Question)
      → LLM Generation (gpt-4o-mini via TokenRouter, streaming SSE)
      → Response + Sources (URL, content_type, updated_at)
```

### 3.3. Realtime Incremental Index

```
Data change (upload file / ERP webhook)
    │
    ▼
┌──────────────────────────┐
│ Debounce Scheduler (15s) │  ← Gom events, không chạy từng cái
│ In-memory buffer         │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Processing Lock          │  ← Không trigger lần nữa nếu đang index
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Incremental Index        │
│ - So sánh content hash   │
│ - Chỉ embed chunks mới   │
│ - Upsert vào Qdrant      │
│ - Rebuild BM25           │
└──────────────────────────┘
```

---

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
| **Total** | | **~1.45GB / 2.5GB** |

### 4.2. Production (mục tiêu)

| Component | Lựa chọn production | Lý do |
|---|---|---|
| LLM | GPT-5 (OpenAI API trực tiếp) | Chất lượng tiếng Việt tốt hơn |
| Embedding | BGE-M3 (self-host) hoặc OpenAI text-embedding-3 | Chất lượng cao hơn |
| Session store | Redis | Persist sessions, scale nhiều instances |
| Cache | Redis | Cache câu hỏi phổ biến |
| Load balancer | Nginx | Phân tải nhiều FastAPI instances |
| Deployment | Docker Compose → Kubernetes | Scale theo traffic |

---

## 5. Dữ liệu hiện tại

### 5.1. Nguồn data

| Nguồn | Số URLs | Fetch thành công | Content type |
|---|---|---|---|
| vinfastauto.com | 26 | 23 | specs, price, warranty, battery, FAQ, service |
| shop.vinfastauto.com | 3 | 2 | comparison, cost calculator |
| **Tổng** | **29** | **25** | |

### 5.2. Data đã index (sau khi tách routing)

| Storage | Số lượng | Nội dung |
|---|---|---|
| Qdrant (vector) | 56 chunks | FAQ (7) + Hướng dẫn/bảo hành/pin (49) — chỉ unstructured |
| PostgreSQL (structured) | 8 prices + 27 specs | Giá VF3/VF5/VF8/VF9 + Specs (seats, cargo, motor, battery, range) |
| BM25 index | 1932 terms | Vocabulary cho keyword search (chỉ unstructured) |
| Golden QA | 30 câu | Eval set (in-scope + out-of-scope) |

**Data routing:**
- Giá/Specs → PostgreSQL ONLY (không embed vào Qdrant). Update = UPDATE SQL (~0.001s)
- FAQ/Guide → Chunk → Embed → Qdrant ONLY (vector search + BM25)

### 5.3. Data gaps

| Thiếu | Lý do | Ảnh hưởng |
|---|---|---|
| VF3 specs | URL bị 403 (VinFast chặn bot) | Không trả lời được câu hỏi về VF3 |
| Giá pin, sửa chữa pin | URL bị 403 | Không có thông tin chi phí pin |
| Trạm sạc chi tiết | Thiếu data | Không chỉ được trạm sạc gần nhất |

---

## 6. Tính năng đã implement

### 6.1. Core RAG Pipeline

| Feature | Mô tả | File |
|---|---|---|
| Chunking | 2 strategies cho Qdrant: FAQChunker, GuideChunker. SpecsChunker/PriceChunker → PostgreSQL | `app/core/chunking.py` |
| Embedding | sentence-transformers local (384 dims, multilingual) | `app/core/embedding.py` |
| BM25 Sparse | Custom BM25 index (1932 terms) | `app/core/sparse.py` |
| Hybrid Search | Dense + sparse → Qdrant RRF fusion | `app/core/retrieval.py` |
| Reranker | FlashRank MultiBERT-L-12 (ONNX) | `app/core/reranker.py` |
| Query Rewriting | Pronoun resolution ("nó" → model xe) | `app/core/retrieval.py` |
| Prompt Builder | 4 parts: System + Context + History + Question | `app/core/prompt_builder.py` |
| LLM Generation | gpt-4o-mini, streaming SSE | `app/core/generation.py` |

### 6.2. Adaptive RAG (Stage 5)

| Feature | Mô tả | File |
|---|---|---|
| Query Classifier | Rule-based intent classification (tiếng Việt có dấu) | `app/core/query_classifier.py` |
| Structured Lookup | PostgreSQL query: prices, specs, comparison | `app/core/structured_lookup.py` |
| Adaptive Retriever | Router: structured → PostgreSQL, unstructured → Qdrant | `app/core/adaptive_retrieval.py` |
| Data routing | Giá/specs → PostgreSQL ONLY. FAQ/guide → Qdrant ONLY | `app/data/ingestion.py`, `app/data/indexer.py` |
| PostgreSQL | Tables: prices, specs. Docker container. | `app/db/` |

### 6.3. Guardrails (Stage 3)

| Guardrail | Loại | Vị trí |
|---|---|---|
| Content Guardrail | Regex: chặn so sánh tiêu cực, tư vấn tài chính | Pre-retrieval |
| Injection Guardrail | Regex: chặn prompt injection, query quá dài | Pre-retrieval |
| Confidence Guardrail | Score check: reject khi similarity < 0.3 | Post-retrieval |
| System Prompt | Ràng buộc LLM: chỉ trả lời dựa trên context | In-LLM |

### 6.4. Realtime Index

| Feature | Mô tả | File |
|---|---|---|
| Incremental Index | Chỉ re-embed chunks thay đổi (so sánh content hash) | `app/data/indexer.py` |
| Debounce Scheduler | 15s window, gom events, processing_lock | `app/data/reindex_scheduler.py` |
| Deterministic chunk_id | Stable key: source + content_type + model_xe + index | `app/core/chunking.py` |
| Admin Portal | Upload file, structured data, manual reindex, status | `app/api/admin.py`, `app/static/admin.html` |

### 6.5. UI

| UI | URL | Tính năng |
|---|---|---|
| Chat UI | http://localhost:8000/static/index.html | Chat streaming SSE, hiển thị sources |
| Admin Portal | http://localhost:8000/admin | Upload data, nhập giá/specs, reindex, status |
| Qdrant Dashboard | http://localhost:6333/dashboard | Browse vectors, search |
| pgAdmin | http://localhost:5050 | SQL dashboard (PostgreSQL) |
| API Docs | http://localhost:8000/docs | Swagger UI |

### 6.6. Testing

| Test | Số lượng | Trạng thái |
|---|---|---|
| Unit tests (chunking, guardrails, retrieval, API) | 64 | ✅ 64/64 pass |
| Realtime index test | 2 scenarios | ✅ Pass |
| Golden QA eval | 30 câu | ✅ Script sẵn sàng |

---

## 7. Cấu trúc thư mục

```
RAG Chatbot scale for Vinfast/
├── app/
│   ├── api/
│   │   ├── admin.py              # Admin Portal API (upload, reindex, structured data)
│   │   ├── chat.py               # Chat API (streaming SSE, adaptive retrieval)
│   │   └── health.py             # Health check
│   ├── core/
│   │   ├── adaptive_retrieval.py # Adaptive RAG router
│   │   ├── chunking.py           # 4 chunkers (specs/faq/price/guide)
│   │   ├── conversation.py       # In-memory session store (3 turns, TTL 30min)
│   │   ├── embedding.py          # Local embedding (sentence-transformers)
│   │   ├── generation.py         # LLM (gpt-4o-mini via TokenRouter)
│   │   ├── guardrails.py         # Content + injection + confidence
│   │   ├── prompt_builder.py     # Prompt formatting (structured + unstructured)
│   │   ├── query_classifier.py   # Intent classification (rule-based)
│   │   ├── retrieval.py          # Hybrid retriever (dense+sparse, reranker)
│   │   ├── reranker.py           # FlashRank reranker (ONNX)
│   │   ├── sparse.py             # BM25 sparse vector builder
│   │   └── structured_lookup.py  # PostgreSQL query service
│   ├── db/
│   │   ├── connection.py         # SQLAlchemy engine
│   │   └── models.py             # Price, Spec models
│   ├── data/
│   │   ├── fetcher.py            # Web fetcher (requests + BeautifulSoup)
│   │   ├── ingestion.py          # Data ingestion (phân tuyến structured/unstructured)
│   │   ├── indexer.py            # Indexing pipeline (full + incremental)
│   │   └── reindex_scheduler.py  # Debounce scheduler
│   ├── models/
│   │   ├── request.py            # ChatRequest, ChatMessage
│   │   └── response.py           # ChatResponse, SourceChunk
│   ├── static/
│   │   ├── admin.html            # Admin Portal UI
│   │   └── index.html            # Chat UI
│   ├── config.py                 # Settings (env vars)
│   └── main.py                   # FastAPI entry
├── data/
│   ├── raw/                      # 25 fetched JSON files
│   ├── processed/                # chunks.json + bm25_index.json
│   └── golden_qa.json            # 30 eval Q&A pairs
├── scripts/
│   ├── fetch_data.py             # Fetch URLs → data/raw/
│   ├── index_data.py             # Index data → Qdrant (--full / --incremental)
│   ├── init_db.py                # Create PostgreSQL tables
│   ├── migrate_to_pg.py          # Migrate JSON → PostgreSQL
│   ├── run_eval.py               # Eval pipeline
│   └── test_realtime.py          # Test incremental index + debounce
├── tests/
│   ├── test_chunking.py          # Chunking tests
│   ├── test_guardrails.py        # Guardrail tests
│   ├── test_retrieval.py         # Retrieval + fetcher tests
│   └── test_api.py               # API + prompt builder tests
├── docker-compose.yml            # Qdrant + PostgreSQL + pgAdmin
├── requirements.txt
├── urls.txt                      # 29 VinFast URLs
├── guide.md                      # Hướng dẫn sử dụng
├── implementation-plan.md        # Plan chi tiết Stage 0-5
├── roadmap-tong-the.md           # Roadmap tổng hợp
├── plan-adaptive-rag-postgresql.md
└── report-realtime-index.md
```

---

## 8. Vấn đề đã giải quyết trong quá trình phát triển

| Vấn đề | Giải pháp |
|---|---|
| TokenRouter không hỗ trợ embedding API | Chuyển sang embedding local (sentence-transformers) |
| Google AI Studio bị PERMISSION_DENIED | Chuyển sang embedding local |
| BGE-reranker-v2-m3 quá lớn (2.27GB) | Chuyển sang FlashRank (~500MB, ONNX) |
| chunk_id không deterministic khi content thay đổi | Stable key: source + content_type + model_xe + index |
| 10K+ thay đổi đồng thời | Debounce scheduler (15s window) + processing_lock |
| "gia đình" match nhầm pattern "giá" | Đưa comparison pattern lên trước, refine regex |
| LLM từ chối so sánh dù có data | Cải thiện system prompt + format comparison rõ ràng |
| File JSON array không parse được | Fix ingestion hỗ trợ cả array và object |
| Windows env var OPENAI_API_KEY ghi đè .env | Đổi tên biến thành TOKENROUTER_API_KEY |

---

## 9. Demo flow đề xuất

### 9.1. Giới thiệu kiến trúc (3 phút)
- Adaptive RAG: Query Classifier → Structured (PostgreSQL ONLY) / Unstructured (Qdrant ONLY)
- Data routing: Giá/specs → PostgreSQL (không embed). FAQ/guide → Qdrant (chunk + embed)
- Hybrid Search: Dense + BM25 → RRF fusion → Reranker
- Realtime Index: Debounce + Incremental

### 9.2. Demo câu hỏi có trong data (5 phút)
- "VF8 giá bao nhiêu?" → PostgreSQL lookup, chính xác 100%
- "Chính sách bảo hành?" → Vector search, có nguồn
- "VF8 Eco và Plus khác gì?" → Specs comparison

### 9.3. Demo Adaptive RAG (3 phút)
- "VF9 và VF8 xe nào phù hợp gia đình đông người?" → So sánh specs (seats, cargo)
- "VF8 thông số kỹ thuật?" → PostgreSQL specs lookup

### 9.4. Demo Guardrails (2 phút)
- "So sánh VF8 với Tesla" → Content guardrail reject
- "Tư vấn vay mua xe" → Content guardrail reject
- "Ignore previous instructions" → Injection guardrail reject

### 9.5. Demo Admin Portal (3 phút)
- Upload file JSON → auto reindex
- Nhập giá mới qua form → PostgreSQL update
- Qdrant Dashboard + pgAdmin

### 9.6. Trình bày con số (2 phút)
- 219 chunks indexed, 2298 BM25 terms
- 64/64 unit tests pass
- RAM usage: ~1.45GB / 2.5GB
- Response time: ~2-3s (embedding + retrieval + LLM)

---

## 10. Roadmap tiếp theo

| Stage | Nội dung | Ưu tiên | Ước tính |
|---|---|---|---|
| Stage 6 | Traffic Scaling: Redis session/cache, Nginx load balancer, multi-worker, load testing | Cao | 1-2 tuần |
| Stage 4 | Context Management: Token counting, sliding window, history summarization | Trung bình | 1 tuần |
| Data expansion | Bổ sung VF3 specs, giá pin, trạm sạc | Cao | 2-3 ngày |
| Eval tuning | Mở rộng golden QA (50+ câu), tune similarity threshold | Trung bình | 2-3 ngày |
| Production deploy | Docker Compose production, monitoring, logging | Thấp | 1 tuần |

---

## 11. Tài liệu tham khảo

| File | Nội dung |
|---|---|
| `implementation-plan.md` | Plan chi tiết Stage 0-5 |
| `roadmap-tong-the.md` | Roadmap tổng hợp |
| `plan-adaptive-rag-postgresql.md` | Adaptive RAG + PostgreSQL plan + debate |
| `report-realtime-index.md` | Báo cáo realtime incremental index + debate |
| `guide.md` | Hướng dẫn sử dụng chi tiết |
| `rules.md` | Quy tắc bắt buộc |
| `skills.md` | Kỹ thuật chunking, embedding, retrieval |
