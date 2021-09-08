resource "google_project" "project" {
  name            = var.project_name
  project_id      = var.project_id
  folder_id       = var.folder_id
  billing_account = var.billing_account

  labels = {
      billing    = lower(var.billing_account),
  }

  auto_create_network = false
  skip_delete = false
}

