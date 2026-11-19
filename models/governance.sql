CREATE TABLE ingestion_run (
    ingestion_run_id TEXT PRIMARY KEY NOT NULL,
    source_system TEXT NOT NULL,
    mapping_version TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    loaded_at TEXT NOT NULL,
    FOREIGN KEY (source_system,mapping_version) REFERENCES mapping_profile
);
CREATE TABLE lineage_event (
    ingestion_run_id TEXT NOT NULL REFERENCES ingestion_run,
    source_record_id TEXT NOT NULL REFERENCES source_record,
    transformation_id TEXT NOT NULL,
    quality_status TEXT NOT NULL,
    curated_record_id TEXT,
    reasons TEXT NOT NULL,
    audit_json TEXT NOT NULL,
    PRIMARY KEY(ingestion_run_id,source_record_id)
);
CREATE INDEX lineage_by_origin ON lineage_event(source_record_id);
CREATE TABLE dataset_catalog (
    dataset TEXT PRIMARY KEY NOT NULL,
    owner TEXT NOT NULL,
    description TEXT NOT NULL,
    vocabulary_version TEXT NOT NULL,
    access_class TEXT NOT NULL,
    refreshed_at TEXT
);
INSERT INTO dataset_catalog VALUES
 ('curated_results','Research Data Engineering','Published screening results from both projects','1.0','internal',NULL),
 ('document_evidence','Research Informatics','Versioned screening notes with document-level access','1.0','mixed',NULL),
 ('evidence_search','Research Informatics','On-demand search over authorized notes and curated links','1.0','mixed',NULL);
CREATE TABLE dataset_dependency (
    upstream TEXT NOT NULL REFERENCES dataset_catalog,
    downstream TEXT NOT NULL REFERENCES dataset_catalog,
    PRIMARY KEY(upstream,downstream)
);
INSERT INTO dataset_dependency VALUES ('curated_results','document_evidence'),('document_evidence','evidence_search');
CREATE TABLE document_result (
    document_id TEXT NOT NULL, version INTEGER NOT NULL, result_id TEXT NOT NULL,
    source_record_id TEXT NOT NULL REFERENCES source_record,
    measurement_json TEXT NOT NULL,
    PRIMARY KEY(document_id,version,result_id),
    FOREIGN KEY(document_id,version) REFERENCES document
);
