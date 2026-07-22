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
# Using absolute path from your previous setup
model.load_state_dict(torch.load("/home/cxiong/mnist_progression/mnist_cnn.pth"))
model.eval()

def process_and_predict(image):
    if image is None:
        return "...", None, None
    
    # Gradio Sketchpad returns a dict with 'composite' or a numpy array
    img_np = image.get('composite', image) if isinstance(image, dict) else image
    
    # MNIST-ify pipeline: Convert to L, invert, threshold, crop, resize
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
    img_tensor = img_tensor.unsqueeze(0).unsqueeze(0).to(DEVICE)
    
    with torch.no_grad():
        logits = model(img_tensor)
        probs = torch.softmax(logits, dim=1)[0]
        prediction = torch.argmax(probs).item()
        
    confidences = {str(i): float(probs[i]) for i in range(10)}
    return f"Digit: {prediction}", confidences, img

# --- UI Design ---
custom_css = """
.gradio-container { max-width: 900px !important; margin: auto !important; }
.predict-box { text-align: center; font-size: 2.5rem !important; font-weight: bold !important; color: #ff8fab !important; }
.tab-pane { padding: 20px !important; }
"""

with gr.Blocks(title="MNIST Cute Guesser", css=custom_css) as demo:
    gr.Markdown("<center><h1 style='color: #ff8fab;'>✍️ MNIST Digit Guesser</h1></center>")
    
    with gr.Tabs():
        with gr.TabItem("🎨 Drawing"):
            # By removing the toolbar-hiding CSS, the pen/undo/redo/delete tools are back
            canvas = gr.Sketchpad(
                label="Draw your digit here", 
                type="numpy", 
                layers=False
            )
            gr.Markdown("<p style='text-align: center;'>Use the toolbar above to draw, undo, or clear!</p>")

        with gr.TabItem("🔮 Prediction"):
            with gr.Row():
                with gr.Column():
                    res_text = gr.Textbox(label="The model thinks it is...", elem_classes=["predict-box"])
                with gr.Column():
                    res_conf = gr.Label(label="Confidence Scores")

        with gr.TabItem("🧠 Model's Eye"):
            res_debug = gr.Image(label="How the model sees your input (28x28)", height=300)
            gr.Markdown("This is the pre-processed image sent to the neural network.")

    # Reactive update: when drawing changes, update all tabs
    canvas.change(fn=process_and_predict, inputs=canvas, outputs=[res_text, res_conf, res_debug])

if __name__ == "__main__":
    # FIX: server_name="0.0.0.0" allows access from outside the local machine
    # share=True provides a public .gradio.live link if the local network is blocked
    demo.launch(
        server_name="0.0.0.0", 
        share=True 
    )
