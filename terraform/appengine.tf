
resource "google_app_engine_application" "app" {
  project       = var.project_id
  location_id   = var.region
  database_type = "CLOUD_FIRESTORE"
  depends_on = [
    google_project_service.services["appengine.googleapis.com"]
  ]
}
