CREATE TABLE mapping_profile (
    source_system TEXT NOT NULL, mapping_version TEXT NOT NULL, profile_json TEXT NOT NULL,
    PRIMARY KEY(source_system, mapping_version)
);
CREATE TABLE quality_decision (
    source_record_id TEXT PRIMARY KEY NOT NULL REFERENCES source_record,
    source_system TEXT NOT NULL,
    mapping_version TEXT NOT NULL,
    quality_status TEXT NOT NULL CHECK(quality_status IN ('accepted','corrected','rejected')),
    reasons TEXT NOT NULL,
    audit_json TEXT NOT NULL,
    FOREIGN KEY(source_system, mapping_version) REFERENCES mapping_profile
);
CREATE TABLE quarantine (
    source_record_id TEXT PRIMARY KEY NOT NULL REFERENCES quality_decision,
    reasons TEXT NOT NULL,
    recommendation TEXT NOT NULL
);
