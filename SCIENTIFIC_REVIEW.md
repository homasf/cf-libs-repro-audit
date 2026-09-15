# Scientific revision — 15 September 2026

Reviewed main: ce0fbf5d2b721e7af391520fa2e64b7998c2c2c6.
This revision corrects numerical and reporting behaviour, without independently
validating the original experiments.

Changes: fix CI wheel command names; reject non-finite/domain-invalid inputs;
add K/eV conversion, mass–mole conversion and stable Voigt inversion; require
explicit numerical comparison rules; add NOT_ASSESSED; preserve provenance in
reports; prevent nonzero slope alone being marked as reproduction; reject
unverified records in strict mode; add the missing Ni temperature equation;
add five source-linked case calculations and a reproducible figure script.

Known results: alloy McWhirter threshold 4.02234e15 cm^-3; plant temperature
7525.426 K (R² 0.978661); conditional plant instrument scenario 9.11552e15 cm^-3;
plant RA percentage floor excludes 23 entries and the fractional necessary bound
excludes 17 under stated assumptions; MESBP distance 22 to 6 percentage points;
all six Alnico mole percentages reconstruct within 0.005 percentage points.

Tests support the implemented arithmetic, domains, rounding envelopes, composition
round trips, Boltzmann intensity-scale invariance and reporting metadata. They do
not verify experimental uncertainty, self-absorption, LTE or whole-sample closure.
Authors must verify transcribed inputs before assigning verification stamps.
The code is not a complete CF-LIBS pipeline. This revision is not a released DOI.
