#!/usr/bin/env python3
"""Recalculate selected printed numerical records, without validating experiments.

Run with Python 3. Input: published_case_inputs.json beside this script.
Outputs: published_case_results.json and three CSV tables beside this script.
Uses only the standard library; never infers omitted inputs.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path


def relative_difference_percent(estimate: float, reference: float) -> float:
    if reference <= 0:
        raise ValueError("Reference value must be positive.")
    return 100.0 * (estimate - reference) / reference


def within_reporting_increment(value: float, printed: float, increment: float) -> bool:
    return abs(value - printed) <= 0.5 * increment + abs(value) * 1e-14


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    task_directory = Path(__file__).resolve().parent
    input_path = task_directory / "published_case_inputs.json"
    data = json.loads(input_path.read_text(encoding="utf-8"))
    checks = []
    soil_rows = []
    for row in data["soil"]["estimates"]:
        density_delta = relative_difference_percent(row["density_estimate_ppm"], row["icp_oes_ppm"])
        temperature_delta = relative_difference_percent(row["temperature_estimate_ppm"], row["icp_oes_ppm"])
        for label, value in (("density", density_delta), ("temperature", temperature_delta)):
            expected = row[f"expected_{label}_delta_percent"]
            passed = within_reporting_increment(value, expected, 0.01)
            checks.append({"name": f"soil_{row['element']}_{label}_delta", "passes": passed})
        soil_rows.append({
            "element": row["element"],
            "icp_oes_ppm": row["icp_oes_ppm"],
            "density_estimate_ppm": row["density_estimate_ppm"],
            "density_delta_percent": density_delta,
            "temperature_estimate_ppm": row["temperature_estimate_ppm"],
            "temperature_delta_percent": temperature_delta,
        })

    alloy_rows = []
    for pair in data["alloy"]["line_pairs"]:
        wavelength_one, wavelength_two = pair["wavelengths_nm"]
        intensity_one, intensity_two = pair["intensities_au"]
        probability_one, probability_two = pair["transition_probabilities_s_inverse"]
        weight_one, weight_two = pair["upper_statistical_weights"]
        energy_one, energy_two = pair["upper_energies_eV"]
        experimental = intensity_one / intensity_two
        theoretical = (probability_one * weight_one * wavelength_two /
                       (probability_two * weight_two * wavelength_one) *
                       math.exp(-(energy_one - energy_two) / data["alloy"]["kBT_eV"]))
        difference = relative_difference_percent(experimental, theoretical)
        for label, value, increment in (("experimental_ratio", experimental, 0.001),
                                        ("theoretical_ratio", theoretical, 0.001),
                                        ("difference_percent", difference, 0.01)):
            expected = pair[f"expected_{label}_{'2dp' if label == 'difference_percent' else '3dp'}"]
            checks.append({"name": f"alloy_{pair['species']}_{label}",
                           "passes": within_reporting_increment(value, expected, increment)})
        satisfies = abs(difference) <= data["alloy"]["ratio_acceptance_percent"]
        checks.append({"name": f"alloy_{pair['species']}_printed_10percent_comparison", "passes": satisfies})
        alloy_rows.append({"species": pair["species"], "experimental_ratio": experimental,
                           "theoretical_ratio": theoretical, "difference_percent": difference,
                           "satisfies_printed_10percent_comparison": satisfies})

    plant = data["plant"]
    energy_gap = plant["upper_energy_eV"] - plant["lower_energy_eV"]
    threshold = plant["mcwhirter_prefactor_cm_inverse_cubed"] * math.sqrt(plant["temperature_K"]) * energy_gap**3
    stark_hwhm_nm = 0.1 * plant["stark_hwhm_Angstrom"]
    density_using_total_width = (plant["total_fitted_fwhm_nm"] / (2 * stark_hwhm_nm) *
                                 plant["stark_reference_density_cm_inverse_cubed"])
    concentration_sum = math.fsum(plant["cflibs_concentrations_mg_per_kg"].values())
    mass_percent = 100 * concentration_sum / 1e6
    checks.extend([
        {"name": "plant_mcwhirter_rounding", "passes": within_reporting_increment(
            threshold, plant["printed_mcwhirter_threshold_cm_inverse_cubed"],
            plant["mcwhirter_reporting_increment_cm_inverse_cubed"])},
        {"name": "plant_total_width_stark_rounding", "passes": within_reporting_increment(
            density_using_total_width, plant["printed_density_cm_inverse_cubed"],
            plant["density_reporting_increment_cm_inverse_cubed"])},
        {"name": "plant_concentration_sum", "passes": math.isclose(
            concentration_sum, plant["expected_concentration_sum_mg_per_kg"], rel_tol=0, abs_tol=1e-8)},
        {"name": "plant_mass_percent", "passes": math.isclose(
            mass_percent, plant["expected_mass_percent"], rel_tol=0, abs_tol=1e-12)},
    ])
    plant_results = {
        "energy_gap_eV": energy_gap,
        "mcwhirter_threshold_cm_inverse_cubed": threshold,
        "density_using_total_fitted_width_cm_inverse_cubed": density_using_total_width,
        "instrument_corrected_density_cm_inverse_cubed": None,
        "concentration_sum_mg_per_kg": concentration_sum,
        "mass_percent_of_reported_23_elements": mass_percent,
        "absolute_closure_reconstructed": False,
    }
    plant_rows = [{"element": element, "cflibs_mg_per_kg": concentration}
                  for element, concentration in plant["cflibs_concentrations_mg_per_kg"].items()]
    if not all(check["passes"] for check in checks):
        failed = [check["name"] for check in checks if not check["passes"]]
        raise AssertionError(f"Recalculation checks failed: {failed}")
    results = {"scope": data["scope"], "sources": data["sources"], "soil": soil_rows,
               "alloy": alloy_rows, "plant": plant_results, "checks": checks,
               "check_count": len(checks), "all_checks_pass": True}
    (task_directory / "published_case_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(task_directory / "published_case_soil.csv", soil_rows)
    write_csv(task_directory / "published_case_alloy_ratios.csv", alloy_rows)
    write_csv(task_directory / "published_case_plant_concentrations.csv", plant_rows)
    print(f"{len(checks)} numerical checks passed. These checks do not validate the experiments or plasma models.")


if __name__ == "__main__":
    main()
