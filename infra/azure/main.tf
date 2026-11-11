terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource group
resource "azurerm_resource_group" "rag" {
  name     = "rg-portfolio-rag"
  location = "UK South"
}

# 2. Private Docker image registry
resource "azurerm_container_registry" "rag" {
  name                = var.registry_name
  resource_group_name = azurerm_resource_group.rag.name
  location            = azurerm_resource_group.rag.location
  sku                 = "Basic"
  admin_enabled       = false
}

# 3. Log storage and monitoring
resource "azurerm_log_analytics_workspace" "rag" {
  name                = "law-portfolio-rag"
  resource_group_name = azurerm_resource_group.rag.name
  location            = azurerm_resource_group.rag.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# 4. Container Apps environment
resource "azurerm_container_app_environment" "rag" {
  name                       = "cae-portfolio-rag"
  resource_group_name        = azurerm_resource_group.rag.name
  location                   = azurerm_resource_group.rag.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.rag.id

  lifecycle {
    ignore_changes = [
      workload_profile
    ]
  }
}

variable "registry_name" {
  description = "Globally unique Azure Container Registry name"
  type        = string
}

output "registry_server" {
  value = azurerm_container_registry.rag.login_server
}

output "resource_group" {
  value = azurerm_resource_group.rag.name
}

resource "azurerm_user_assigned_identity" "rag" {
  name                = "id-portfolio-rag"
  location            = azurerm_resource_group.rag.location
  resource_group_name = azurerm_resource_group.rag.name
}

resource "azurerm_role_assignment" "rag_pull" {
  scope                = azurerm_container_registry.rag.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.rag.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_container_app" "rag" {
  name                         = "ca-portfolio-rag"
  resource_group_name          = azurerm_resource_group.rag.name
  container_app_environment_id = azurerm_container_app_environment.rag.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.rag.id]
  }

  registry {
    server   = azurerm_container_registry.rag.login_server
    identity = azurerm_user_assigned_identity.rag.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000

/*
    ip_security_restriction {
      name             = "my-development-pc"
      action           = "Allow"
      ip_address_range = var.development_ip_cidr
    }
*/
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "knowledge-api"
      image  = "${azurerm_container_registry.rag.login_server}/portfolio-rag:v3"
      cpu    = 1.0
      memory = "2Gi"

      # The actual DeepSeek key is stored with Azure CLI as a
      # Container Apps secret, not in this Terraform file.
      env {
        name        = "DEEPSEEK_API_KEY"
        secret_name = "deepseek-api-key"
      }

      env {
        name  = "CORS_ORIGINS"
        value = "https://iand4096.github.io,http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
      }

      # Keep paid generation disabled until deliberately enabled
      # after deploying and testing the protected backend.
      env {
        name  = "RAG_CHAT_ENABLED"
        value = "true"
      }
    }
  }

  # The secret is created and updated outside Terraform using Azure CLI.
  # Preserve it when Terraform updates the Container App.
  lifecycle {
    ignore_changes = [secret]
  }

  depends_on = [azurerm_role_assignment.rag_pull]
}

output "api_url" {
  value = "https://${azurerm_container_app.rag.ingress[0].fqdn}"
}
