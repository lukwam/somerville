resource "google_cloud_scheduler_job" "run_update_meeting_calendar" {
  name             = "run_update_meeting_calendar"
  description      = "Run \"update_meeting_calendar\" function"
  schedule         = "17 * * * *"
  time_zone        = "America/New_York"
  attempt_deadline = "300s"
  project          = google_project.project.project_id
  region           = var.region
  http_target {
    http_method = "POST"
    uri = "https://${var.region}-${var.project_id}.cloudfunctions.net/update_meeting_calendar"

    oidc_token {
      audience = "https://${var.region}-${var.project_id}.cloudfunctions.net/update_meeting_calendar"
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
    }
  }
  depends_on = [
    google_app_engine_application.app,
    google_project_service.services["cloudscheduler.googleapis.com"]
  ]
}
