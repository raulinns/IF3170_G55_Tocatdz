from __future__ import annotations

from dataclasses import dataclass

from algorithms.genetic_algorithm.gen_algorithm import required_evaluations
from search.run import AlgorithmKind, RunConfig
from .config import ExperimentConfig


@dataclass(frozen=True, slots=True)
class ExperimentRunSpec:
    case_id: str
    group_id: str
    group_label: str
    config: RunConfig


PROTOCOLS = (
    "specification",
    "non_ga",
    "ga_population_sweep",
    "ga_generation_sweep",
    "fairness",
    "hc_comparison",
)

_HC_ALGORITHMS = (
    AlgorithmKind.STEEPEST_ASCENT,
    AlgorithmKind.SIDEWAYS,
    AlgorithmKind.STOCHASTIC,
    AlgorithmKind.RANDOM_RESTART,
)


def _spec(
    algorithm: AlgorithmKind,
    seed: int,
    objective,
    budget: int,
    *,
    parameters: dict | None = None,
) -> RunConfig:
    return RunConfig(
        algorithm=algorithm,
        objective=objective,
        seed=seed,
        max_evaluations=budget,
        **(parameters or {}),
    )


def build_run_specs(config: ExperimentConfig) -> list[ExperimentRunSpec]:
    """Expand a named protocol into deterministic, auditable runs."""
    protocol = "non_ga" if config.protocol == "specification" else config.protocol
    runs: list[ExperimentRunSpec] = []

    def add(group_id: str, label: str, run_config: RunConfig) -> None:
        case_id = f"{group_id}-seed-{run_config.seed}"
        if any(run.case_id == case_id for run in runs):
            case_id = f"{case_id}-run-{len(runs) + 1}"
        runs.append(ExperimentRunSpec(case_id, group_id, label, run_config))

    if protocol in {"non_ga", "hc_comparison"}:
        algorithms = _HC_ALGORITHMS if protocol == "hc_comparison" else (
            *_HC_ALGORITHMS,
            AlgorithmKind.SIMULATED_ANNEALING,
        )
        for algorithm in algorithms:
            group_id = algorithm.value
            for seed in config.seeds:
                add(
                    group_id,
                    algorithm.value,
                    _spec(algorithm, seed, config.objective, config.max_evaluations),
                )
    elif protocol == "ga_population_sweep":
        for population in (20, 50, 100):
            generations = 100
            budget = required_evaluations(population, generations)
            for seed in config.seeds:
                group_id = f"population-{population}"
                add(
                    group_id,
                    f"Population {population}",
                    _spec(
                        AlgorithmKind.GENETIC_ALGORITHM,
                        seed,
                        config.objective,
                        budget,
                        parameters={"population_size": population, "generations": generations},
                    ),
                )
    elif protocol == "ga_generation_sweep":
        population = 50
        for generations in (50, 100, 200):
            budget = required_evaluations(population, generations)
            for seed in config.seeds:
                group_id = f"generations-{generations}"
                add(
                    group_id,
                    f"Generations {generations}",
                    _spec(
                        AlgorithmKind.GENETIC_ALGORITHM,
                        seed,
                        config.objective,
                        budget,
                        parameters={"population_size": population, "generations": generations},
                    ),
                )
    elif protocol == "fairness":
        for algorithm in (
            AlgorithmKind.STEEPEST_ASCENT,
            AlgorithmKind.SIMULATED_ANNEALING,
            AlgorithmKind.GENETIC_ALGORITHM,
        ):
            for seed in config.seeds:
                add(
                    algorithm.value,
                    algorithm.value,
                    _spec(algorithm, seed, config.objective, 50_000),
                )
    else:
        raise ValueError(f"unknown experiment protocol: {config.protocol}")
    return runs


__all__ = ["ExperimentRunSpec", "PROTOCOLS", "build_run_specs"]
