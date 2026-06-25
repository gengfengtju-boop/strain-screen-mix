ul <- file.path(Sys.getenv("USERPROFILE"), "R", "win-library", "4.6")
dir.create(ul, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(ul, .libPaths()))
options(repos = c(CRAN = "https://cloud.r-project.org"))

# ExperimentHub also needs source install (same issue as AnnotationHub)
if (!requireNamespace("ExperimentHub", quietly = TRUE)) {
  bioc_base <- "https://bioconductor.org/packages/3.23/bioc"
  av <- available.packages(repos = bioc_base, type = "source")
  ver <- av["ExperimentHub", "Version"]
  cat("Installing ExperimentHub", ver, "from source...\n")
  url <- paste0(bioc_base, "/src/contrib/ExperimentHub_", ver, ".tar.gz")
  install.packages(url, lib = ul, repos = NULL, type = "source")
}
cat("ExperimentHub:", requireNamespace("ExperimentHub", quietly = TRUE), "\n")

# Now install curatedMetagenomicData via BiocManager
if (!requireNamespace("curatedMetagenomicData", quietly = TRUE)) {
  BiocManager::install("curatedMetagenomicData", lib = ul, ask = FALSE, update = FALSE)
}
cat("curatedMetagenomicData:", requireNamespace("curatedMetagenomicData", quietly = TRUE), "\n")
