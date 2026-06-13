variable "environment" {
  type = string
}

variable "zone" {
  type = string
}

variable "folder_id" {
  type = string
}

variable "network_id" {
  type = string
}

variable "subnet_ids" {
  type = map(string)
}

variable "security_group_ids" {
  type = map(string)
}

variable "instances" {
  type = map(object({
    subnet_key   = string
    cores        = number
    memory       = number
    disk_size    = number
    image_family = string
    nat          = bool
    role         = string
  }))
}
