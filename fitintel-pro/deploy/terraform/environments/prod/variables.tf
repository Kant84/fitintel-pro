variable "folder_id" {
  description = "Yandex Cloud Folder ID"
  type        = string
}

variable "zone" {
  description = "Yandex Cloud Zone"
  type        = string
  default     = "ru-central1-a"
}

variable "domain" {
  description = "Домен для приложения"
  type        = string
  default     = "fitintel.ru"
}
