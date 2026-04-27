#' @title climasus.data: Shared Metadata Catalog for CLIMA-SUS
#'
#' @description
#' Provides access to the shared JSON metadata catalog used by climasus4r
#' and climasus4py. All data files are stored in `inst/extdata/`.
#'
#' Main functions:
#' - [cd_path()] -- returns the full path to a data file
#' - [cd_load()] -- loads and parses a JSON file
#' - [cd_list_files()] -- lists all available data files
#' - [cd_version()] -- returns the package version
#'
#' @keywords internal
"_PACKAGE"


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

.extdata_root <- function() {
  system.file("extdata", package = "climasus.data", mustWork = TRUE)
}


# ---------------------------------------------------------------------------
# Exported API
# ---------------------------------------------------------------------------

#' Return the full path to a data file
#'
#' @param relative Character. Path relative to the extdata root, e.g.
#'   `"geo/municipios.json"` or `"metadata/datasus_systems.json"`.
#'
#' @return A character string with the absolute path to the file.
#'
#' @examples
#' cd_path("metadata/datasus_systems.json")
#' cd_path("geo/municipios.json")
#'
#' @export
cd_path <- function(relative) {
  stopifnot(is.character(relative), length(relative) == 1L)
  path <- file.path(.extdata_root(), relative)
  if (!file.exists(path)) {
    stop(sprintf("File not found in climasus.data: '%s'", relative))
  }
  path
}


#' Load a JSON file from the data catalog
#'
#' Parses the requested JSON file and returns it as an R object (usually a
#' named list). Requires the \pkg{jsonlite} package.
#'
#' @param relative Character. Path relative to the extdata root, e.g.
#'   `"metadata/datasus_systems.json"`.
#' @param simplifyVector Logical. Passed to [jsonlite::fromJSON()]. Default
#'   `TRUE` converts JSON arrays into R vectors/data frames.
#'
#' @return An R list (or data frame when `simplifyVector = TRUE`).
#'
#' @examples
#' \donttest{
#'   systems <- cd_load("metadata/datasus_systems.json")
#'   regions <- cd_load("metadata/regions.json")
#' }
#'
#' @export
cd_load <- function(relative, simplifyVector = TRUE) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop("Package 'jsonlite' is required for cd_load(). Install it with install.packages('jsonlite').")
  }
  jsonlite::fromJSON(cd_path(relative), simplifyVector = simplifyVector)
}


#' List all available data files
#'
#' @param pattern Optional character. A [grep()] pattern to filter file names.
#'
#' @return A character vector of relative paths (e.g. `"geo/municipios.json"`).
#'
#' @examples
#' cd_list_files()
#' cd_list_files(pattern = "json$")
#'
#' @export
cd_list_files <- function(pattern = NULL) {
  root <- .extdata_root()
  files <- list.files(root, recursive = TRUE, full.names = FALSE)
  if (!is.null(pattern)) {
    files <- grep(pattern, files, value = TRUE)
  }
  files
}


#' Return the climasus.data package version
#'
#' @return A character string with the version, e.g. `"0.1.0"`.
#'
#' @examples
#' cd_version()
#'
#' @export
cd_version <- function() {
  as.character(utils::packageVersion("climasus.data"))
}
