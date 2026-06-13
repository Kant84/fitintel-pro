variable "environment" {
  description = "Окружение (prod/staging)"
  type        = string
}

variable "zone" {
  description = "Yandex Cloud Zone"
  type        = string
  default     = "ru-central1-a"
}

variable "vpc_name" {
  description = "Имя VPC"
  type        = string
}

variable "subnets" {
  description = "Конфигурация подсетей"
  type = map(object({
    cidr = string
    name = string
  }))
}
