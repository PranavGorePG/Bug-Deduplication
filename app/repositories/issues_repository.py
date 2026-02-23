import pandas as pd
from io import BytesIO
from typing import List, BinaryIO
from app.models.schemas import Issue
from app.core.constants import REQUIRED_COLUMNS

class IssuesRepository:
    def parse_file(self, file_content: BinaryIO, file_name: str) -> List[Issue]:
        
        if file_name.endswith('.csv'):
            df = pd.read_csv(file_content)
        elif file_name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_content)
        else:
            raise ValueError("Unsupported file format. Please upload CSV or XLSX.")

        # Normalize headers: strip whitespace
        df.columns = df.columns.astype(str).str.strip()
        
        # Check required columns
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        
        # Special handling: if "ID" or "Title" missing -> error
        critical_missing = []
        if "ID" not in df.columns: critical_missing.append("ID")
        if "Title" not in df.columns: critical_missing.append("Title")
        
        if critical_missing:
            raise ValueError(f"Missing critical columns: {critical_missing}")

        # Other missing columns -> log warning, fill with empty
        # For now, just fill empty
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = "" # Fill missing column with empty string
        
        issues = []
        for _, row in df.iterrows():
            # Handle potential NaN
            issue_data = {}
            for col in REQUIRED_COLUMNS:
                val = row.get(col)
                if pd.isna(val):
                    issue_data[col] = ""
                else:
                    issue_data[col] = str(val).strip()
            
            # Additional fields mapping if needed, but we stick to required for now
            # Convert keys to lowercase snake_case for Pydantic model
            # "Work Item Type" -> "work_item_type"
            model_data = {
                "id": issue_data["ID"],
                "work_item_type": issue_data["Work Item Type"],
                "title": issue_data["Title"],
                "repro_steps": issue_data["Repro Steps"],
                "module": issue_data["Module"],
                "source": "uploaded_csv"
            }
            issues.append(Issue(**model_data))
            
        return issues
