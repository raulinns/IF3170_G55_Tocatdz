from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from ...domain.model import Orientation, Placement, Problem, State, Truck
from ...domain.packing import candidate_anchors, try_place
from ...search.moves import rotated_orientation
from ...search.run import (
    AlgorithmKind,
    BudgetExhausted,
    RunCancelled,
    RunConfig,
    RunContext,
    SearchResult,
    StopReason,
    TracePoint,
)

# Default peluang mutasi per anak jika config tidak diatur
DEFAULT_MUTATION_PROB = 0.2

_ORIENTATIONS = tuple(Orientation)
_AXES = ("x", "y", "z")


@dataclass(frozen=True, slots=True)
class Gene:
    # Priority mengatur urutan, orientation cara muat, truck_id tujuan paket
    # truck_id None berarti paket sengaja tidak dimasukkan ke truk
    priority: float
    orientation: Orientation
    truck_id: str | None


# Satu chromosome berisi gene untuk semua paket
Chromosome = tuple[Gene, ...]


@dataclass(frozen=True, slots=True)
class Individual:
    chromosome: Chromosome
    state: State
    fitness: float


@dataclass(frozen=True, slots=True)
class GAOptions:
    # Jumlah individu terbaik yang langsung dibawa ke generasi berikutnya
    elite_count: int = 0

    def __post_init__(self) -> None:
        if self.elite_count < 0:
            raise ValueError("elite_count must be non-negative")


def required_evaluations(
    population_size: int, generations: int, elite_count: int = 0
) -> int:
    # Hitung evaluasi populasi awal ditambah anak yang dibuat tiap generasi
    return population_size + (population_size - elite_count) * generations


def _truck_options(problem: Problem) -> list[str | None]:
    return [truck.id for truck in problem.trucks] + [None]


def random_chromosome(problem: Problem, rng: random.Random) -> Chromosome:
    # Buat satu solusi acak dengan gene untuk setiap paket
    options = _truck_options(problem)
    return tuple(
        Gene(rng.random(), rng.choice(_ORIENTATIONS), rng.choice(options))
        for _ in problem.packages
    )


def validate_chromosome(problem: Problem, chromosome: Chromosome) -> None:
    # Validasi jumlah gene pas dan setiap orientasi/truk yang dipakai valid
    if len(chromosome) != len(problem.packages):
        raise ValueError("chromosome must contain exactly one gene per package")
    truck_ids = {truck.id for truck in problem.trucks}
    for gene in chromosome:
        if not isinstance(gene.orientation, Orientation):
            raise ValueError("chromosome contains an invalid orientation")
        if gene.truck_id is not None and gene.truck_id not in truck_ids:
            raise ValueError("chromosome contains an unknown truck")


def _can_fit(
    truck: Truck, oriented, weight: float, used_weight: float
) -> bool:
    # filter ukuran dan kapasitas dulu sebelum mencoba posisi paket
    return (
        oriented.width <= truck.dimensions.width
        and oriented.length <= truck.dimensions.length
        and oriented.height <= truck.dimensions.height
        and used_weight + weight <= truck.max_capacity
    )


def decode_chromosome(problem: Problem, chromosome: Chromosome) -> State:
    # Ubah kromosom jadi state dengan menempatkan paket sesuai prioritas
    # Paket yang tidak muat atau tujuan None akan tetap berada di luar
    validate_chromosome(problem, chromosome)
    packages = problem.packages
    state = State(
        tuple(
            Placement(package.id, orientation=gene.orientation)
            for package, gene in zip(packages, chromosome)
        )
    )
    used_weight = {truck.id: 0.0 for truck in problem.trucks}

    order = sorted(range(len(packages)), key=lambda i: (chromosome[i].priority, i))
    for index in order:
        package = packages[index]
        gene = chromosome[index]
        if gene.truck_id is None:
            continue
        oriented = package.dimensions.oriented(gene.orientation)
        trucks = sorted(problem.trucks, key=lambda t: t.id != gene.truck_id)
        # Coba truk tujuan dulu, lalu truk lain sebagai cadangan
        for truck in trucks:
            if not _can_fit(truck, oriented, package.weight, used_weight[truck.id]):
                continue
            placed = None
            for anchor in candidate_anchors(problem, state, truck.id):
                placed = try_place(
                    problem, state, package.id, truck.id, anchor, gene.orientation
                )
                if placed is not None:
                    break
            if placed is not None:
                state = placed
                used_weight[truck.id] += package.weight
                break
    return state


def roulette_select(population: list[Individual], rng: random.Random) -> Individual:
    # Fitness lebih besar berarti peluang terpilih juga lebih besar
    weights = [individual.fitness for individual in population]
    if any(weight < 0 for weight in weights):
        raise ValueError("roulette selection requires non-negative fitness")
    total = sum(weights)
    # Kalau semua fitness nol, pilih acak karena peluangnya sama
    if total == 0:
        return rng.choice(population)
    pointer = rng.uniform(0, total)
    cumulative = 0.0
    for individual, weight in zip(population, weights):
        cumulative += weight
        if pointer <= cumulative:
            return individual
    # Fallback kalau ada selisih pembulatan pada angka kumulatif
    return population[-1]


def crossover(first: Chromosome, second: Chromosome, rng: random.Random) -> Chromosome:
    # Ambil bagian awal dari orang tua pertama, sisanya dari orang tua kedua
    if len(first) != len(second):
        raise ValueError("parents must have the same length")
    if len(first) < 2:
        return first
    cut = rng.randint(1, len(first) - 1)
    return first[:cut] + second[cut:]


