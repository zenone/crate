from fastapi import FastAPI

app = FastAPI(title="App")


@app.get("/health")
def health():
    return {"ok": True}
