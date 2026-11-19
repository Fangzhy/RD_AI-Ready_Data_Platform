# R&D AI-Ready Data Modeling & Knowledge Platform

## Development Plan — Streamlit Interview Demonstration

**Purpose:** Build a credible, interactive demonstration of how heterogeneous pharmaceutical research data can be standardized, modeled, validated, governed, and made reusable for analytics and GenAI retrieval (RAG).

**Target audience:** Hiring manager for an AI-Ready Data Modeling role.

**Data:** Synthetic compound-screening and assay data only. The demo is not a validated GxP system and must not imply access to company proprietary systems.

**Status:** Implementation and test outcomes are recorded under each phase below.

---

## 1. Goals and success criteria

The application should demonstrate that you can:

1. Translate R&D requirements into **conceptual, logical, and physical data models**.
2. Define and enforce **reusable schemas** across different source systems.
3. Handle practical integration issues: inconsistent naming, identifiers, units, missing fields, and duplicates.
4. Maintain **metadata, versioning, provenance, lineage, and quality decisions**.
5. Publish clean, discoverable datasets through **SQL and APIs**.
6. Explain how **taxonomy, ontology, and retrieval architectures** build on the shared data foundation.
7. Demonstrate an evidence-grounded **RAG use case**, without suggesting vector similarity alone establishes scientific truth.

**Definition of done for the core MVP:** The user can load two differently formatted synthetic datasets, map both into a shared schema, run validation, inspect rejected rows, query accepted records using one common model, and trace each curated result to its source and mapping version.

---

## 2. Demonstration scenario and synthetic datasets

**Scenario:** Research teams Alpha and Beta run related compound-screening experiments but use different ELN and LIMS field names. The platform standardizes them into shared entities so a scientist can query both projects and retrieve experimental evidence.

| Source | Illustrative data | Intentional differences or defects |
|---|---|---|
| ELN Alpha | Experiments, protocol notes, compound references | `ExpNumber`, `MaterialID` |
| LIMS Alpha | Samples, assay results | `TestName`, `ResultValue`, `ResultUnits` |
| ELN/LIMS Beta | Same domain, different local naming | `ExperimentCode`, `CompoundCode`, `UnitCode` |
| Compound registry | Canonical compound IDs, aliases | Multiple local aliases |
| Research documents | Synthetic assay reports and method descriptions | References to experiments and assays |

**Suggested volume:** ~100 experiments, ~300 samples, ~20 compounds, ~500–1,000 assay results, and 20–40 synthetic supporting documents. Small but relationally coherent data is preferable to a large, inconsistent synthetic dataset.

**Seed quality defects deliberately:** Missing units, nonnumeric results, duplicate IDs, unmatched sample/compound references, alternate assay terminology, conflicting units, and a superseded report. Preserve raw values; do not silently correct ambiguous scientific records.

---

## 3. Current starting point: schema-mapping app

The existing `rd_schema_mapper/` implementation includes:

- Streamlit CSV upload and synthetic sample source data.
- Editable default source-to-target mappings:

  | Source field | Canonical field |
  |---|---|
  | `ExpNumber` | `experiment_id` |
  | `MaterialID` | `compound_id` |
  | `TestName` | `assay_name` |
  | `ResultValue` | `result_value` |
  | `ResultUnits` | `result_unit` |

- Checks for duplicate target assignments, missing mappings, and source/target issues.
- JSON mapping import/export.
- Row-level required-field, numeric, nonnegative, and allowed-unit checks.
- Raw, accepted, and flagged record previews and CSV exports.
- Generated pandas transformation code, SQLite SQL view, and downloadable SQLite database.

**Important limitations to address:** Rules are illustrative, unit validation does not perform unit conversion, and SQLite casting is permissive. The current demo should not be described as enterprise-grade or GxP-validated.

### Local launch

See the repository README for root-level virtual environment, launch, and test commands.

---

## 4. Application pages and priorities

