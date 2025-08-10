# Utilise une image Python légère
FROM python:3.11-slim

# Crée un dossier de travail
WORKDIR /app

# Copie les fichiers backend et frontend dans le container
COPY backend ./backend
COPY frontend ./frontend

# Installe les dépendances backend
RUN pip install --no-cache-dir -r backend/requirements.txt

# Expose le port
EXPOSE 8000

# Commande pour lancer l'application
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
