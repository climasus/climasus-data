test_that("cd_version() returns a non-empty string", {
  v <- cd_version()
  expect_type(v, "character")
  expect_true(nchar(v) > 0)
})

test_that("cd_list_files() returns character vector with JSON files", {
  files <- cd_list_files()
  expect_type(files, "character")
  expect_true(length(files) > 0)
  expect_true(any(grepl("\\.json$", files)))
})

test_that("cd_path() returns existing path for known file", {
  p <- cd_path("metadata/datasus_systems.json")
  expect_type(p, "character")
  expect_true(file.exists(p))
})

test_that("cd_path() errors for non-existent file", {
  expect_error(cd_path("nao_existe.json"), "File not found")
})

test_that("cd_load() returns a list or data.frame for datasus_systems.json", {
  skip_if_not_installed("jsonlite")
  result <- cd_load("metadata/datasus_systems.json")
  expect_true(is.list(result) || is.data.frame(result))
})

test_that("cd_load() returns data for geo/municipios.json", {
  skip_if_not_installed("jsonlite")
  municipios <- cd_load("geo/municipios.json")
  expect_true(length(municipios) > 0)
})