| Page | Primary capability | Priority | Acceptance check |
|---|---|---|---|
| 1. Overview | Data sources, pipeline state, quality counts | P1 | Counts match underlying records |
| 2. Schema Mapping | Source-to-target mapping and JSON configuration | **P0 — existing** | Duplicate targets are blocked; config round-trips |
| 3. Data Modeling Studio | Conceptual, logical, physical model and ERD | **P0** | Entities, keys and generated DDL are consistent |
| 4. Data Quality | Rules, failure reasons, quarantine, approved output | **P0 — extend existing** | Bad records never enter accepted dataset |
| 5. Metadata & Lineage | Field mappings, source IDs, transformation version | **P0** | Trace a curated result back to source row |
| 6. AI-Ready Data Explorer | SQL queries, cross-project view, API examples | **P0** | One query works across Alpha and Beta |
| 7. Taxonomy & Ontology | Controlled terms and typed scientific links | P1 | Alias normalization and graph traversal demonstrable |
| 8. RAG Assistant | Hybrid retrieval, provenance, citations | P2 | Cited answers grounded in retrieved evidence |

**Recommended focus:** Finish P0 pages first, then add one small but convincing P1 semantic example, then an optional P2 RAG demonstration.

---

## 5. Implementation phases

### Phase 0 — Baseline review and refactor (current prototype)

**Implementation status — complete.** Recreated the documented mapper because the referenced prototype was absent from the checkout. The five Phase 0 tests passed, including the UI smoke test, and the README screenshot was captured from the running app.

**Deliverables:** Maintain the existing working page while extracting reusable functions from UI code.

- Keep `app.py` as a launcher and move mapping, validation, and export logic into `src/` modules.
- Add deterministic synthetic input fixtures and tests for existing behaviors.
- Record mapping configuration version and an immutable source-record ID.
- Add a short README with commands, assumptions, known limitations, and screenshots.

**Acceptance:** The current mapping workflow still works after refactoring; tests cover duplicate-target rejection, invalid numeric strings, missing units, and configuration round-trip.

### Phase 1 — Shared conceptual, logical, and physical data models

**Implementation status — complete.** Six cumulative tests passed. Fresh SQLite DDL, foreign-key targets, a complete curated join, rejected orphan references, and the schema-derived ERD were verified.

**Deliverables:** A visible modeling studio and implemented relational database.

- **Conceptual entities:** `ResearchProject`, `Experiment`, `Compound`, `Sample`, `Assay`, `AssayRun`, `AssayResult`, `SourceRecord`, and `Document`.
- **Logical model:** Define attributes, stable identifiers, nullability, cardinality, reference tables, unique constraints, and association tables where needed.
- **Physical model:** Create SQLite/DuckDB tables, keys, indexes, and a unified curated result view.
- Use Graphviz to show an ERD; selecting an entity shows its definition, attributes, and underlying table.
- Add explicit source-to-canonical ID crosswalk tables; avoid joining entities by display name alone.

**Acceptance:** DDL executes on a new database; all declared foreign keys reference actual tables; one curated result joins to its experiment, sample, compound, and assay.

### Phase 2 — Reusable mappings, harmonization, and data quality

**Implementation status — complete.** Seven cumulative tests passed. The two deterministic feeds contain 600 input rows, 584 curated results, and 16 quarantined rows. Replaying Alpha preserves those counts. Original values, approved conversions, and field assignments are available for review.

**Deliverables:** Two source systems mapped into the same canonical schema.

- Add a Beta mapping profile, keeping source-specific mappings separate from shared entity definitions.
- Check mandatory fields, types, enumerations, uniqueness, referential integrity, and unit compatibility.
- Track mapping status, reasons for rejection, and transformations at field level.
- Convert units only for explicitly approved compatible quantities; retain original values and units.
- Keep flagged data in a quarantine table with reasons and recommended manual review.
- Add deterministic rerun behavior so a repeated load does not duplicate valid records.

