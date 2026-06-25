#!/usr/bin/env Rscript
# Fetch obesity-relevant samples from curatedMetagenomicData and export to
# project-standard CSVs:
#   data/metadata/sample_metadata_raw.csv
#   data/taxonomic_profile/species_abundance_wide.csv   (samples x species)
#   data/taxonomic_profile/species_abundance_long.csv   (project schema)
#
# Usage:
#   Rscript scripts/data_download/fetch_curatedMetagenomicData.R
#
# Requirements (install once):
#   install.packages("BiocManager")
#   BiocManager::install("curatedMetagenomicData")
#   install.packages(c("dplyr", "tidyr", "readr", "stringr"))

ul <- file.path(Sys.getenv("USERPROFILE"), "R", "win-library", "4.6")
if (dir.exists(ul)) .libPaths(c(ul, .libPaths()))

suppressPackageStartupMessages({
  library(curatedMetagenomicData)
  library(dplyr)
  library(tidyr)
  library(readr)
  library(stringr)
  library(SummarizedExperiment)
})

# ── paths ──────────────────────────────────────────────────────────────────────
# Accept root as first command-line arg, else use working directory
args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) normalizePath(args[1], mustWork = FALSE) else getwd()

out_meta   <- file.path(root, "data", "metadata",         "sample_metadata_raw.csv")
out_wide   <- file.path(root, "data", "taxonomic_profile", "species_abundance_wide.csv")
out_long   <- file.path(root, "data", "taxonomic_profile", "species_abundance_long.csv")

dir.create(dirname(out_meta), showWarnings = FALSE, recursive = TRUE)
dir.create(dirname(out_wide), showWarnings = FALSE, recursive = TRUE)

# ── 1. filter sample metadata ──────────────────────────────────────────────────
message("[1/4] Filtering sampleMetadata ...")

meta_raw <- sampleMetadata

# Keep samples with:
#   - BMI recorded
#   - gut (fecal) body site
#   - disease label covering obesity spectrum or healthy controls
target_diseases <- c(
  "healthy", "obesity", "overweight",
  "T2D", "metabolic_syndrome", "NAFLD",
  "hypertension", "IGT"          # common obesity-comorbidity studies
)

meta_filt <- meta_raw |>
  filter(
    !is.na(BMI),
    body_site %in% c("stool", "feces"),
    disease %in% target_diseases
  )

message(sprintf("  %d samples pass filter (from %d total)", nrow(meta_filt), nrow(meta_raw)))

if (nrow(meta_filt) == 0) stop("No samples passed filter — check curatedMetagenomicData version.")

# ── 2. fetch relative abundance (species level) ────────────────────────────────
message("[2/4] Fetching species-level relative abundance (this may take a while) ...")

study_ids <- sort(unique(meta_filt$study_name))

# Optional: limit number of studies via 2nd command-line arg (for testing / flaky net)
max_studies <- if (length(args) >= 2) as.integer(args[2]) else Inf
if (is.finite(max_studies)) {
  study_ids <- head(study_ids, max_studies)
  message(sprintf("  LIMITED to first %d studies (max_studies arg)", length(study_ids)))
}
message(sprintf("  %d studies to fetch", length(study_ids)))

# per-study cache dir so interrupted runs resume
cache_dir <- file.path(root, "data", "raw_data", "cmd_cache")
dir.create(cache_dir, showWarnings = FALSE, recursive = TRUE)

# robust per-study fetch with retries (Schannel TLS handshake is flaky in CN)
fetch_one <- function(sid, max_try = 4) {
  rds <- file.path(cache_dir, paste0(sid, ".relative_abundance.rds"))
  if (file.exists(rds)) {
    message(sprintf("  [cache] %s", sid))
    return(readRDS(rds))
  }
  # resource titles look like "2021-03-31.AsnicarF_2021.relative_abundance"
  pat <- paste0(sid, "\\.relative_abundance$")
  for (attempt in seq_len(max_try)) {
    res <- tryCatch({
      lst <- curatedMetagenomicData(pat, dryrun = FALSE, counts = FALSE,
                                     rownames = "long")
      if (length(lst) == 0) stop("empty result")
      lst[[1]]
    }, error = function(e) { message(sprintf("    attempt %d/%d failed: %s",
                                             attempt, max_try, conditionMessage(e)))
                             NULL })
    if (!is.null(res)) {
      saveRDS(res, rds)
      message(sprintf("  [ok]    %s  (%d samples)", sid, ncol(res)))
      return(res)
    }
    Sys.sleep(2 * attempt)  # backoff
  }
  message(sprintf("  [SKIP]  %s  — failed after %d attempts", sid, max_try))
  NULL
}

se_list <- list()
for (i in seq_along(study_ids)) {
  message(sprintf("  (%d/%d) %s", i, length(study_ids), study_ids[i]))
  se_i <- fetch_one(study_ids[i])
  if (!is.null(se_i)) se_list[[study_ids[i]]] <- se_i
}

