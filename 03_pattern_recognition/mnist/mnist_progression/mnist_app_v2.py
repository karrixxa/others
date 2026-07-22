import gradio as gr
import torch
import torch.nn as nn
import numpy as np
from PIL import Image, ImageOps

# ── Model ──────────────────────────────────────────────────────────────────────

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

DEVICE = torch.device("cpu")
model = CNN().to(DEVICE)
model.load_state_dict(torch.load("/home/cxiong/mnist_progression/mnist_cnn.pth", map_location=DEVICE))
model.eval()

# ── Inference ──────────────────────────────────────────────────────────────────

def predict(image):
    if image is None:
        return None, None

    img_np = image.get("composite", image) if isinstance(image, dict) else image
    if img_np is None or img_np.max() == 0:
        return None, None

    # MNIST-ify: grayscale → invert → threshold → crop tight → pad → 28×28
    img = Image.fromarray(img_np.astype("uint8")).convert("L")
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

    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=1)[0].cpu().numpy()

    confidences = {str(i): float(probs[i]) for i in range(10)}

    # Upscale 28×28 → 112×112 for display (pixelated but clear)
    model_view = img.resize((112, 112), Image.Resampling.NEAREST)
    model_view_rgb = Image.fromarray(np.array(model_view)).convert("RGB")

    return confidences, model_view_rgb

# ── CSS ────────────────────────────────────────────────────────────────────────

CSS = """
/* Page */
.gradio-container {
    max-width: 780px !important;
    margin: 0 auto !important;
    font-family: 'Inter', sans-serif !important;
    background: #0f0f13 !important;
}

/* Header */
.header {
    text-align: center;
    padding: 32px 0 8px;
}
.header h1 {
    font-size: 1.9rem;
    font-weight: 700;
    color: #f0f0f0;
    letter-spacing: -0.5px;
    margin: 0;
}
.header p {
    color: #666;
    font-size: 0.85rem;
    margin: 6px 0 0;
}

/* Cards */
.card {
    background: #18181f;
    border: 1px solid #2a2a35;
    border-radius: 14px;
    padding: 20px;
}

/* Canvas label override */
.canvas-label .label-wrap { display: none !important; }

/* Confidence label rows */
.label-wrap span { color: #ccc !important; font-size: 0.82rem !important; }

/* Model view image — pixelated rendering */
.model-view img {
    image-rendering: pixelated;
    border-radius: 8px;
    width: 100% !important;
    border: 1px solid #2a2a35;
}

/* Section headings */
.section-title {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: #555;
    text-transform: uppercase;
    margin-bottom: 10px;
}
"""

# ── UI ─────────────────────────────────────────────────────────────────────────

with gr.Blocks(css=CSS, title="Digit Guesser") as demo:

    gr.HTML("""
        <div class="header">
            <h1>Digit Guesser</h1>
            <p>Draw any digit 0 – 9. The CNN reads it live.</p>
        </div>
    """)

    with gr.Row(equal_height=False):

        # Left — canvas
        with gr.Column(scale=5):
            gr.HTML('<div class="section-title">Draw</div>')
            with gr.Group(elem_classes=["card"]):
                canvas = gr.Sketchpad(
                    label="",
                    type="numpy",
                    layers=False,
                    elem_classes=["canvas-label"],
                    height=320,
                )

        # Right — outputs
        with gr.Column(scale=4):

            gr.HTML('<div class="section-title">Confidence</div>')
            with gr.Group(elem_classes=["card"]):
                confidence = gr.Label(
                    label="",
                    num_top_classes=10,
                )

            gr.HTML('<div class="section-title" style="margin-top:16px">What the model sees</div>')
            with gr.Group(elem_classes=["card", "model-view"]):
                model_view = gr.Image(
                    label="",
                    show_label=False,
                    height=140,
                )

    canvas.change(fn=predict, inputs=canvas, outputs=[confidence, model_view])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=8000, share=True)