**Acceptance:** Both sources appear in one standardized result table; invalid references and duplicate IDs are flagged; rerunning ingestion does not create additional copies.

### Phase 3 — Metadata, lineage, and governance

**Deliverables:** Searchable lineage explorer and a lightweight governance model.

- Capture `source_system`, `source_record_id`, `ingestion_run_id`, `mapping_version`, `transformation_id`, `quality_status`, `curated_record_id`, and timestamps.
- Display upstream lineage (curated record → source and mapping) and downstream impact (mapping → affected datasets/indexes).
- Record dataset ownership, descriptions, refresh timestamps, controlled vocabulary version, and access classification.
- Distinguish rejected, corrected, and unmodified accepted records.
- Demonstrate an authorization filter for restricted source documents *before* retrieval.

**Acceptance:** Every curated result has a resolvable origin; a changed mapping version identifies impacted derived records; restricted documents do not enter unauthorized search results.

### Phase 4 — Semantic modeling: taxonomy and ontology

**Deliverables:** A small, clearly scoped controlled vocabulary and knowledge graph.

- Create an assay taxonomy (e.g., biochemical → enzyme activity / binding; cell-based → viability).
- Provide preferred terms, synonyms, stable concept IDs, and source-term mappings.
- Define a lightweight ontology-aligned vocabulary for `Compound`, `Assay`, `Target`, `Experiment`, and `Result`, with precise relations such as `usesSample`, `measuresTarget`, and `reportedIn`.
- Build a NetworkX graph for visualization; optionally export RDF/Turtle using RDFLib.
- Preserve assertions' source references and distinguish **tested in** from **demonstrated active against**.

**Acceptance:** Searching via a synonym returns the canonical assay category; a user can traverse a compound → assay → supporting result relationship; each asserted edge has provenance.

### Phase 5 — AI-ready explorer and API

**Deliverables:** Reusable SQL views, query explorer, and an optional small FastAPI service.

- Build a read-only SQL explorer with curated sample queries and output previews.
- Expose a documented JSON representation for experiments and assay results.
- Add endpoints such as `GET /experiments/{experiment_id}`, `GET /compounds/{compound_id}`, and `GET /assay-results` if an API server is included.
- Validate API response schemas and use safe pagination/filtering.
- Show that two research projects can be queried using the same canonical field names.

**Acceptance:** A cross-project query returns reproducible results; API/JSON output uses the same identifiers and schema as SQL.

### Phase 6 — RAG proof of value (optional after core MVP)

**Deliverables:** A working document retrieval and evidence presentation page.

- Generate synthetic scientific notes/reports tied to the structured records.
- Chunk documents and preserve `document_id`, section, version, access class, and source link.
- Implement a baseline retriever (TF-IDF or embeddings) and metadata-aware retrieval.
- Optionally use a local Chroma index or another retrieval backend.
- Add graph/SQL retrieval for precise questions involving compounds, assays, and results.
- Make LLM generation optional; always display actual retrieved evidence and source IDs.
- When evidence is insufficient, the app should say so rather than invent a result.

**Acceptance:** Compare baseline vs metadata/relationship-aware retrieval on a fixed labeled question set (10–20 questions). Report actual Recall@5, citation correctness, and unanswered/unsupported cases without fabricated performance claims.

---

## 6. Reference architecture

```text
Synthetic ELN / LIMS / Registry / Research Documents
                     |
            Ingestion + CSV/API adapters
                     |
        Source record store (immutable raw)
                     |
       Mapping configurations (versioned JSON)
                     |
       Schema + referential/unit validation
                /            \
        Quarantine        Canonical SQL model
                               |
                  Metadata + lineage tables
                               |
          +--------------------+-------------------+
          |                    |                   |
      SQL explorer       Taxonomy/graph      Document index
          |                    |                   |
          +--------------------+-------------------+
                               |
                  Hybrid retrieval for RAG
                               |
                 Source-grounded answer UI
```