def mutate_chromosome(
    problem: Problem, chromosome: Chromosome, rng: random.Random
) -> Chromosome:
    # Pilih paket lalu ubah urutan, orientasi, atau tujuan truknya
    genes = list(chromosome)
    index = rng.randrange(len(genes))
    gene = genes[index]
    package = problem.packages[index]

    current_dims = package.dimensions.oriented(gene.orientation)
    rotations: list[Orientation] = []
    seen = {current_dims}
    for axis in _AXES:
        candidate = rotated_orientation(
            problem, Placement(package.id, orientation=gene.orientation), axis
        )
        dims = package.dimensions.oriented(candidate)
        # Rotasi yang menghasilkan ukuran sama tidak perlu dicoba lagi
        if dims not in seen:
            seen.add(dims)
            rotations.append(candidate)

    # Reassign selalu tersedia, swap dan rotate hanya jika memungkinkan
    operators = ["reassign"]
    if len(genes) > 1:
        operators.append("swap")
    if rotations:
        operators.append("rotate")

    operator = rng.choice(operators)
    # Swap tukar prioritas/truk, rotate ubah orientasi, reassign ubah tujuan
    if operator == "swap":
        other = rng.choice([i for i in range(len(genes)) if i != index])
        a, b = genes[index], genes[other]
        genes[index] = Gene(b.priority, a.orientation, b.truck_id)
        genes[other] = Gene(a.priority, b.orientation, a.truck_id)
    elif operator == "rotate":
        genes[index] = Gene(gene.priority, rng.choice(rotations), gene.truck_id)
    else:
        choices = [t for t in _truck_options(problem) if t != gene.truck_id]
        genes[index] = Gene(rng.random(), gene.orientation, rng.choice(choices))
    return tuple(genes)


def _best_index(population: list[Individual]) -> int:
    return max(range(len(population)), key=lambda i: population[i].fitness)


def run_genetic_algorithm(
    problem: Problem,
    config: RunConfig,
    *,
    on_progress: Callable[[TracePoint], None] | None = None,
    context: RunContext | None = None,
    options: GAOptions | None = None,
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
    options = options if options is not None else GAOptions()
    if options.elite_count >= config.population_size:
        raise ValueError("elite_count must be smaller than population_size")

    ctx = context if context is not None else RunContext(problem, config, on_progress=on_progress)
    rng = ctx.rng
    mutation_prob = (
        config.mutation_prob if config.mutation_prob is not None else DEFAULT_MUTATION_PROB
    )

    def make_individual(
        chromosome: Chromosome, known: dict[Chromosome, Individual]
    ) -> Individual:
        ctx.check_cancelled()
        ctx.check_budget()
        # Kalau kromosom sama dengan orang tua, state-nya bisa dipakai lagi
        previous = known.get(chromosome)
        state = previous.state if previous is not None else decode_chromosome(problem, chromosome)
        return Individual(chromosome, state, ctx.evaluate(state))

    def record(population: list[Individual], generation: int) -> None:
        # Simpan fitness tertinggi dan rata-rata untuk grafik GA
        fitnesses = [individual.fitness for individual in population]
        ctx.record(
            max(fitnesses),
            generation=generation,
            population_mean_objective=sum(fitnesses) / len(fitnesses),
        )

    population: list[Individual] = []
    initial: Individual | None = None
    reason = StopReason.GENERATION_LIMIT
    try:
        # Isi populasi awal dengan solusi acak
        for _ in range(config.population_size):
            individual = make_individual(random_chromosome(problem, rng), {})
            population.append(individual)
            if initial is None:
                initial = individual
        record(population, generation=0)

        for generation in range(1, config.generations + 1):
            known = {individual.chromosome: individual for individual in population}
            ranked = sorted(population, key=lambda item: item.fitness, reverse=True)
            # Bawa individu terbaik jika elitism diaktifkan
            next_population = ranked[: options.elite_count]
            while len(next_population) < config.population_size:
                # Pilih orang tua, crossover, lalu mutasi sesuai peluang
                x = roulette_select(population, rng)
                y = roulette_select(population, rng)
                if rng.random() < config.crossover_prob:
                    child = crossover(x.chromosome, y.chromosome, rng)
                else:
                    child = x.chromosome
                if rng.random() < mutation_prob:
                    child = mutate_chromosome(problem, child, rng)
                next_population.append(make_individual(child, known))
            population = next_population
            record(population, generation)
    except BudgetExhausted:
        reason = StopReason.BUDGET_EXHAUSTED
    except RunCancelled:
        reason = StopReason.CANCELLED

    if not population or initial is None:
        raise RunCancelled("GA stopped before evaluating an initial individual")

    # Final state berarti yang terbaik di populasi terakhir
    final = population[_best_index(population)]
    # Best state mencatat solusi terbaik dari seluruh proses pencarian
    return ctx.build_result(
        initial_state=initial.state,
        initial_objective=initial.fitness,
        final_state=final.state,
        final_objective=final.fitness,
        stopped_reason=reason,
    )


__all__ = [
    "Chromosome",
    "DEFAULT_MUTATION_PROB",
    "GAOptions",
    "Gene",
    "Individual",
    "crossover",
    "decode_chromosome",
    "mutate_chromosome",
    "random_chromosome",
    "required_evaluations",
    "roulette_select",
    "run_genetic_algorithm",
    "validate_chromosome",
]
