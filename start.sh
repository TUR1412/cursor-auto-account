#!/bin/bash

# Start the Python application
waitress-serve --listen=0.0.0.0:8001 wsgi:app