### Proposed technology stack

| Layer | Tool | Reason |
|---|---|---|
| Frontend | Streamlit | Fast interactive multipage prototype |
| Processing | pandas | Ingestion and transformations |
| Validation | Pydantic + custom rules | Explicit data contracts and cross-row validation |
| Relational storage | SQLite initially; DuckDB optional | Portable demo and SQL queries |
| Diagramming | Graphviz | Conceptual/logical ERDs |
| Vocabulary | JSON / relational tables | Simple versionable taxonomy |
| Graph | NetworkX; RDFLib optional | Semantic relationships and SPARQL proof of concept |
| API | FastAPI optional | Independent access to reusable data |
| Retrieval | scikit-learn TF-IDF, embeddings optional | Demonstrable baseline and extensions |
| Testing | pytest | Repeatable evidence of correctness |

Keep business logic outside Streamlit page modules. The SQL database should be the source of truth for curated records; do not make a vector index the canonical system of record.

---

## 7. Suggested repository structure

```text
rd-ai-ready-platform/
├── app.py
├── requirements.txt
├── README.md
├── pages/
│   ├── 01_overview.py
│   ├── 02_schema_mapping.py
│   ├── 03_data_modeling.py
│   ├── 04_data_quality.py
│   ├── 05_lineage.py
│   ├── 06_data_explorer.py
│   ├── 07_semantic_model.py
│   └── 08_rag_assistant.py
├── src/
│   ├── data_generation.py
│   ├── mapping.py
│   ├── schemas.py
│   ├── validation.py
│   ├── relational_model.py
│   ├── database.py
│   ├── lineage.py
│   ├── taxonomy.py
│   ├── graph.py
│   └── retrieval.py
├── configs/
│   ├── mappings_alpha.json
│   ├── mappings_beta.json
│   └── data_contracts.json
├── models/
│   ├── conceptual_model.md
│   ├── logical_model.json
│   ├── physical_schema.sql
│   └── ontology.ttl
├── data/
│   ├── synthetic_raw/
│   ├── documents/
│   └── curated/
└── tests/
    ├── test_mapping.py
    ├── test_validation.py
    ├── test_referential_integrity.py
    ├── test_lineage.py
    └── test_retrieval.py
```

---

## 8. Detailed backlog by priority

### Must have (P0)

- [ ] Extract reusable mapping and validation functions from current Streamlit code.
- [ ] Add second source system and versioned mapping profile.
- [ ] Define conceptual entities and their scientific definitions.
- [ ] Create logical model with primary/foreign keys and cardinalities.
- [ ] Implement physical SQL schema and curated result view.
- [ ] Add referential integrity and controlled unit checks.
- [ ] Save source IDs, mapping version, validation outcomes, and lineage.
- [ ] Implement read-only cross-project SQL queries.
- [ ] Write tests for common failure cases and repeat loads.
- [ ] Build a repeatable 5–7 minute walkthrough.

### Should have (P1)

- [ ] Interactive ERD and entity inspector.
- [ ] Source/target field-level mapping audit and impact analysis.
- [ ] Taxonomy explorer with preferred terms and aliases.
- [ ] Small provenance-aware scientific knowledge graph.
- [ ] API endpoint or JSON export for a reusable entity.
- [ ] Quality and readiness dashboard.

### Could have (P2)

- [ ] Baseline document search and metadata-aware search comparison.
- [ ] Vector embeddings and a persistent search index.
- [ ] Graph-assisted retrieval for multi-hop scientific questions.
- [ ] LLM answer generation with explicit source citations.
- [ ] Retrieval evaluation dashboard with labeled test cases.

---

## 9. Testing and validation plan

