from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from ...domain.model import Orientation, Placement, Problem, State
from ...domain.packing import candidate_anchors, try_place
from ...search.moves import rotated_orientation
from ...search.run import (
    AlgorithmKind,
    RunCancelled,
    RunConfig,
    RunContext,
    SearchResult,
    StopReason,
    TracePoint,
)


@dataclass(frozen=True, slots=True)
class Chromosome:
    package_order: tuple[str, ...]
    orientations: tuple[Orientation, ...]
    destinations: tuple[str | None, ...]


@dataclass(frozen=True, slots=True)
class Individual:
    chromosome: Chromosome
    state: State
    fitness: float


def validate_chromosome(problem: Problem, chromosome: Chromosome) -> None:
    package_ids = {package.id for package in problem.packages}
    count = len(problem.packages)
    if (
        len(chromosome.package_order) != count
        or len(chromosome.orientations) != count
        or len(chromosome.destinations) != count
        or set(chromosome.package_order) != package_ids
    ):
        raise ValueError("chromosome must contain each package exactly once")
    if any(not isinstance(item, Orientation) for item in chromosome.orientations):
        raise ValueError("chromosome contains an invalid orientation")
    truck_ids = {truck.id for truck in problem.trucks}
    if any(
        destination is not None and destination not in truck_ids
        for destination in chromosome.destinations
    ):
        raise ValueError("chromosome contains an unknown truck")


def decode_chromosome(problem: Problem, chromosome: Chromosome) -> State:
    validate_chromosome(problem, chromosome)
    state = State.all_outside(problem)
    for package_id, orientation, preferred_truck in zip(
        chromosome.package_order,
        chromosome.orientations,
        chromosome.destinations,
    ):
        if preferred_truck is None:
            state = state.replace(Placement(package_id, orientation=orientation))
            continue

        truck_ids = (preferred_truck,) + tuple(
            truck.id for truck in problem.trucks if truck.id != preferred_truck
        )
        placed = None
        for truck_id in truck_ids:
            for anchor in candidate_anchors(problem, state, truck_id):
                placed = try_place(
                    problem, state, package_id, truck_id, anchor, orientation
                )
                if placed is not None:
                    break
            if placed is not None:
                break
        if placed is not None:
            state = placed
        else:
            state = state.replace(Placement(package_id, orientation=orientation))
    return state


def random_chromosome(problem: Problem, rng: random.Random) -> Chromosome:
    package_ids = [package.id for package in problem.packages]
    rng.shuffle(package_ids)
    destinations = [truck.id for truck in problem.trucks] + [None]
    return Chromosome(
        tuple(package_ids),
        tuple(rng.choice(tuple(Orientation)) for _ in package_ids),
        tuple(rng.choice(destinations) for _ in package_ids),
    )


def roulette_select(population: list[Individual], rng: random.Random) -> Individual:
    weights = [individual.fitness for individual in population]
    if any(weight < 0 for weight in weights):
        raise ValueError("roulette selection requires non-negative fitness")
    if sum(weights) == 0:
        return rng.choice(population)
    return rng.choices(population, weights=weights, k=1)[0]


def _order_child(
    first: tuple[str, ...], second: tuple[str, ...], left: int, right: int
) -> tuple[str, ...]:
    child: list[str | None] = [None] * len(first)
    child[left : right + 1] = first[left : right + 1]
    used = set(first[left : right + 1])
    positions = list(range(right + 1, len(first))) + list(range(right + 1))
    remaining = (
        second[index]
        for index in positions
        if second[index] not in used
    )
    for index in positions:
        if child[index] is None:
            child[index] = next(remaining)
    return tuple(package_id for package_id in child if package_id is not None)


