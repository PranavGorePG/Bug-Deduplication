from typing import List  # Add this import
from app.models.schemas import Issue  # Add this import
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.services.vector_store_service import VectorStoreService
from app.repositories.issues_repository import IssuesRepository
from app.models.schemas import VectorStoreStatus
from typing import Dict, Any

router = APIRouter(prefix="/vector-store", tags=["Vector Store"])
vector_store_service = VectorStoreService()
issues_repository = IssuesRepository()


@router.post("/append", response_model=Dict)
async def append_issues(file: UploadFile = File(...)):
    try:

        contents = await file.read()
        file.file.seek(0)

        # Parse issues
        issues = issues_repository.parse_file(file.file, file.filename)

        # Append to vector store
        added_count = vector_store_service.append_issues(issues)

        # Record upload
        vector_store_service.record_upload(file.filename, added_count)

        # Get updated status
        status = vector_store_service.get_status()

        return {
            "file_name": file.filename,
            "issues_added": added_count,
            "total_issues": status.total_issues,
            "upload_events": status.upload_events,
            "last_updated_utc": status.last_updated_utc
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/status", response_model=VectorStoreStatus)
async def get_status():
    return vector_store_service.get_status()


@router.post("/reset", response_model=VectorStoreStatus)
async def reset_store():
    vector_store_service.reset_store()
    return vector_store_service.get_status()


# Add after existing routes

@router.post("/append-json", response_model=Dict[str, Any])
async def append_json_issues(issues: List[Issue]):
    """
    Append issues directly from JSON.
    """
    try:
        print(f"📥 Received {len(issues)} JSON issues")
        for issue in issues[:2]:  # Debug first 2
            print(f"  ID: {issue.id}, Title: {issue.title[:50]}...")

        added_count = vector_store_service.append_issues(issues)
        print(f"✅ Added {added_count} new issues")

        vector_store_service.record_upload("json_upload", added_count)
        status = vector_store_service.get_status()

        return {
            "issues_added": added_count,
            "total_issues": status.total_issues,
            "upload_events": status.upload_events,
            "last_updated_utc": status.last_updated_utc
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}")
