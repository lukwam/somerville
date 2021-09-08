resource "google_cloudbuild_trigger" "deploy-update-meeting-calendar-function" {
  provider       = google-beta
  name           = "deploy-google-meeting-calendar-function"
  description    = "Deploy Update Meeting Calendar Function"
  filename       = "functions/update_meeting_calendar/cloudbuild.yaml"
  project        = var.project_id
  included_files = [
    "functions/update_meeting_calendar/**",
  ]
  ignored_files = [
    "functions/update_meeting_calendar/*.md",
    "functions/update_meeting_calendar/*.sh",
    "functions/update_meeting_calendar/Dockerfile",
  ]

  github {
    name     = "somerville"
    owner    = "lukwam"
    push {
      branch = "main"
    }
  }

  depends_on = [
    google_project_service.services["cloudbuild.googleapis.com"]
  ]
}