if (length(se_list) == 0) stop("No studies fetched successfully — check network.")
message(sprintf("  %d / %d studies fetched OK", length(se_list), length(study_ids)))

# merge: align on union of taxa (different studies may have different rownames)
all_taxa <- sort(unique(unlist(lapply(se_list, rownames))))
align_one <- function(se_i) {
  m <- matrix(0, nrow = length(all_taxa), ncol = ncol(se_i),
              dimnames = list(all_taxa, colnames(se_i)))
  m[rownames(se_i), ] <- assay(se_i)
  m
}
abund_full <- do.call(cbind, lapply(se_list, align_one))
se <- SummarizedExperiment(assays = list(relative_abundance = abund_full))

# ── 3. restrict to filtered samples & species level ───────────────────────────
message("[3/4] Restricting to filtered samples and species-level taxa ...")

# keep only the sample IDs that passed our metadata filter
common_samples <- intersect(colnames(se), meta_filt$sample_id)
message(sprintf("  %d / %d filtered samples found in abundance data",
                length(common_samples), nrow(meta_filt)))

se <- se[, common_samples]

# keep only species-level rows (contain exactly one '|s__' segment)
tax_names <- rownames(se)
is_species <- str_detect(tax_names, "\\|s__") & !str_detect(tax_names, "\\|t__")
se_sp <- se[is_species, ]
message(sprintf("  %d species-level taxa retained", nrow(se_sp)))

# short species name: last 's__' component
short_name <- str_extract(rownames(se_sp), "s__[^|]+$") |>
  str_remove("^s__") |>
  str_replace_all("[^A-Za-z0-9_]", "_")

# ── 4. export ──────────────────────────────────────────────────────────────────
message("[4/4] Exporting CSVs ...")

## 4a. sample metadata (project schema)
meta_out <- meta_filt |>
  filter(sample_id %in% common_samples) |>
  transmute(
    sample_id          = sample_id,
    subject_id         = subject_id,
    study_id           = study_name,
    database_source    = "curatedMetagenomicData",
    sequencing_type    = "shotgun",
    body_site          = "feces",
    time_point         = case_when(
      str_detect(tolower(study_condition), "baseline|pre|0") ~ "baseline",
      str_detect(tolower(study_condition), "post|follow")    ~ "post",
      TRUE                                                   ~ "baseline"
    ),
    age                = age,
    sex                = case_when(
      tolower(gender) == "male"   ~ "male",
      tolower(gender) == "female" ~ "female",
      TRUE                        ~ "unknown"
    ),
    BMI                = BMI,
    obesity_status     = case_when(
      BMI < 18.5               ~ "lean",
      BMI < 25                 ~ "lean",
      BMI < 30                 ~ "overweight",
      BMI >= 30                ~ "obesity",
      TRUE                     ~ NA_character_
    ),
    disease_status     = disease,
    country            = country,
    region             = NA_character_,
    antibiotic_use     = case_when(
      !is.na(antibiotics_current_use) ~ as.character(antibiotics_current_use),
      TRUE                            ~ NA_character_
    ),
    diet_info_available    = FALSE,
    intervention_available = FALSE,
    age_missing            = is.na(age)
  )

write_csv(meta_out, out_meta)
message(sprintf("  Wrote %d rows -> %s", nrow(meta_out), out_meta))

## 4b. wide abundance matrix (samples as rows for ML)
abund_mat <- t(assay(se_sp))                        # samples x taxa
colnames(abund_mat) <- short_name
wide_df <- as.data.frame(abund_mat) |>
  tibble::rownames_to_column("sample_id")

write_csv(wide_df, out_wide)
message(sprintf("  Wrote wide matrix [%d samples x %d species] -> %s",
                nrow(wide_df), ncol(wide_df) - 1, out_wide))

## 4c. long format (project taxonomic_profile schema)
long_df <- wide_df |>
  pivot_longer(-sample_id, names_to = "taxon_name", values_to = "relative_abundance") |>
  filter(relative_abundance > 0) |>
  mutate(
    taxon_level      = "species",
    database_source  = "curatedMetagenomicData",
    profiling_method = "MetaPhlAn"
  ) |>
  select(sample_id, taxon_level, taxon_name, relative_abundance,
         database_source, profiling_method)

write_csv(long_df, out_long)
message(sprintf("  Wrote long format [%d rows] -> %s", nrow(long_df), out_long))

message("\nDone. Next steps:")
message("  python -m proslim_ai clean-sample-metadata data/metadata/sample_metadata_raw.csv data/processed_data/sample_metadata_clean.csv")
message("  python -m proslim_ai validate-table sample_metadata data/metadata/sample_metadata_raw.csv")
