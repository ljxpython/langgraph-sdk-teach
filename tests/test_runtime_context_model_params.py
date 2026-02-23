from __future__ import annotations

from graph_src.agent import RuntimeOptions, apply_model_runtime_params, build_runtime_options


class _DummyModel:
    def __init__(self) -> None:
        self.bound_kwargs: dict[str, object] | None = None

    def bind(self, **kwargs: object) -> "_DummyModel":
        self.bound_kwargs = kwargs
        return self


def test_build_runtime_options_reads_model_params_from_context() -> None:
    options = build_runtime_options(
        config=None,
        runtime_context={
            "temperature": 0.3,
            "top_p": 0.85,
            "max_tokens": 512,
            "system_prompt": "ctx prompt",
            "model_provider": "glm4",
        },
    )
    assert isinstance(options, RuntimeOptions)
    assert options.temperature == 0.3
    assert options.top_p == 0.85
    assert options.max_tokens == 512
    assert options.system_prompt == "ctx prompt"


def test_apply_model_runtime_params_binds_expected_kwargs() -> None:
    model = _DummyModel()
    options = RuntimeOptions(temperature=0.7, top_p=0.9, max_tokens=1024)
    result = apply_model_runtime_params(model, options)
    assert result is model
    assert model.bound_kwargs == {"temperature": 0.7, "max_tokens": 1024, "top_p": 0.9}
