"""Scientific requirements and their implementation in the screening model."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Requirement:
    need: str
    entity: str
    field: str
    definition: str
    relationship: str
    quality_rule: str
    decision: str


REQUIREMENTS = (
    Requirement(
        "Compare binding measurements reported in different units.",
        "assay_result", "result_unit",
        "The unit of the curated numeric result after an approved conversion.",
        "The result references an assay run by run_id. The run references the assay whose canonical_unit governs the measurement.",
        "Binding accepts nM or µM (CSV code uM). Multiply uM by 1,000 to publish nM. Quarantine missing or incompatible units.",
        "Store the canonical value and unit beside original_value and original_unit so a scientist can reproduce the conversion.",
    ),
    Requirement(
        "Trace a measurement to the sample actually tested.",
        "assay_result", "sample_id",
        "The registered sample measured in this assay run.",
        "(sample_id, experiment_id) references the same pair in sample. Each sample has one registered compound.",
        "Resolve the local IDs through the source crosswalks. Reject unknown references or a sample registered to a different compound or experiment.",
        "Use stable sample IDs and a composite foreign key to preserve experiment membership across source systems.",
    ),
    Requirement(
        "Count each observation once when feeds are reloaded.",
        "assay_result", "result_id",
        "The canonical identifier for one source observation.",
        "result_id is the primary key. source_record_id uniquely links a curated result to its immutable input row.",
        "Reject repeated observation IDs within a batch and collisions with another published batch from the same source.",
        "Namespace local observation IDs by source. Reloading the same batch replaces its current results and adds a lineage event.",
    ),
    Requirement(
        "Reconstruct how a scientist’s original reading was interpreted.",
        "source_record", "source_record_id",
        "A stable identifier derived from source system, batch, data-row number, and original fields.",
        "lineage_event links a source row to an ingestion_run and its mapping version.",
        "Preserve raw fields for every decision, including rejection. A source and mapping version must identify one set of assignments.",
        "Keep input rows immutable and retain run-specific decisions so a later mapping cannot erase an earlier interpretation.",
    ),
)