| Test | Expected outcome |
|---|---|
| Two source fields map to one target | Mapping blocked with a clear error |
| Required target unmapped | Cannot publish mapping |
| Missing result unit | Record flagged; original preserved |
| Result value contains letters | Record flagged; not silently converted to a number |
| Unknown compound/sample ID | Referential integrity error |
| Duplicate source row on rerun | No duplicate accepted record |
| Alias assay term | Maps to approved canonical concept when unambiguous |
| Mapping configuration export/import | Identical mapping after round-trip |
| Mapping version changes | Derived records and indexes identified for review |
| Restricted evidence | Not included in unauthorized retrieval |
| RAG question with no evidence | Returns an explicit insufficient-evidence outcome |

Use deterministic fixtures and unit tests; do not claim that this demo constitutes formal regulated-system validation.

---

## 10. Interview walkthrough (5–7 minutes)

| Sequence | Show | Message to hiring manager |
|---|---|---|
| 1 | Alpha and Beta raw datasets | R&D systems have different field conventions |
| 2 | Editable source-to-target mappings | Shared schemas reconcile heterogeneous sources |
| 3 | Conceptual, logical, physical ERDs | Scientific requirements become reusable data architecture |
| 4 | Quality failures and quarantined records | Data quality and scientific integrity are enforced |
| 5 | Curated cross-project SQL query | One common model supports multiple consumers |
| 6 | Lineage from result to source | Every output has transparent provenance |
| 7, if ready | Taxonomy and evidence retrieval | Well-structured data enables more reliable GenAI |

### Opening script

> "I built this synthetic R&D data platform to demonstrate how I approach AI-ready data modeling. It begins with inconsistent source records, maps them into standardized schemas, enforces data quality, and links experiments, samples, compounds, and assay results through a shared data model. I then make those records available for cross-project SQL queries and traceable scientific evidence retrieval. The goal is to demonstrate reusable data modeling rather than a chatbot alone."

### Questions to anticipate

- **Why use three modeling levels?** Conceptual captures domain meaning, logical captures entity relationships and constraints, physical makes it executable in the chosen database.
- **How are schemas different from data models?** Schemas specify fields and validation rules; a model describes entities, relationships, and semantics.
- **How would this scale beyond the demo?** Replace local files/SQLite with governed ingestion, shared catalogs, managed databases, access controls, and monitored pipelines while retaining versioned contracts.
- **When is an ontology useful?** When standardizing scientific meaning and navigating complex cross-system relationships adds measurable value; not required for every RAG implementation.
- **How do you prevent hallucinations?** Verified metadata and source linking, authorization-aware retrieval, citations, structured answers, and explicit abstention when evidence is insufficient.

---

## 11. Risks, assumptions, and scope boundaries

- **Synthetic scientific data:** Do not make clinical, biological, or efficacy claims from invented data.
- **Scientific measurements:** Nonnegative value checks and unit whitelists are assay-specific examples, not universal rules.
- **Identifier matching:** Do not equate records just because compound or sample names look similar; use governed crosswalks.
- **Ontology claims:** A NetworkX visualization alone is not a production ontology; distinguish concept definitions from asserted facts.
- **SQL safety:** Use read-only queries or known templates in the demo; never run unrestricted user SQL against valuable data.
- **Security and governance:** Access controls in a demo illustrate requirements, but do not imply production security certification.
- **RAG evidence:** Vector similarity is a retrieval signal, not a scientific validation method.
- **Regulated use:** This application is a prototype, not validated for GxP or Part 11 use.

---

## 12. Recommended next coding milestone

**Next task:** Implement **Phase 1 shared data modeling** on top of the existing `rd_schema_mapper` application.

Deliver, in this order:

1. `physical_schema.sql` with Experiment, Compound, Sample, Assay, and AssayResult entities.
2. A deterministic generator for a second source system with renamed columns.
3. Two JSON mapping profiles producing the same canonical fields.
4. A Streamlit page displaying conceptual, logical, and physical views.
5. A single SQL query returning validated assay results from both projects.
6. Tests for referential integrity and mapping consistency.

**Milestone completion criterion:** Demonstrate that one standardized data model supports two independently formatted R&D sources and produces a single traceable, queryable dataset.
