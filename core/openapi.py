from __future__ import annotations


def build_openapi_spec() -> dict:
    """
    Minimal OpenAPI spec (hand-written) for this Flask service.

    We intentionally avoid runtime introspection to keep dependencies small and
    the output stable across environments.
    """

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Account Manager API",
            "version": "1.0.0",
            "description": (
                "A lightweight account-management service built with Flask + SQLAlchemy.\n\n"
                "Compliance notice: this project does NOT perform any automated third-party "
                "registration, CAPTCHA bypass, or anti-bot circumvention."
            ),
        },
        "servers": [{"url": "/"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "error"},
                        "message": {"type": "string"},
                        "code": {"type": "string"},
                        "request_id": {"type": "string"},
                    },
                    "required": ["status", "message"],
                },
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "username": {"type": "string"},
                        "email": {"type": "string", "nullable": True},
                    },
                    "required": ["id", "username"],
                },
                "Account": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "email": {"type": "string"},
                        "password": {"type": "string"},
                        "is_used": {"type": "integer", "description": "0/1"},
                        "expire_time": {"type": "integer", "nullable": True},
                        "expire_time_fmt": {"type": "string", "nullable": True},
                        "create_time": {"type": "integer"},
                    },
                    "required": ["id", "email", "is_used"],
                },
                "AuditLog": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "action": {"type": "string"},
                        "entity_type": {"type": "string", "nullable": True},
                        "entity_id": {"type": "integer", "nullable": True},
                        "detail": {"type": "string", "nullable": True},
                        "created_at": {"type": "integer"},
                    },
                    "required": ["id", "action", "created_at"],
                },
            },
        },
        "paths": {
            "/api/register": {
                "post": {
                    "summary": "Register",
                    "description": "Create a user and return a JWT token (can be disabled by ALLOW_SELF_REGISTER=false).",
                    "security": [],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                    "required": ["username", "password"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "OK"},
                        "403": {"description": "Forbidden"},
                    },
                }
            },
            "/api/login": {
                "post": {
                    "summary": "Login",
                    "security": [],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string"},
                                    },
                                    "required": ["username", "password"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/user": {
                "get": {
                    "summary": "Current user",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "user": {"$ref": "#/components/schemas/User"},
                                        },
                                        "required": ["status", "user"],
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/logout": {
                "post": {
                    "summary": "Logout",
                    "description": "Revokes the current JWT token (jti blacklist) until it expires.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/account": {
                "get": {
                    "summary": "Checkout one unused account",
                    "responses": {
                        "200": {"description": "OK"},
                        "404": {"description": "No available account"},
                    },
                },
                "post": {
                    "summary": "Import account into pool",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                        "expire_days": {"type": "integer"},
                                    },
                                    "required": ["email", "password"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "409": {"description": "Already exists"},
                    },
                },
            },
            "/api/accounts": {
                "get": {
                    "summary": "List my accounts",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 1},
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 10},
                        },
                        {"name": "q", "in": "query", "schema": {"type": "string"}},
                        {
                            "name": "used",
                            "in": "query",
                            "description": "Filter used status: true/false/1/0",
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/account/{id}": {
                "get": {
                    "summary": "Get one account (may include password)",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {"description": "OK"},
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/api/account/{id}/status": {
                "put": {
                    "summary": "Update account status",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "is_used": {"type": "integer", "description": "0/1"}
                                    },
                                    "required": ["is_used"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/account/{id}/delete": {
                "put": {
                    "summary": "Soft-delete account",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/audit/logs": {
                "get": {
                    "summary": "List my audit logs",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 1},        
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 20},       
                        },
                        {"name": "q", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/admin/accounts": {
                "get": {
                    "summary": "Admin list accounts",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 1},
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 10},
                        },
                        {
                            "name": "include_password",
                            "in": "query",
                            "schema": {"type": "boolean", "default": False},
                        },
                        {
                            "name": "show_deleted",
                            "in": "query",
                            "schema": {"type": "boolean", "default": False},
                        },
                        {"name": "q", "in": "query", "schema": {"type": "string"}},
                        {"name": "used", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {"description": "OK"},
                        "403": {"description": "Forbidden"},
                    },
                }
            },
            "/api/admin/users": {
                "get": {
                    "summary": "Admin list users",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 1},
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 10},
                        },
                        {"name": "q", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "summary": "Admin create user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                    "required": ["username", "password"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "409": {"description": "Conflict"},
                    },
                },
            },
            "/api/admin/users/{id}/password": {
                "put": {
                    "summary": "Admin reset user password",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"password": {"type": "string"}},
                                    "required": ["password"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}, "404": {"description": "Not found"}},
                }
            },
            "/api/admin/audit/logs": {
                "get": {
                    "summary": "Admin list audit logs",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 1},        
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 20},       
                        },
                        {
                            "name": "user_id",
                            "in": "query",
                            "schema": {"type": "integer"},
                        },
                        {"name": "q", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/health": {
                "get": {
                    "summary": "Health check",
                    "security": [],
                    "parameters": [
                        {
                            "name": "ready",
                            "in": "query",
                            "description": "If set to 1, also checks DB connectivity (readiness probe).",
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}, "503": {"description": "Unready"}},
                }
            },
            "/metrics": {
                "get": {
                    "summary": "Prometheus metrics",
                    "security": [],
                    "parameters": [
                        {
                            "name": "X-Metrics-Token",
                            "in": "header",
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {"description": "OK"},
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
            "/openapi.json": {
                "get": {
                    "summary": "OpenAPI spec",
                    "security": [],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/docs": {
                "get": {
                    "summary": "API documentation page",
                    "security": [],
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
        "security": [{"bearerAuth": []}],
    }
