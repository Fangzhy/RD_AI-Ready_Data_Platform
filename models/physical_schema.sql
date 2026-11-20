PRAGMA foreign_keys=ON;

CREATE TABLE research_project (
    project_id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL
);
CREATE TABLE experiment (
    experiment_id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT NOT NULL REFERENCES research_project,
    title TEXT NOT NULL
);
CREATE TABLE compound (
    compound_id TEXT PRIMARY KEY NOT NULL,
    label TEXT NOT NULL
);
CREATE TABLE sample (
    sample_id TEXT PRIMARY KEY NOT NULL,
    experiment_id TEXT NOT NULL REFERENCES experiment,
    compound_id TEXT NOT NULL REFERENCES compound,
    UNIQUE (sample_id, experiment_id)
);
CREATE TABLE assay (
    assay_id TEXT PRIMARY KEY NOT NULL,
    preferred_term TEXT UNIQUE NOT NULL,
    canonical_unit TEXT NOT NULL
);
CREATE TABLE assay_run (
    run_id TEXT PRIMARY KEY NOT NULL,
    experiment_id TEXT NOT NULL REFERENCES experiment,
    assay_id TEXT NOT NULL REFERENCES assay,
    UNIQUE (run_id, experiment_id)
);
CREATE TABLE source_record (
    source_record_id TEXT PRIMARY KEY NOT NULL,
    source_system TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    row_number INTEGER NOT NULL CHECK (row_number > 0),
    raw_json TEXT NOT NULL,
    UNIQUE (source_system, batch_id, row_number)
);
CREATE TRIGGER preserve_source_update BEFORE UPDATE ON source_record
BEGIN SELECT RAISE(ABORT, 'Immutable source record'); END;
CREATE TRIGGER preserve_source_delete BEFORE DELETE ON source_record
BEGIN SELECT RAISE(ABORT, 'Immutable source record'); END;

CREATE TABLE assay_result (
    result_id TEXT PRIMARY KEY NOT NULL,
    experiment_id TEXT NOT NULL REFERENCES experiment,
    sample_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    result_value REAL NOT NULL CHECK (result_value >= 0),
    result_unit TEXT NOT NULL,
    original_value TEXT NOT NULL,
    original_unit TEXT NOT NULL,
    source_record_id TEXT UNIQUE NOT NULL REFERENCES source_record,
    mapping_version TEXT NOT NULL,
    FOREIGN KEY (sample_id, experiment_id) REFERENCES sample (sample_id, experiment_id),
    FOREIGN KEY (run_id, experiment_id) REFERENCES assay_run (run_id, experiment_id)
);
CREATE TABLE document (
    document_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    experiment_id TEXT NOT NULL REFERENCES experiment,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    access_class TEXT NOT NULL CHECK (access_class IN ('public','restricted')),
    lifecycle TEXT NOT NULL CHECK (lifecycle IN ('current','superseded')),
    PRIMARY KEY (document_id, version)
);
CREATE UNIQUE INDEX current_document ON document (document_id) WHERE lifecycle='current';
CREATE TABLE compound_crosswalk (
    source_system TEXT NOT NULL,
    local_id TEXT NOT NULL,
    compound_id TEXT NOT NULL REFERENCES compound,
    PRIMARY KEY (source_system, local_id)
);
CREATE TABLE experiment_crosswalk (
    source_system TEXT NOT NULL,
    local_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL REFERENCES experiment,
    PRIMARY KEY (source_system, local_id)
);
CREATE TABLE sample_crosswalk (
    source_system TEXT NOT NULL,
    local_id TEXT NOT NULL,
    sample_id TEXT NOT NULL REFERENCES sample,
    PRIMARY KEY (source_system, local_id)
);
CREATE INDEX experiments_by_project ON experiment(project_id);
CREATE INDEX results_by_sample ON assay_result(sample_id);
CREATE INDEX documents_by_experiment ON document(experiment_id);
CREATE VIEW curated_results AS
SELECT r.result_id, e.project_id, e.experiment_id, s.sample_id, c.compound_id,
       a.assay_id, a.preferred_term AS assay_name, r.run_id, r.result_value, r.result_unit,
       r.original_value, r.original_unit, src.source_system, r.source_record_id, r.mapping_version
FROM assay_result r
JOIN assay_run ar ON ar.run_id=r.run_id
JOIN assay a ON a.assay_id=ar.assay_id
JOIN sample s ON s.sample_id=r.sample_id
JOIN compound c ON c.compound_id=s.compound_id
JOIN experiment e ON e.experiment_id=r.experiment_id
JOIN source_record src ON src.source_record_id=r.source_record_id;
