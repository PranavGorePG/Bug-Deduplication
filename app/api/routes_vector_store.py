from typing import List, Dict, Any
from io import BytesIO
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.services.vector_store_service import VectorStoreService
from app.repositories.issues_repository import IssuesRepository
from app.models.schemas import VectorStoreStatus, Issue, ProcessRequest
from app.core.logging import logger

router = APIRouter(prefix="/vector-store", tags=["Vector Store"])
vector_store_service = VectorStoreService()
issues_repository = IssuesRepository()


@router.post("/collection/create")
async def create_collection(product_name: str = Query(..., description="Product name for collection")):
    """Create product-specific collection"""
    try:
        collection_name = vector_store_service.create_collection(product_name)
        status = vector_store_service.get_collection_status(collection_name)
        return {
            "success": True,
            "collection_name": collection_name,
            "status": status
        }
    except Exception as e:
        logger.error(f"Create collection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collection/{product_name}")
async def delete_collection(product_name: str):
    """Delete product-specific collection"""
    try:
        vector_store_service.delete_collection(product_name)
        return {"success": True, "deleted": product_name}
    except Exception as e:
        logger.error(f"Delete collection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/{product_name}/status", response_model=VectorStoreStatus)
async def get_collection_status(product_name: str):
    """Status for specific collection"""
    return vector_store_service.get_collection_status(product_name)


@router.post("/append")
async def append_issues(
    file: UploadFile = File(...),
    product_name: str = Query(..., description="Product name for collection")
):
    """Append Excel/CSV issues to product collection"""
    try:
        # ✅ 1. Set collection FIRST
        vector_store_service.set_collection(product_name)

        # ✅ 2. Read file contents
        contents = await file.read()
        file_obj = BytesIO(contents)

        # ✅ 3. Parse into Issue objects (product="" default from parse_file fix)
        issues = issues_repository.parse_file(file_obj, file.filename)

        # ✅ 4. Override product from query param
        for issue in issues:
            issue.product = product_name

        # ✅ 5. Append to Qdrant
        added_count = vector_store_service.append_issues(issues)
        status = vector_store_service.get_collection_status(
            vector_store_service.default_collection)

        return {
            "success": True,
            "product_name": product_name,
            "file_name": file.filename,
            "issues_added": added_count,
            "status": status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Append issues error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/append-json")
async def append_json_issues(issues: List[Issue]):
    """
    Append JSON issues to their respective product collections.
    - Each issue's `product` field determines collection name
    - Auto-sets collection per product (mixed products OK)
    """
    if not issues:
        raise HTTPException(status_code=400, detail="No issues provided")

    # Group by product and process
    products = {}
    for issue in issues:
        product = issue.product
        if not product:
            raise HTTPException(
                status_code=400, detail="Each issue must have 'product'")

        if product not in products:
            products[product] = []
        products[product].append(issue)

    results = {}
    for product, product_issues in products.items():
        try:
            vector_store_service.set_collection(product)
            added_count = vector_store_service.append_issues(product_issues)
            status = vector_store_service.get_collection_status(
                vector_store_service.default_collection)

            results[product] = {
                "issues_added": added_count,
                "status": status
            }
            logger.info(f"✅ Added {added_count} issues to {product}")
        except Exception as e:
            results[product] = {"error": str(e)}

    return {
        "success": True,
        "summary": results
    }


@router.get("/status")
async def get_default_status():
    """Legacy: default collection status"""
    return vector_store_service.get_status()


@router.post("/reset")
async def reset_default_store():
    """Legacy: reset default (use delete_collection instead)"""
    if vector_store_service.default_collection:
        vector_store_service.delete_collection(
            vector_store_service.default_collection)
    return vector_store_service.get_status()


@router.get("/collections", response_model=List[Dict[str, Any]])
async def list_collections():
    """
    List all Qdrant collections.
    """
    try:
        return vector_store_service.list_collections()
    except Exception as e:
        logger.error(f"List collections error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to list collections")


@router.post("/collection/{product_name}/clear")
async def clear_collection(product_name: str):
    """
    Clear all vectors/data from a collection without deleting the collection itself.
    """
    try:
        cleared_count = vector_store_service.clear_collection(product_name)
        return {
            "success": True,
            "collection": product_name,
            "points_deleted": cleared_count
        }
    except Exception as e:
        logger.error(f"Clear collection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
