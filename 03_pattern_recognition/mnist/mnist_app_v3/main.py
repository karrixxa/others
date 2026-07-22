import torch
import torch.nn as nn
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps
import io

# ── Model Architectures ─────────────────────────────────────────────────────────

class CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 128), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(128, 10),
        )
    def forward(self, x):
        return self.fc(self.conv(x))

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Sequential(
            nn.Flatten(),
            nn.Linear(28 * 28, 512), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(256, 10),
        )
    def forward(self, x):
        return self.model(x)

# ── Setup ──────────────────────────────────────────────────────────────────────

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DEVICE = torch.device("cpu")
MODELS = {
    "cnn": CNN().to(DEVICE),
    "mlp": MLP().to(DEVICE),
}

# Load weights
MODELS["cnn"].load_state_dict(torch.load("/home/cxiong/mnist_progression/mnist_cnn.pth", map_location=DEVICE))
MODELS["mlp"].load_state_dict(torch.load("/home/cxiong/mnist_progression/mnist_mlp.pth", map_location=DEVICE))

for m in MODELS.values():
    m.eval()

# ── Utils ──────────────────────────────────────────────────────────────────────

def preprocess(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    img = ImageOps.invert(img)
    img = img.point(lambda p: 255 if p > 30 else 0)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        pad = int(max(img.width, img.height) * 0.2)
        img = ImageOps.expand(img, border=pad, fill=0)
    img = img.resize((28, 28), Image.Resampling.LANCZOS)
    tensor = torch.tensor(np.array(img).astype(np.float32) / 255.0)
    tensor = (tensor - 0.1307) / 0.3081
    tensor = tensor.unsqueeze(0).unsqueeze(0).to(DEVICE)
    return tensor

@app.post("/predict")
async def predict(file: UploadFile = File(...), model_type: str = Form("cnn")):
    if model_type not in MODELS:
        model_type = "cnn"
    
    img_bytes = await file.read()
    tensor = preprocess(img_bytes)
    
    with torch.no_grad():
        logits = MODELS[model_type](tensor)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
    
    ranked_indices = np.argsort(probs)[::-1]
    sorted_probs = probs[ranked_indices]
    
    results = []
    for i in range(10):
        results.append({"digit": int(ranked_indices[i]), "prob": float(sorted_probs[i])})
    
    return {"ranked": results}

app.mount("/", StaticFiles(directory="/home/cxiong/mnist_app_v3/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
