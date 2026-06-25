#!/usr/bin/env Rscript
# E1b — fetch HUMAnN pathway_abundance from curatedMetagenomicData for the SAME samples
# already in data/metadata/sample_metadata_raw.csv, and export a samples x pathways matrix.
#   Rscript scripts/data_download/fetch_pathways.R "F:\strain screen mix" [max_studies]

suppressPackageStartupMessages({
  ul <- file.path(Sys.getenv("USERPROFILE"), "R", "win-library", "4.6")
  .libPaths(c(ul, .libPaths()))
  library(curatedMetagenomicData); library(dplyr); library(readr)
  library(tidyr); library(stringr); library(SummarizedExperiment)
})

args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) args[1] else getwd()
out_wide <- file.path(root, "data", "functional_profile", "pathway_abundance_wide.csv")
dir.create(dirname(out_wide), showWarnings = FALSE, recursive = TRUE)

meta <- read_csv(file.path(root, "data", "metadata", "sample_metadata_raw.csv"),
                 show_col_types = FALSE)
keep_samples <- meta$sample_id
study_ids <- sort(unique(meta$study_id))
max_studies <- if (length(args) >= 2) as.integer(args[2]) else Inf
if (is.finite(max_studies)) study_ids <- head(study_ids, max_studies)
message(sprintf("[1/3] %d studies / %d target samples", length(study_ids), length(keep_samples)))

cache_dir <- file.path(root, "data", "raw_data", "cmd_pathway_cache")
dir.create(cache_dir, showWarnings = FALSE, recursive = TRUE)

fetch_one <- function(sid, max_try = 4) {
  rds <- file.path(cache_dir, paste0(sid, ".pathway_abundance.rds"))
  if (file.exists(rds)) { message(sprintf("  [cache] %s", sid)); return(readRDS(rds)) }
  pat <- paste0(sid, "\\.pathway_abundance$")
  for (attempt in seq_len(max_try)) {
    res <- tryCatch({
      lst <- curatedMetagenomicData(pat, dryrun = FALSE, counts = FALSE, rownames = "short")
      if (length(lst) == 0) stop("empty"); lst[[1]]
    }, error = function(e) { message(sprintf("    attempt %d/%d: %s", attempt, max_try,
                                              conditionMessage(e))); NULL })
    if (!is.null(res)) { saveRDS(res, rds)
      message(sprintf("  [ok] %s (%d samples x %d pathways)", sid, ncol(res), nrow(res)))
      return(res) }
    Sys.sleep(2 * attempt)
  }
  message(sprintf("  [SKIP] %s", sid)); NULL
}

message("[2/3] fetching pathway_abundance per study ...")
se_list <- list()
for (i in seq_along(study_ids)) {
  message(sprintf("  (%d/%d) %s", i, length(study_ids), study_ids[i]))
  se <- fetch_one(study_ids[i])
  if (!is.null(se)) {
    common <- intersect(colnames(se), keep_samples)
    if (length(common) > 0) se_list[[study_ids[i]]] <- se[, common]
  }
}
if (length(se_list) == 0) stop("no pathway data fetched")

message("[3/3] merging into union-pathway wide matrix ...")
# keep UNstratified pathway rows only (drop the |g__..|s__.. stratified rows)
clean_one <- function(se) {
  rn <- rownames(se)
  unstrat <- !str_detect(rn, "\\|")
  se[unstrat, , drop = FALSE]
}
se_list <- lapply(se_list, clean_one)
all_paths <- sort(unique(unlist(lapply(se_list, rownames))))
align <- function(se) {
  m <- matrix(0, nrow = length(all_paths), ncol = ncol(se),
              dimnames = list(all_paths, colnames(se)))
  m[rownames(se), ] <- assay(se); m
}
full <- do.call(cbind, lapply(se_list, align))
wide <- as.data.frame(t(full)); wide <- tibble::rownames_to_column(wide, "sample_id")
# sanitize pathway column names
names(wide)[-1] <- make.names(names(wide)[-1])
write_csv(wide, out_wide)
message(sprintf("Wrote [%d samples x %d pathways] -> %s", nrow(wide), ncol(wide) - 1, out_wide))
