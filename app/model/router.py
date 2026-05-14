"""
router.py
Cactus-track: Intelligent model routing.
"""

from enum import Enum
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "app_config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)


class ModelTier(Enum):
    FAST_TEXT = "gemma4:2b"
    FULL_TEXT = "gemma4:latest"
    VISION = "gemma4:latest"


class TaskType(Enum):
    IMAGE_EXTRACTION = "image_extraction"
    PDF_STRUCTURING = "pdf_structuring"
    SPANISH_EXPLANATION = "spanish_explanation"
    FOLLOWUP_QUESTION = "followup_question"
    DEMAND_LETTER = "demand_letter"


class ModelRouter:
    ROUTING_TABLE = {
        TaskType.IMAGE_EXTRACTION: ModelTier.VISION,
        TaskType.PDF_STRUCTURING: ModelTier.FULL_TEXT,
        TaskType.SPANISH_EXPLANATION: ModelTier.FULL_TEXT,
        TaskType.FOLLOWUP_QUESTION: ModelTier.FAST_TEXT,
        TaskType.DEMAND_LETTER: ModelTier.FULL_TEXT,
    }

    def route(self, task_type: TaskType) -> str:
        tier = self.ROUTING_TABLE.get(task_type, ModelTier.FULL_TEXT)
        print(f"Routing {task_type.value} → {tier.value}")
        return tier.value

    def get_task_type(self, input_type: str, is_followup: bool = False) -> TaskType:
        if is_followup:
            return TaskType.FOLLOWUP_QUESTION
        routing = CONFIG["model_routing"]
        if input_type in routing["use_vision_for"]:
            return TaskType.IMAGE_EXTRACTION
        return TaskType.PDF_STRUCTURING