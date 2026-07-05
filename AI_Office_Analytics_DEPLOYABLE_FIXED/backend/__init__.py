"""
AI Office Analytics — backend package.

Exposing this as a real package (rather than a loose folder of sibling
modules) is what lets the app be launched in a deployment-standard way:

    gunicorn backend.app:app

from the project root, which is what Render (see render.yaml/Procfile)
uses to start the service.
"""