def crossover(
    first: Chromosome, second: Chromosome, rng: random.Random
) -> tuple[Chromosome, Chromosome]:
    if set(first.package_order) != set(second.package_order):
        raise ValueError("parents must contain the same packages")
    if len(first.package_order) < 2:
        first_order, second_order = first.package_order, second.package_order
    else:
        left, right = sorted(rng.sample(range(len(first.package_order)), 2))
        first_order = _order_child(first.package_order, second.package_order, left, right)
        second_order = _order_child(second.package_order, first.package_order, left, right)
    first_genes = {
        package_id: (orientation, destination)
        for package_id, orientation, destination in zip(
            first.package_order, first.orientations, first.destinations
        )
    }
    second_genes = {
        package_id: (orientation, destination)
        for package_id, orientation, destination in zip(
            second.package_order, second.orientations, second.destinations
        )
    }
    child_genes: dict[str, tuple[tuple[Orientation, str | None], tuple[Orientation, str | None]]] = {}
    for package_id in first.package_order:
        a_orientation, a_destination = first_genes[package_id]
        b_orientation, b_destination = second_genes[package_id]
        if rng.random() < 0.5:
            first_orientation, second_orientation = a_orientation, b_orientation
        else:
            first_orientation, second_orientation = b_orientation, a_orientation
        if rng.random() < 0.5:
            first_destination, second_destination = a_destination, b_destination
        else:
            first_destination, second_destination = b_destination, a_destination
        child_genes[package_id] = (
            (first_orientation, first_destination),
            (second_orientation, second_destination),
        )

    def make_child(order: tuple[str, ...], child_index: int) -> Chromosome:
        return Chromosome(
            order,
            tuple(child_genes[package_id][child_index][0] for package_id in order),
            tuple(child_genes[package_id][child_index][1] for package_id in order),
        )

    return make_child(first_order, 0), make_child(second_order, 1)


def mutate_chromosome(
    problem: Problem,
    chromosome: Chromosome,
    rng: random.Random,
    probability: float,
) -> Chromosome:
    validate_chromosome(problem, chromosome)
    if not 0 <= probability <= 1:
        raise ValueError("mutation probability must be in [0, 1]")

    order = list(chromosome.package_order)
    orientations = list(chromosome.orientations)
    destinations = list(chromosome.destinations)
    truck_choices = [truck.id for truck in problem.trucks] + [None]
    for package_id in chromosome.package_order:
        if rng.random() >= probability:
            continue
        index = order.index(package_id)
        package = problem.package(package_id)
        current_placement = Placement(package_id, orientation=orientations[index])
        current_dimensions = package.dimensions.oriented(orientations[index])
        new_orientations = []
        seen_dimensions = set()
        for axis in ("x", "y", "z"):
            orientation = rotated_orientation(problem, current_placement, axis)
            dimensions = package.dimensions.oriented(orientation)
            if dimensions != current_dimensions and dimensions not in seen_dimensions:
                seen_dimensions.add(dimensions)
                new_orientations.append(orientation)
        new_destinations = [
            destination
            for destination in truck_choices
            if destination != destinations[index]
        ]
        operations = []
        if len(order) > 1:
            operations.append("swap")
        if new_orientations:
            operations.append("rotate")
        if new_destinations:
            operations.append("reassign")
        if not operations:
            continue

        operation = rng.choice(operations)
        if operation == "swap":
            other_indices = [i for i in range(len(order)) if i != index]
            other = rng.choice(other_indices)
            order[index], order[other] = order[other], order[index]
            orientations[index], orientations[other] = (
                orientations[other], orientations[index]
            )
            destinations[index], destinations[other] = (
                destinations[other], destinations[index]
            )
        elif operation == "rotate":
            orientations[index] = rng.choice(new_orientations)
        else:
            destinations[index] = rng.choice(new_destinations)

    return Chromosome(tuple(order), tuple(orientations), tuple(destinations))


