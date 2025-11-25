# Parlant Architecture Guide

> A comprehensive guide to understanding the Parlant codebase structure, patterns, and interconnections.

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [The Three Pillars](#the-three-pillars)
- [Hexagonal Architecture](#hexagonal-architecture)
- [Request Flow](#request-flow)
- [Module Dependencies](#module-dependencies)
- [Important Files](#important-files)
- [Test Structure](#test-structure)
- [Development Tasks](#development-tasks)
- [Architectural Patterns](#architectural-patterns)

---

## Overview

Parlant is a Python-based AI agent framework following **Hexagonal Architecture** (Ports and Adapters pattern). It enables developers to create compliant, controlled AI agents for customer-facing use cases with enterprise-grade features.

**Core Strengths:**
1. Compliant and controlled AI agents for customer-facing use cases
2. Conversational management features out of the box
3. Built for enterprise, large-scale use cases with focus on SLAs, stability, and security

---

## Repository Structure

```
parlant/
├── 📂 src/parlant/          ⭐ Main source code
├── 📂 tests/                ⭐ Test suite (mirrors src/)
├── 📂 docs/                 📚 Documentation
├── 📂 examples/             💡 Example implementations
├── 📂 scripts/              🔧 Utility scripts
├── 📂 data/                 📊 Synthetic conversation data
├── 📂 journeys/             🗺️ Journey definitions
├── 📂 parlant-data/         💾 Runtime data directory
├── 📄 pyproject.toml        📦 Poetry dependencies
├── 📄 CLAUDE.md             🤖 AI assistant instructions
├── 📄 ARCHITECTURE.md       📖 This file
└── 📄 README.md             📖 Main documentation
```

---

## The Three Pillars

### 1. core/ - Business Logic (The Brain 🧠)

The core contains all domain logic, completely independent of external frameworks.

```
core/
│
├── 📋 Domain Models (Entities)
│   ├── agents.py (463 lines)           # Agent definitions
│   ├── sessions.py (1,234 lines)       # Conversation sessions
│   ├── guidelines.py (621 lines)       # Behavioral rules
│   ├── journeys.py (1,331 lines)       # Conversation flows
│   ├── customers.py (487 lines)        # Customer entities
│   ├── context_variables.py (691 lines)# Dynamic context
│   ├── canned_responses.py (713 lines) # Pre-defined responses
│   ├── capabilities.py (577 lines)     # Agent capabilities
│   ├── glossary.py (541 lines)         # Domain terminology
│   ├── tools.py (563 lines)            # Tool definitions
│   ├── tags.py (266 lines)             # Tagging system
│   ├── relationships.py (489 lines)    # Entity relationships
│   └── evaluations.py (1,026 lines)    # Behavior evaluation
│
├── 🎯 Application Layer (Use Cases)
│   └── app_modules/
│       ├── agents.py                   # Agent operations
│       ├── sessions.py                 # Session operations
│       ├── guidelines.py               # Guideline operations
│       ├── journeys.py                 # Journey operations
│       ├── customers.py                # Customer operations
│       ├── context_variables.py        # Variable operations
│       ├── canned_responses.py         # Response operations
│       ├── capabilities.py             # Capability operations
│       ├── glossary.py                 # Glossary operations
│       ├── relationships.py            # Relationship operations
│       ├── evaluations.py              # Evaluation operations
│       └── services.py                 # Service management
│
├── 🤖 Engine (The Heart)
│   └── engines/alpha/                  # Main "Alpha" engine
│       ├── engine.py                   # Core orchestration
│       ├── message_generator.py        # Generate responses
│       ├── canned_response_generator.py# Handle canned responses
│       ├── prompt_builder.py           # Build prompts
│       ├── hooks.py                    # Extension points
│       ├── loaded_context.py           # Context management
│       │
│       ├── 🎯 guideline_matching/     # Match guidelines to context
│       │   ├── guideline_matcher.py
│       │   └── generic/
│       │       ├── disambiguation_batch.py
│       │       ├── guideline_actionable_batch.py
│       │       ├── journey_node_selection_batch.py
│       │       ├── observational_batch.py
│       │       └── response_analysis_batch.py
│       │
│       └── 🔧 tool_calling/            # Execute tools
│           ├── tool_caller.py
│           ├── single_tool_batch.py
│           └── overlapping_tools_batch.py
│
├── 🔌 Ports (Interfaces)
│   ├── persistence/
│   │   ├── document_database.py        # Document DB interface
│   │   └── vector_database.py          # Vector DB interface
│   ├── nlp/
│   │   ├── service.py                  # NLP service interface
│   │   ├── generation.py               # Text generation
│   │   ├── embedding.py                # Embedding interface
│   │   └── moderation.py               # Content moderation
│   ├── loggers.py                      # Logging interface
│   ├── tracer.py                       # Tracing interface
│   └── meter.py                        # Metrics interface
│
└── 🛠️ Infrastructure Services
    ├── application.py                  # DI container
    ├── background_tasks.py             # Background jobs
    ├── emissions.py                    # Event emission
    └── services/
        ├── indexing/                   # Indexing services
        └── tools/                      # Tool services
            ├── service_registry.py
            ├── plugins.py
            ├── openapi.py
            └── mcp_service.py
```

### 2. adapters/ - External Integrations (The Hands 🤝)

Implementations of core interfaces using real external services.

```
adapters/
│
├── 💾 Database Adapters
│   ├── db/
│   │   ├── json_file.py                # JSON file storage (dev)
│   │   ├── mongo_db.py                 # MongoDB (production)
│   │   └── transient.py                # In-memory (testing)
│   │
│   └── vector_db/
│       ├── chroma.py                   # ChromaDB (production)
│       └── transient.py                # nano_vectordb (testing)
│
├── 🤖 NLP Service Adapters (18+ providers!)
│   ├── openai_service.py               # OpenAI GPT-4o, GPT-4.1
│   ├── anthropic_service.py            # Claude Sonnet 4, Opus 4.1
│   ├── azure_service.py                # Azure OpenAI
│   ├── aws_service.py                  # AWS Bedrock
│   ├── gemini_service.py               # Google Gemini
│   ├── vertex_service.py               # Google Vertex AI
│   ├── deepseek_service.py             # DeepSeek
│   ├── cerebras_service.py             # Cerebras
│   ├── together_service.py             # Together.ai
│   ├── mistral_service.py              # Mistral AI
│   ├── fireworks_service.py            # Fireworks AI
│   ├── ollama_service.py               # Ollama (local)
│   ├── litellm_service.py              # LiteLLM
│   ├── qwen_service.py                 # Qwen
│   ├── glm_service.py                  # GLM
│   ├── modelscope_service.py           # ModelScope
│   ├── snowflake_cortex_service.py     # Snowflake Cortex
│   └── hugging_face.py                 # Hugging Face
│
└── 📊 Observability Adapters
    ├── loggers/
    │   ├── websocket.py                # WebSocket logger (UI)
    │   └── opentelemetry.py            # OpenTelemetry logger
    ├── tracing/
    │   └── opentelemetry.py            # Distributed tracing
    └── meter/
        └── opentelemetry.py            # Metrics collection
```

### 3. api/ - REST API Layer (The Voice 📢)

HTTP endpoints exposing functionality via FastAPI.

```
api/
│
├── 🌐 FastAPI Application
│   ├── app.py                          # ASGI app setup
│   ├── authorization.py                # Auth & rate limiting
│   └── common.py                       # Shared utilities
│
├── 🔗 REST Endpoints
│   ├── agents.py                       # POST/GET /agents
│   ├── sessions.py                     # POST/GET /sessions
│   ├── guidelines.py                   # POST/GET /guidelines
│   ├── journeys.py                     # POST/GET /journeys
│   ├── customers.py                    # POST/GET /customers
│   ├── context_variables.py            # POST/GET /context-variables
│   ├── canned_responses.py             # POST/GET /canned-responses
│   ├── capabilities.py                 # POST/GET /capabilities
│   ├── glossary.py                     # POST/GET /terms
│   ├── relationships.py                # POST/GET /relationships
│   ├── evaluations.py                  # POST/GET /evaluations
│   ├── services.py                     # POST/GET /services
│   ├── tags.py                         # POST/GET /tags
│   └── logs.py                         # WebSocket /logs
│
└── 💬 Integrated Chat UI (React/TypeScript)
    └── chat/
        ├── dist/                       # Built assets (served by API)
        ├── src/
        │   ├── components/
        │   │   ├── chatbot/            # Chat interface
        │   │   ├── message/            # Message display
        │   │   ├── session-list/       # Session management
        │   │   ├── session-view/       # Session details
        │   │   ├── agents-list/        # Agent management
        │   │   ├── canned-responses/   # Response management
        │   │   └── log-filters/        # Log filtering
        │   ├── hooks/                  # React hooks
        │   └── lib/                    # Utilities
        ├── package.json
        └── vite.config.ts
```

---

## Hexagonal Architecture

Parlant strictly follows Hexagonal Architecture (Ports and Adapters pattern):

### Core Concepts

- **Ports** = Interfaces (abstract classes) that define contracts
- **Adapters** = Concrete implementations of those interfaces
- **Core** = Business logic that depends only on ports, never on adapters

### Example: Document Database

**Port Definition** (`core/persistence/document_database.py`):
```python
class DocumentDatabase(ABC):
    @abstractmethod
    async def create_collection(
        self, name: str, schema: type[TDocument]
    ) -> DocumentCollection[TDocument]:
        """Create a collection for storing documents"""
```

**Adapters** (Multiple Implementations):
1. `adapters/db/mongo_db.py` - MongoDB for production
2. `adapters/db/json_file.py` - JSON files for development
3. `adapters/db/transient.py` - In-memory for testing

### Port-Adapter Mapping

| Port (Interface) | Location | Adapters |
|-----------------|----------|----------|
| `DocumentDatabase` | `core/persistence/document_database.py` | MongoDB, JSON Files, In-Memory |
| `VectorDatabase` | `core/persistence/vector_database.py` | ChromaDB, nano_vectordb |
| `NLPService` | `core/nlp/service.py` | OpenAI, Anthropic, Ollama, +15 more |
| `Logger` | `core/loggers.py` | Stdout, File, WebSocket, OpenTelemetry |
| `Meter` | `core/meter.py` | Null, OpenTelemetry |
| `Tracer` | `core/tracer.py` | Local, OpenTelemetry |

### Benefits

1. **Testability**: Use transient adapters for fast, isolated testing
2. **Flexibility**: Swap implementations without changing business logic
3. **Independence**: Core has zero dependencies on external frameworks
4. **Environment-Based**: Different adapters for dev vs production

---

## Request Flow

### User Message → Agent Response

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User sends message via REST API                             │
│     POST /sessions/{session_id}/events                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. API Layer (api/sessions.py)                                 │
│     • Validates request                                         │
│     • Extracts session_id and message                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Application Layer (core/app_modules/sessions.py)            │
│     • SessionModule.post_event()                                │
│     • Retrieves session from SessionStore                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Engine (core/engines/alpha/engine.py)                       │
│     • AlphaEngine.respond()                                     │
│     • Orchestrates the response generation                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Context │    │Guideline│    │  Tool   │
    │ Loading │    │Matching │    │ Calling │
    └────┬────┘    └────┬────┘    └────┬────┘
         │              │              │
         └──────────────┼──────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Guideline Matcher                                           │
│     (core/engines/alpha/guideline_matching/guideline_matcher.py)│
│     • Loads relevant guidelines from GuidelineStore             │
│     • Uses NLPService to match guidelines to context            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. NLP Service (via adapter)                                   │
│     • core/nlp/service.py (interface)                           │
│     • adapters/nlp/openai_service.py (implementation)           │
│     • Calls GPT-4o/Claude/Llama to match guidelines             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. Tool Execution (if needed)                                  │
│     (core/engines/alpha/tool_calling/tool_caller.py)            │
│     • Identifies required tools from matched guidelines         │
│     • Executes tools via ServiceRegistry                        │
│     • Returns tool results                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. Message Generation                                          │
│     (core/engines/alpha/message_generator.py)                   │
│     • Builds prompt with matched guidelines + tool results      │
│     • Uses NLPService to generate final response                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  9. Event Emission & Storage                                    │
│     • Saves message to SessionStore (via adapter)               │
│     • Emits events for real-time updates                        │
│     • Returns response to API layer                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  10. Response returned to user                                  │
│      HTTP 200 with agent message                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Dependencies

### Layer Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENTRY POINTS                            │
│  • bin/server.py (parlant-server command)                       │
│  • bin/client.py (parlant CLI)                                  │
│  • sdk.py (Python SDK for developers)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │ imports
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API LAYER                               │
│  • api/*.py (FastAPI endpoints)                                 │
│  • Depends on: core/app_modules/*, core/application.py          │
└────────────────────────┬────────────────────────────────────────┘
                         │ imports
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                            │
│  • core/app_modules/*.py (use cases)                            │
│  • Depends on: core domain models, core/engines/*, stores       │
└────────────────────────┬────────────────────────────────────────┘
                         │ imports
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                               │
│  • core/*.py (entities, business logic)                         │
│  • core/engines/alpha/ (engine implementation)                  │
│  • Depends on: ONLY interfaces (ports), NO concrete adapters    │
└────────────────────────┬────────────────────────────────────────┘
                         │ uses (via DI)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ADAPTER LAYER                              │
│  • adapters/db/*.py (database implementations)                  │
│  • adapters/nlp/*.py (LLM provider implementations)             │
│  • adapters/vector_db/*.py (vector DB implementations)          │
│  • Depends on: core interfaces + external libraries             │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Injection

Parlant uses the **Lagom** DI container (configured in `bin/server.py`):

```python
@asynccontextmanager
async def setup_container() -> AsyncIterator[Container]:
    c = Container()

    # Choose adapter based on environment
    await _define_tracer(c)  # OpenTelemetry or Local
    await _define_logger(c)  # OpenTelemetry or Stdout
    await _define_meter(c)   # OpenTelemetry or Null

    # Core business logic services
    _define_singleton(c, Engine, AlphaEngine)
    _define_singleton(c, Application, Application)

    yield c
```

**Environment-Based Adapter Selection:**
```python
async def _define_tracer(container: Container) -> None:
    # Check if OpenTelemetry is configured
    if os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"):
        # Production: Use OpenTelemetry
        from parlant.adapters.tracing.opentelemetry import OpenTelemetryTracer
        container[Tracer] = await EXIT_STACK.enter_async_context(
            OpenTelemetryTracer()
        )
    else:
        # Development: Use local tracer
        _define_singleton(container, Tracer, LocalTracer)
```

---

## Important Files

### Most Critical Files

| File | Lines | Purpose | When to Use |
|------|-------|---------|-------------|
| `bin/server.py` | ~900 | Server entry point, DI setup | Starting server, understanding wiring |
| `sdk.py` | 30,220 | Developer SDK | Creating agents, tools, sessions |
| `core/engines/alpha/engine.py` | ~700 | Main engine logic | Understanding response flow |
| `core/application.py` | ~500 | DI container | Understanding dependency injection |
| `core/sessions.py` | 1,234 | Session management | Working with conversations |
| `core/guidelines.py` | 621 | Guideline system | Creating behavioral rules |
| `core/engines/alpha/guideline_matching/guideline_matcher.py` | ~800 | Guideline matching | Understanding how guidelines are applied |
| `core/engines/alpha/message_generator.py` | ~600 | Response generation | Understanding message creation |
| `adapters/nlp/openai_service.py` | ~400 | OpenAI integration | Adding/modifying LLM support |
| `api/sessions.py` | ~500 | Session API | Working with REST API |

### Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Poetry dependencies, project metadata |
| `mypy.ini` | Type checking configuration (strict mode!) |
| `ruff.toml` | Ruff linter configuration |
| `pytest.ini` | Pytest test configuration |
| `CLAUDE.md` | Development workflow and TDD instructions |
| `ARCHITECTURE.md` | This file - architecture reference |

### Entry Points

| File | Purpose | Command |
|------|---------|---------|
| `src/parlant/bin/server.py` | Main server entry point | `parlant-server run` |
| `src/parlant/bin/client.py` | CLI client | `parlant` |
| `src/parlant/sdk.py` | SDK entry point | `import parlant.sdk as p` |

---

## Test Structure

The `tests/` directory mirrors the `src/` structure:

```
tests/
├── conftest.py                     # Root test fixtures
│
├── adapters/                       # Test adapters
│   ├── db/
│   │   ├── test_json_file.py
│   │   ├── test_mongo_db.py
│   │   └── test_transient.py
│   └── nlp/
│       └── test_*.py
│
├── api/                            # API endpoint tests
│   ├── conftest.py
│   └── test_*.py
│
├── core/
│   ├── conftest.py                 # Core fixtures
│   ├── common/
│   │   ├── engines/
│   │   │   └── alpha/
│   │   │       └── steps/         # BDD step definitions
│   │   └── utils.py
│   │
│   ├── stable/                     # Production-ready tests
│   │   ├── engines/
│   │   │   └── alpha/
│   │   │       ├── test_guideline_matcher.py
│   │   │       ├── test_tool_caller.py
│   │   │       ├── test_baseline_scenarios.py
│   │   │       └── test_user_story_scenarios.py
│   │   ├── persistence/
│   │   ├── services/
│   │   └── test_*.py
│   │
│   └── unstable/                   # Experimental tests
│       └── engines/
│
├── sdk/                            # SDK tests
│   ├── conftest.py
│   └── test_*.py
│
└── e2e/                            # End-to-end tests
    ├── conftest.py
    └── test_*.py
```

### Test Naming Convention

Pattern: `test_that_{context}_{action}_{expected_result}`

Example:
```python
def test_that_guideline_matches_when_condition_is_met():
    # Test implementation
```

### Test Infrastructure

- **Base class**: `SDKTest` for testing engine behavior
- **Framework**: pytest with async support
- **Fixtures**: Defined in `conftest.py` files at each level
- **Isolation**: Uses transient adapters for fast, isolated tests

---

## Development Tasks

### Common Tasks and File Locations

| Task | Files to Modify |
|------|-----------------|
| Add new LLM provider | Create `adapters/nlp/my_service.py`, update `bin/server.py` |
| Add new domain entity | Create `core/my_entity.py`, `core/app_modules/my_entity.py`, `api/my_entity.py` |
| Modify guideline matching | Edit files in `core/engines/alpha/guideline_matching/` |
| Add new tool | Use `@tool` decorator in SDK or create plugin service |
| Change prompt behavior | Edit `core/engines/alpha/prompt_builder.py` |
| Add API endpoint | Create `api/my_endpoint.py`, update `api/app.py` |
| Modify storage | Implement new adapter in `adapters/db/` |
| Add observability | Implement in `adapters/loggers/`, `adapters/tracing/`, `adapters/meter/` |

### Development Workflow (TDD)

From `CLAUDE.md`:

1. **Write failing tests first**
2. **Implement minimal code** to pass tests
3. **Refactor** for clarity and maintainability
4. **Format** with ruff: `poetry run ruff format .`
5. **Type check** with mypy: `poetry run python scripts/lint.py --mypy --ruff`

### Running Tests

```bash
# Run specific test
poetry run pytest tests/path/to/test_file.py::test_name

# Run with coverage
poetry run pytest --cov=src/parlant

# Run stable tests only
poetry run pytest tests/core/stable/

# Lint and type check
poetry run python scripts/lint.py --mypy --ruff
```

### Starting the Server

```bash
# Development mode with OpenAI
parlant-server run --openai

# With custom module
parlant-server run --openai --module my_module

# With migration
parlant-server run --openai --migrate

# Using different providers
parlant-server run --anthropic
parlant-server run --ollama
```

---

## Architectural Patterns

### 1. Hexagonal Architecture (Ports and Adapters)

**Principles:**
- Core business logic independent of external frameworks
- Dependencies point inward (from adapters to core)
- Interfaces (ports) define contracts
- Multiple implementations (adapters) possible

**Example:**
```python
# Port (in core/)
class NLPService(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...

# Adapter (in adapters/)
class OpenAIService(NLPService):
    async def generate(self, prompt: str) -> str:
        # Implementation using OpenAI API
```

### 2. Dependency Injection

**Container-based DI** using Lagom:
- All dependencies registered in `bin/server.py`
- Services injected through constructors
- Easy to swap implementations for testing

### 3. CQRS (Command Query Responsibility Segregation)

**Separation of reads and writes:**
- `EntityQueries`: Read operations
- `EntityCommands`: Write operations
- Implemented in `core/entity_cq.py`

### 4. Event-Driven Architecture

**Event emission for real-time updates:**
- `EventEmitter` for publishing events
- Event buffering and publishing
- WebSocket-based real-time updates to UI
- Background task processing

### 5. Engine Pipeline

**The Alpha engine processes requests through stages:**

1. **Context Loading**: Load relevant context (agent, customer, session)
2. **Guideline Matching**: Match applicable guidelines using NLP
3. **Tool Execution**: Execute required tools
4. **Response Generation**: Generate final agent response
5. **Event Emission**: Emit events for tracking and UI updates

### 6. Strategy Pattern

**Multiple strategies for guideline matching:**
- `DisambiguationBatch` - Disambiguate between guidelines
- `GuidelineActionableBatch` - Check if guideline is actionable
- `JourneyNodeSelectionBatch` - Select journey nodes
- `ObservationalBatch` - Observational guidelines
- `ResponseAnalysisBatch` - Analyze previous responses

### 7. Plugin Architecture

**Three ways to integrate tools:**

1. **SDK Tools**: Python functions with `@tool` decorator
   ```python
   @p.tool()
   def get_weather(location: str) -> str:
       return "Sunny, 72°F"
   ```

2. **Plugin Services**: Separate HTTP services
   ```python
   service = PluginService(url="http://localhost:8080")
   ```

3. **OpenAPI**: Auto-generated from OpenAPI specs
   ```python
   service = OpenAPIService(spec_url="http://api.example.com/openapi.json")
   ```

---

## Architectural Rules

### The "Never" Rules

❌ **Core NEVER imports from adapters**
- Core defines interfaces, adapters implement them
- Keeps business logic independent

❌ **Core NEVER imports from api**
- API layer depends on core, not vice versa
- Maintains clean separation of concerns

❌ **Domain models NEVER have external dependencies**
- Pure Python with type hints
- No framework-specific code

✅ **Everything flows through interfaces (ports)**
- Dependency Injection wires concrete implementations
- Easy to swap implementations

### Data Flow Rules

```
HTTP Request
    ↓ (handled by)
API Layer (FastAPI)
    ↓ (calls)
Application Layer (Use Cases)
    ↓ (orchestrates)
Domain Layer (Business Logic)
    ↓ (uses via interfaces)
Adapter Layer (External Services)
    ↓ (communicates with)
External Systems (OpenAI, MongoDB, ChromaDB, etc.)
```

---

## Key Innovations

### 1. Guideline System

**Core innovation** - ensures agent compliance:
- Guidelines define conditions and actions
- Matched contextually using LLM
- Multiple matching strategies (actionable, observational, etc.)
- Built-in explainability

**Example:**
```python
guideline = Guideline(
    condition="User asks about pricing",
    action="Provide pricing from the price list tool"
)
```

### 2. Journey Management

**Structured conversation flows:**
- Define customer journey steps
- Map guidelines to journey nodes
- Track progress through journey
- Enable goal-oriented conversations

### 3. Multi-Provider NLP Support

**Support for 18+ LLM providers:**
- Provider selection via CLI flags or SDK
- Common interface: `NLPService`
- Adapter pattern for each provider
- Easy to add new providers

### 4. Tool Integration Framework

**Flexible tool integration:**
- SDK decorators for Python functions
- Plugin services for HTTP tools
- OpenAPI auto-generation
- Tool chaining and batching

### 5. Canned Responses

**Pre-defined response templates:**
- Match user input to canned responses
- Generate follow-up responses
- Composition mode for complex responses
- Hallucination prevention

---

## Module System

Parlant supports custom modules for extensibility.

### Module Structure

```python
# my_module.py
from lagom import Container

async def configure_module(container: Container) -> Container:
    # Modify container, register services
    return container

async def initialize_module(container: Container) -> None:
    # Initialize resources (databases, connections, etc.)
    pass

async def shutdown_module() -> None:
    # Cleanup resources
    pass
```

### Module Management

```bash
# Create module from template
parlant-server module create my_module --template tool-service

# Enable module
parlant-server module enable my_module

# List modules
parlant-server module list

# Load module at runtime
parlant-server run --openai --module my_module
```

---

## Observability

### Logging

**Multiple logging adapters:**
- `StdoutLogger` - Console output (development)
- `FileLogger` - Log files (development)
- `WebSocketLogger` - Real-time UI streaming
- `OpenTelemetryLogger` - Enterprise logging (production)

**Usage:**
```python
logger.info("Processing user message")
with logger.scope("guideline_matching"):
    logger.debug("Matched 5 guidelines")
```

### Metrics

**Metrics collection via Meter interface:**
- `NullMeter` - No-op (development)
- `OpenTelemetryMeter` - Production metrics

**Usage:**
```python
counter = meter.create_counter("messages_processed", "Total messages")
counter.add(1)

histogram = meter.create_duration_histogram("response_time", "Response time")
with histogram.measure():
    # Process request
```

### Tracing

**Distributed tracing:**
- `LocalTracer` - Simple in-process tracing
- `OpenTelemetryTracer` - Distributed tracing (production)

**Usage:**
```python
with tracer.span("process_message"):
    # Process message
    tracer.add_event("guidelines_matched")
```

---

## Summary

Parlant is a well-architected, enterprise-ready AI agent framework with:

✅ **Clear separation of concerns** (Hexagonal Architecture)
✅ **Comprehensive test coverage** (TDD approach)
✅ **Multiple LLM provider support** (18+ providers)
✅ **Flexible storage backends** (MongoDB, JSON, in-memory)
✅ **Extensible module system** (Custom modules and plugins)
✅ **Production-ready features** (Tracing, metrics, logging)
✅ **Developer-friendly SDK** (Python decorators and helpers)
✅ **Built-in compliance** (Guidelines and explainability)

The codebase is organized to make it easy to:
- Add new LLM providers (`adapters/nlp/`)
- Extend engine behavior (`core/engines/alpha/`)
- Add new domain entities (`core/`)
- Create custom tools and services (modules)
- Test thoroughly (`tests/` mirrors `src/`)

---

## Further Reading

- **README.md** - Getting started guide
- **CLAUDE.md** - Development workflow and TDD instructions
- **CONTRIBUTING.md** - Contribution guidelines
- **docs/** - Comprehensive documentation
- **examples/** - Example implementations

---

*Last Updated: November 2025*
