from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Numbers(StrictModel):
    values: list[Annotated[int, Field(ge=-10**9, le=10**9)]] = Field(min_length=1, max_length=1000)


class TrainingData(StrictModel):
    x: list[Annotated[float, Field(ge=-10**6, le=10**6, allow_inf_nan=False)]] = Field(min_length=2, max_length=1000)
    y: list[Annotated[float, Field(ge=-10**6, le=10**6, allow_inf_nan=False)]] = Field(min_length=2, max_length=1000)

    @model_validator(mode="after")
    def paired(self):
        if len(self.x) != len(self.y) or len(set(self.x)) < 2:
            raise ValueError("Training requires paired x/y samples and varying x")
        return self


BERT_CPUS_PER_WORKER = 2


class BertTinyParams(StrictModel):
    """bert_tiny_ddp_v1: fine-tune BERT-tiny (SST-2 sentiment) across `workers` computers, one per computer."""
    examples: int = Field(default=480, ge=32, le=2000)
    steps: int = Field(default=100, ge=1, le=2000)
    workers: int = Field(default=2, ge=1, le=8)
    global_batch: int = Field(default=96, ge=8, le=512)
    max_length: int = Field(default=128, ge=16, le=256)
    # 1 = average gradients every step; N = average the model every N steps (far less network traffic).
    sync_every: int = Field(default=50, ge=1, le=500)
    eval_examples: int = Field(default=200, ge=16, le=872)

    @model_validator(mode="after")
    def consistent(self):
        if self.global_batch < self.workers:
            raise ValueError("global_batch must be at least the number of workers")
        return self


def input_model(template_id):
    if template_id == "bert_tiny_ddp_v1":
        return BertTinyParams
    return TrainingData if template_id == "linear_regression_v1" else Numbers


class Requirements(StrictModel):
    cpu_cores: int = Field(default=1, ge=1, le=4)
    ram_gb: float = Field(default=0.125, ge=0.0625, le=4)
    gpus: Literal[0] = 0
    execution_class: Literal["trusted_cpu"] = "trusted_cpu"
    max_runtime_seconds: int = Field(default=60, ge=1, le=1800)


class Submission(StrictModel):
    template_id: Literal["sum_numbers_v1", "linear_regression_v1", "bert_tiny_ddp_v1"]
    parameters: Numbers | TrainingData | BertTinyParams | None = None
    input_artifact_id: str | None = Field(default=None, pattern=r"^[0-9a-f-]{36}$")
    requirements: Requirements = Field(default_factory=Requirements)
    idempotency_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")

    @model_validator(mode="after")
    def one_input(self):
        if (self.parameters is None) == (self.input_artifact_id is None):
            raise ValueError("Provide exactly one of parameters or input_artifact_id")
        if self.parameters is not None and not isinstance(self.parameters, input_model(self.template_id)):
            raise ValueError("Input does not match selected pipeline")
        if self.template_id != "bert_tiny_ddp_v1" and self.requirements.max_runtime_seconds > 300:
            raise ValueError("Only bert_tiny_ddp_v1 may run longer than 300 seconds")
        return self
