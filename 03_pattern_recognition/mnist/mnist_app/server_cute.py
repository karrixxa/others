
import torch
import torch.nn as nn
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from PIL import Image, ImageOps
import base64
import io

app = Flask(__name__)
CORS(app)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400
    
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    img_np = np.array(img)

    try:
        img_tensor, debug_img = mnist_ify(img_np)
        with torch.no_grad():
            logits = model(img_tensor)
            probs = torch.softmax(logits, dim=1)[0]
            prediction = torch.argmax(probs).item()
        
        buffered = io.BytesIO()
        debug_img.save(buffered, format="PNG")
        debug_base64 = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
        
        return jsonify({
            'prediction': prediction,
            'confidence': [round(float(p), 3) for p in probs],
            'debug_image': debug_base64
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
