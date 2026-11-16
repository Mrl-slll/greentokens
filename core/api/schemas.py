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


def input_model(template_id):
    return TrainingData if template_id == "linear_regression_v1" else Numbers


class Requirements(StrictModel):
    cpu_cores: int = Field(default=1, ge=1, le=4)
    ram_gb: float = Field(default=0.125, ge=0.0625, le=4)
    gpus: Literal[0] = 0
    execution_class: Literal["trusted_cpu"] = "trusted_cpu"
    max_runtime_seconds: int = Field(default=60, ge=1, le=300)


class Submission(StrictModel):
    template_id: Literal["sum_numbers_v1", "linear_regression_v1"]
    parameters: Numbers | TrainingData | None = None
    input_artifact_id: str | None = Field(default=None, pattern=r"^[0-9a-f-]{36}$")
    requirements: Requirements = Field(default_factory=Requirements)
    idempotency_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")

    @model_validator(mode="after")
    def one_input(self):
        if (self.parameters is None) == (self.input_artifact_id is None):
            raise ValueError("Provide exactly one of parameters or input_artifact_id")
        if self.parameters is not None and not isinstance(self.parameters, input_model(self.template_id)):
            raise ValueError("Input does not match selected pipeline")
        return self
