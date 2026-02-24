from pydantic import BaseModel, model_validator, ConfigDict, field_validator
from typing import List, Optional


class Issue(BaseModel):
    id: str
    work_item_type: Optional[str] = None
    title: str
    repro_steps: str
    module: Optional[str] = None
    source: str = "uploaded_csv"


class BugReportInput(BaseModel):
    id: Optional[int | str] = None
    title: str
    repro_steps: str
    module: Optional[str] = None


class CandidateMatch(BaseModel):
    id: str
    title: str
    module: Optional[str] = None
    repro_steps: str
    score_pct: float


class RowDecision(BaseModel):
    model_config = ConfigDict(strict=False)
    input_id: Optional[str] = None
    result: str
    exact_match_id: Optional[str] = None
    matches: List[CandidateMatch] = []
    llm_confirmed_duplicate: bool = False
    llm_best_match_id: Optional[str] = None
    dedup_within_sheet: bool = False
    duplicate_of_row_index: Optional[int] = None


class VectorStoreStatus(BaseModel):
    index_built: bool
    total_issues: int
    last_updated_utc: str
    upload_events: int


class UploadEvent(BaseModel):
    timestamp_utc: str
    file_name: str
    issues_added: int


class JsonIssue(BaseModel):
    issue_id: str
    title: str
    repro_steps: str
    module: Optional[str] = None
    source: str = "json_api"
    work_item_type: Optional[str] = None
