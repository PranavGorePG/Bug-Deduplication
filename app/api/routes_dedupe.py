from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.services.vector_store_service import VectorStoreService
from app.services.bug_analyzer import BugAnalyzer
from app.repositories.excel_repository import ExcelRepository
from app.models.schemas import RowDecision, BugReportInput
from typing import List
import pandas as pd
from io import BytesIO

router = APIRouter(tags=["Deduplication"])
vector_store_service = VectorStoreService()
bug_analyzer = BugAnalyzer()
excel_repository = ExcelRepository()


@router.post("/process-excel")
async def process_excel(file: UploadFile = File(...)):
    # Check if index is built and non-empty
    status = vector_store_service.get_status()
    if not status.index_built or status.total_issues == 0:
        raise HTTPException(
            status_code=400, detail="Vector store is empty. Please upload existing issues first.")

    try:
        # Read Excel
        contents = await file.read()
        file_obj = BytesIO(contents)
        df = excel_repository.read_excel(file_obj)

        # Validate required columns
        required = ["Title", "Repro Steps"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400, detail=f"Missing required columns in Excel: {missing}")

        # Convert DF to list of dicts for BugAnalyzer
        # Replace NaN with empty string
        rows = df.fillna("").to_dict(orient="records")

        # Analyze
        decisions = bug_analyzer.analyze_sheet(rows)

        # Prepare results for Excel appending
        results_for_excel = []
        for d in decisions:
            # Result string
            result_str = d.result

            # Matching IDs
            matches_str = "NA"
            if d.matches:
                lines = []
                for m in d.matches:
                    repro_preview = m.repro_steps[:50] + \
                        "..." if len(m.repro_steps) > 50 else m.repro_steps
                    lines.append(
                        f"{m.id} ({m.score_pct:.1f}%) | {repro_preview}")
                matches_str = "\\n".join(lines)

            # Match Confidence
            confidence = "NA"
            if "Exact found" in d.result:
                confidence = "High"
            elif "Similar Found" in d.result:
                confidence = "Medium"
            elif "Appended above" in d.result:
                confidence = "NA"  # As per requirement "Not Found or in-sheet duplicate -> NA"
            elif "Not Found" in d.result:
                confidence = "NA"

            results_for_excel.append({
                "result": result_str,
                "matching_ids": matches_str,
                "match_confidence": confidence
            })

        # Append to Excel
        # Reset file pointer for reading again (or we could pass the df but repository expects file content to preserve formatting)
        # Actually Repository implementation loads workbook from binary content.
        # We need original content. 'contents' variable has it.
        file_obj_orig = BytesIO(contents)
        output_io = excel_repository.append_results_to_excel(
            file_obj_orig, results_for_excel)

        filename = f"processed_{file.filename}"

        return StreamingResponse(
            output_io,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/process-json", response_model=List[RowDecision])
async def process_json(bug_reports: List[BugReportInput]):
    # Check if index is built and non-empty
    status = vector_store_service.get_status()
    if not status.index_built or status.total_issues == 0:
        raise HTTPException(
            status_code=400, detail="Vector store is empty. Please upload existing issues first.")

    try:
        # Convert Pydantic models to list of dicts for BugAnalyzer
        # BugAnalyzer expects keys: "Title", "Repro Steps", "Module" (optional)
        rows = []
        input_ids = []
        for report in bug_reports:
            row = {
                "Title": report.title,
                "Repro Steps": report.repro_steps,
                "Module": report.module
            }
            rows.append(row)
            input_ids.append(str(report.id) if hasattr(
                report, 'id') else str(len(rows)))

        # Analyze
        decisions = bug_analyzer.analyze_sheet(rows, input_ids=input_ids)

        return decisions

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}")
