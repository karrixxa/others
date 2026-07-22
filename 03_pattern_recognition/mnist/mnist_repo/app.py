
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
        return "No input", None, None
    img_np = image.get('composite', image) if isinstance(image, dict) else image
    try:
        img_tensor, debug_img = mnist_ify(img_np)
        with torch.no_grad():
            logits = model(img_tensor)
            probs = torch.softmax(logits, dim=1)[0]
            prediction = torch.argmax(probs).item()
        confidences = {str(i): float(probs[i]) for i in range(10)}
        return f"Prediction: {prediction}", confidences, debug_img
    except Exception as e:
        return f"Error: {str(e)}", None, None

# --- UI Layout ---
with gr.Blocks(title="MNIST Digit Guesser") as demo:
    gr.Markdown("### ✍️ Draw a Digit")
    
    with gr.Row():
        with gr.Column(scale=1):
            # type="numpy" ensures we get the array and avoids complex layering issues
            # We keep it simple to avoid triggering the tool-selection prompt
            canvas = gr.Sketchpad(label="Canvas", type="numpy", layers=False)
            
        with gr.Column(scale=1):
            res_text = gr.Textbox(label="Prediction")
            res_conf = gr.Label(label="Confidence")
            res_debug = gr.Image(label="Model's View (28x28)")

    # Real-time update
    canvas.change(fn=predict_digit, inputs=canvas, outputs=[res_text, res_conf, res_debug])

if __name__ == "__main__":
    demo.launch(share=True)
