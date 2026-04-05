import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .project import Project
from .export_params import ExportParams


@dataclass
class ExportTask:
    project: Project
    output_path: Path
    quality: int = 23   # CRF 值，0=无损，51=最差，默认 23
    params: ExportParams = field(default_factory=ExportParams)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "pending"   # pending / running / done / failed / cancelled
    progress: float = 0.0
    error: Optional[str] = None
