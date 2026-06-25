#!/usr/bin/env Rscript
# Install all R dependencies needed for fetch_curatedMetagenomicData.R
# Run once: Rscript scripts/data_download/install_r_deps.R

options(repos = c(CRAN = "https://cloud.r-project.org"))

# ensure a writable user library exists
user_lib <- file.path(Sys.getenv("USERPROFILE"), "R", "win-library",
                      paste0(R.version$major, ".", substr(R.version$minor, 1, 1)))
dir.create(user_lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(user_lib, .libPaths()))

cran_pkgs <- c("dplyr", "tidyr", "readr", "stringr", "tibble")
bioc_pkgs <- c("BiocManager", "curatedMetagenomicData", "SummarizedExperiment")

install_if_missing <- function(pkg, bioc = FALSE) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    message(sprintf("Installing %s ...", pkg))
    if (bioc) {
      BiocManager::install(pkg, lib = user_lib, ask = FALSE, update = FALSE)
    } else {
      install.packages(pkg, lib = user_lib, quiet = TRUE)
    }
  } else {
    message(sprintf("Already installed: %s", pkg))
  }
}

for (p in cran_pkgs) install_if_missing(p)

install_if_missing("BiocManager")
for (p in c("curatedMetagenomicData", "SummarizedExperiment")) {
  install_if_missing(p, bioc = TRUE)
}

message("\nAll dependencies ready.")