def run_genetic_algorithm(
    problem: Problem,
    config: RunConfig,
    *,
    on_progress: Callable[[TracePoint], None] | None = None,
    context: RunContext | None = None,
) -> SearchResult:
    if config.algorithm is not AlgorithmKind.GENETIC_ALGORITHM:
        raise ValueError("RunConfig algorithm must be genetic_algorithm")
    if not problem.packages or not problem.trucks:
        raise ValueError("GA requires at least one package and one truck")
    if context is not None and (context.problem is not problem or context.config != config):
        raise ValueError("context must belong to the same problem and config")
    if context is not None and context.evaluations:
        raise ValueError("context must not contain previous evaluations")
    if context is not None and on_progress is not None:
        raise ValueError("set on_progress on the context or pass it to this function")
    ctx = context if context is not None else RunContext(problem, config, on_progress=on_progress)

    population: list[Individual] = []
    reason = StopReason.GENERATION_LIMIT
    for _ in range(config.population_size):
        if not ctx.has_budget():
            reason = StopReason.BUDGET_EXHAUSTED
            break
        chromosome = random_chromosome(problem, ctx.rng)
        state = decode_chromosome(problem, chromosome)
        try:
            fitness = ctx.evaluate(state)
        except RunCancelled:
            reason = StopReason.CANCELLED
            break
        population.append(Individual(chromosome, state, fitness))

    if not population:
        raise RunCancelled("GA cancelled before evaluating an initial individual")

    initial = population[ctx.argmax_tie([item.fitness for item in population])]
    current_best = initial
    ctx.record(
        current_best.fitness,
        generation=0,
        population_mean_objective=sum(item.fitness for item in population) / len(population),
    )

    if len(population) == config.population_size:
        for generation in range(1, config.generations + 1):
            if ctx.cancelled:
                reason = StopReason.CANCELLED
                break
            if config.population_size > 1 and not ctx.has_budget():
                reason = StopReason.BUDGET_EXHAUSTED
                break

            elite = population[ctx.argmax_tie([item.fitness for item in population])]
            next_population = [elite]
            while len(next_population) < config.population_size:
                if ctx.cancelled:
                    reason = StopReason.CANCELLED
                    break
                if not ctx.has_budget():
                    reason = StopReason.BUDGET_EXHAUSTED
                    break
                parent_a = roulette_select(population, ctx.rng).chromosome
                parent_b = roulette_select(population, ctx.rng).chromosome
                if ctx.rng.random() < config.crossover_prob:
                    children = crossover(parent_a, parent_b, ctx.rng)
                else:
                    children = (parent_a, parent_b)
                for child in children:
                    if len(next_population) == config.population_size:
                        break
                    if ctx.cancelled:
                        reason = StopReason.CANCELLED
                        break
                    if not ctx.has_budget():
                        reason = StopReason.BUDGET_EXHAUSTED
                        break
                    child = mutate_chromosome(
                        problem,
                        child,
                        ctx.rng,
                        config.mutation_rate(len(problem.packages)),
                    )
                    state = decode_chromosome(problem, child)
                    try:
                        fitness = ctx.evaluate(state)
                    except RunCancelled:
                        reason = StopReason.CANCELLED
                        break
                    next_population.append(Individual(child, state, fitness))
                if reason is not StopReason.GENERATION_LIMIT:
                    break
            if reason is not StopReason.GENERATION_LIMIT:
                break

            population = next_population
            current_best = population[ctx.argmax_tie([item.fitness for item in population])]
            ctx.record(
                current_best.fitness,
                generation=generation,
                population_mean_objective=(
                    sum(item.fitness for item in population) / len(population)
                ),
            )
        if ctx.cancelled:
            reason = StopReason.CANCELLED

    return ctx.build_result(
        initial_state=initial.state,
        initial_objective=initial.fitness,
        final_state=current_best.state,
        final_objective=current_best.fitness,
        stopped_reason=reason,
    )


__all__ = [
    "Chromosome",
    "Individual",
    "crossover",
    "decode_chromosome",
    "mutate_chromosome",
    "random_chromosome",
    "roulette_select",
    "run_genetic_algorithm",
    "validate_chromosome",
]
