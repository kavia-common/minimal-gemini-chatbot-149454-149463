from app import app

if __name__ == "__main__":
    # Bind to 0.0.0.0 for container/dev accessibility and use port 3001 to match frontend
    app.run(host="0.0.0.0", port=3001)
