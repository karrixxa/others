
import gradio as gr
import torch
import torch.nn as nn
import numpy as np
from PIL import Image, ImageOps

# --- Model Architecture ---
class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, 10)
        )
    def forward(self, x):
        x = self.conv(x)
        return self.fc(x)

# --- Load Model ---
DEVICE = torch.device("cpu")
model = CNN().to(DEVICE)
model.load_state_dict(torch.load("/home/cxiong/mnist_progression/mnist_cnn.pth"))
model.eval()

def mnist_ify(img_np):
    img = Image.fromarray(img_np.astype('uint8')).convert('L')
    img = ImageOps.invert(img)
    img = img.point(lambda x: 255 if x > 128 else 0)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        padding = int(max(img.width, img.height) * 0.1)
        img = ImageOps.expand(img, border=padding, fill=0)
    img = img.resize((28, 28), Image.Resampling.LANCZOS)
    img_tensor = torch.from_numpy(np.array(img).astype(np.float32)) / 255.0
    img_tensor = (img_tensor - 0.1307) / 0.3081
    return img_tensor.unsqueeze(0).unsqueeze(0).to(DEVICE), img

def predict_digit(image):
    if image is None:
        return "...", None, None
    img_np = image.get('composite', image) if isinstance(image, dict) else image
    try:
        img_tensor, debug_img = mnist_ify(img_np)
        with torch.no_grad():
            logits = model(img_tensor)
            probs = torch.softmax(logits, dim=1)[0]
            prediction = torch.argmax(probs).item()
        confidences = {str(i): float(probs[i]) for i in range(10)}
        return f"{prediction}", confidences, debug_img
    except Exception as e:
        return "Error", None, None

# --- Custom CSS for "Prettier" and "Smaller" Look ---
custom_css = """
.gradio-container { max-width: 800px !important; margin: auto !important; }
.predict-box { text-align: center; font-size: 2rem !important; font-weight: bold !important; }
.model-view { border: 2px solid #ddd !important; border-radius: 10px !important; }
#canvas-component { border-radius: 15px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; }
"""

with gr.Blocks(css=custom_css, title="MNIST Digit Guesser") as demo:
    gr.Markdown("<center><h1>✍️ MNIST Digit Guesser</h1></center>")
    
    with gr.Row():
        with gr.Column(scale=1):
            # layers=False simplifies the UI significantly
            canvas = gr.Sketchpad(label="Draw here", type="numpy", layers=False, elem_id="canvas-component")
            
        with gr.Column(scale=1):
            with gr.Row():
                res_text = gr.Textbox(label="Prediction", elem_classes=["predict-box"], placeholder="...")
            res_conf = gr.Label(label="Confidence")
            res_debug = gr.Image(label="Model's View", elem_classes=["model-view"])

    canvas.change(fn=predict_digit, inputs=canvas, outputs=[res_text, res_conf, res_debug])

if __name__ == "__main__":
    demo.launch(share=True)
