import asyncio
from contextlib import asynccontextmanager
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.services.vector_store_service import VectorStoreService
from app.services.bug_analyzer import BugAnalyzer
from app.repositories.excel_repository import ExcelRepository
from app.models.schemas import RowDecision, BugReportInput, ProcessRequest
from typing import List
import pandas as pd
from io import BytesIO
from app.core.logging import logger

process_json_lock = asyncio.Lock()

router = APIRouter(tags=["Deduplication"])
# vector_store_service = VectorStoreService()
# bug_analyzer = BugAnalyzer()

vector_store_service = VectorStoreService()
bug_analyzer = BugAnalyzer()
bug_analyzer.vector_store_service = vector_store_service


excel_repository = ExcelRepository()


@router.post("/process-excel")
async def process_excel(
    file: UploadFile = File(...),
    product_name: str = Query(..., description="Product collection name")
):
    """Process new Excel bugs against product collection"""
    try:
        # Set product collection
        vector_store_service.set_collection(product_name)
        status = vector_store_service.get_collection_status(
            vector_store_service.default_collection)

        if not status.index_built or status.total_issues == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Collection '{product_name}' empty. Upload reference bugs first."
            )

        # Read Excel
        contents = await file.read()
        file_obj = BytesIO(contents)
        df = excel_repository.read_excel(file_obj)

        # Validate columns
        required = ["Title", "Repro Steps"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {missing}"
            )

        # Convert to dicts (add product)
        rows = df.fillna("").to_dict(orient="records")
        for row in rows:
            row["product"] = product_name

        logger.info(f"Processing {len(rows)} Excel rows for {product_name}")

        # Analyze against product collection
        decisions = bug_analyzer.analyze_sheet(rows)

        # Prepare Excel results
        results_for_excel = []
        for d in decisions:
            result_str = d.result
            matches_str = "NA"

            if d.matches:
                lines = []
                for m in d.matches:
                    repro_preview = m.repro_steps[:50] + \
                        "..." if len(m.repro_steps) > 50 else m.repro_steps
                    lines.append(
                        f"{m.id} ({m.score_pct:.1f}%) | {repro_preview}")
                matches_str = "\\n".join(lines)

            confidence = "NA"
            if "Exact found" in d.result:
                confidence = "High"
            elif "Similar Found" in d.result:
                confidence = "Medium"

            results_for_excel.append({
                "result": result_str,
                "matching_ids": matches_str,
                "match_confidence": confidence
            })

        # Append results to Excel
        file_obj_orig = BytesIO(contents)
        output_io = excel_repository.append_results_to_excel(
            file_obj_orig, results_for_excel)

        filename = f"processed_{product_name}_{file.filename}"

        return StreamingResponse(
            output_io,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel process error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process-json", response_model=List[RowDecision])
async def process_json(request: ProcessRequest):
    async with process_json_lock:
        logger.info("🔒 Lock acquired - processing JSON request")

        product_name = request.product_name
        vector_store_service.set_collection(product_name)
        status = vector_store_service.get_collection_status(
            vector_store_service.default_collection)
        if not status.index_built or status.total_issues == 0:
            raise HTTPException(
                status_code=400, detail=f"Collection '{product_name}' empty. Upload reference bugs first.")

        try:
            rows = []
            input_ids = []
            for i, report in enumerate(request.bug_reports):
                row = {
                    "Title": report.title,
                    "Repro Steps": report.repro_steps,
                    "Module": getattr(report, 'module', '') or '',
                    "product": product_name
                }
                rows.append(row)
                input_ids.append(str(getattr(report, 'id', i)))

            logger.info(f"Processing {len(rows)} JSON bugs for {product_name}")
            decisions = bug_analyzer.analyze_sheet(
                rows, input_ids=input_ids, collection_name=product_name)

            logger.info(
                f"✅ JSON processing finished for {product_name} - releasing lock")
            return decisions

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"JSON process error: {e}")
            raise HTTPException(
                status_code=500, detail=f"Analysis failed: {str(e)}")
