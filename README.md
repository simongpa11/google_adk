# Google ADK - Gmail Agent

Este proyecto contiene un agente inteligente que automatiza las respuestas de Gmail basándose en el contexto de un documento de Google Docs utilizando la IA de Gemini.

## Arquitectura del Sistema

```mermaid
graph TD
    subgraph "Google Cloud & APIs"
        Gmail[Gmail API]
        Docs[Google Docs API]
    end

    subgraph "Local Agent (Python)"
        Script[gmail_agent.py]
        Env[.env - API Keys]
        Creds[credentials.json / token.json]
    end

    subgraph "AI Model"
        Gemini[Gemini 1.5 Flash / 2.0]
    end

    %% Flow
    Sender((Remitente: simon.garcia@aquaservice.com)) -->|Envía Email| Gmail
    Script -->|1. Busca correos no leídos| Gmail
    Gmail -->|2. Devuelve contenido del email| Script
    Script -->|3. Lee contexto| Docs
    Docs -->|4. Devuelve información| Script
    Script -->|5. Envía Prompt + Contexto| Gemini
    Gemini -->|6. Genera respuesta| Script
    Script -->|7. Envía respuesta| Gmail
    Gmail -->|8. Respuesta enviada| Sender
    Script -->|9. Marcar como leído| Gmail
```

## Configuración
1. Crea un entorno virtual: `python -m venv .venv`
2. Instala dependencias: `pip install -r requirements.txt`
3. Configura el archivo `.env` con tus claves.
4. Añade tu `credentials.json` en la raíz.
5. Ejecuta: `python gmail_agent.py`
