1|
2|import torch
3|import torch.nn as nn
4|import numpy as np
5|from flask import Flask, request, jsonify, render_template
6|from flask_cors import CORS
7|from PIL import Image, ImageOps
8|import base64
9|import io
10|
11|app = Flask(__name__)
12|CORS(app)
13|
14|# --- Model Architecture ---
15|class CNN(nn.Module):
16|    def __init__(self):
17|        super(CNN, self).__init__()
18|        self.conv = nn.Sequential(
19|            nn.Conv2d(1, 32, 3, padding=1),
20|            nn.ReLU(),
21|            nn.MaxPool2d(2),
22|            nn.Conv2d(32, 64, 3, padding=1),
23|            nn.ReLU(),
24|            nn.MaxPool2d(2)
25|        )
26|        self.fc = nn.Sequential(
27|            nn.Flatten(),
28|            nn.Linear(64 * 7 * 7, 128),
29|            nn.ReLU(),
30|            nn.Dropout(0.5),
31|            nn.Linear(128, 10)
32|        )
33|    def forward(self, x):
34|        x = self.conv(x)
35|        return self.fc(x)
36|
37|# --- Load Model ---
38|DEVICE = torch.device("cpu")
39|model = CNN().to(DEVICE)
40|model.load_state_dict(torch.load("/home/cxiong/mnist_progression/mnist_cnn.pth"))
41|model.eval()
42|
43|def mnist_ify(img_np):
44|    img = Image.fromarray(img_np.astype('uint8')).convert('L')
45|    img = ImageOps.invert(img)
46|    img = img.point(lambda x: 255 if x > 128 else 0)
47|    bbox = img.getbbox()
48|    if bbox:
49|        img = img.crop(bbox)
50|        padding = int(max(img.width, img.height) * 0.1)
51|        img = ImageOps.expand(img, border=padding, fill=0)
52|    img = img.resize((28, 28), Image.Resampling.LANCZOS)
53|    img_tensor = torch.from_numpy(np.array(img).astype(np.float32)) / 255.0
54|    img_tensor = (img_tensor - 0.1307) / 0.3081
55|    return img_tensor.unsqueeze(0).unsqueeze(0).to(DEVICE), img
56|
57|@app.route('/')
58|def index():
59|    return render_template('index.html')
60|
61|@app.route('/predict', methods=['POST'])
62|def predict():
63|    data = request.json
64|    if not data or 'image' not in data:
65|        return jsonify({'error': 'No image provided'}), 400
66|    
67|    # Decode base64 image
68|    img_data = data['image'].split(',')[1]
69|    img_bytes = base64.b64decode(img_data)
70|    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
71|    img_np = np.array(img)
72|
73|    try:
74|        img_tensor, debug_img = mnist_ify(img_np)
75|        with torch.no_grad():
76|            logits = model(img_tensor)
77|            probs = torch.softmax(logits, dim=1)[0]
78|            prediction = torch.argmax(probs).item()
79|        
80|        # Convert debug image to base64 to send back to UI
81|        buffered = io.BytesIO()
82|        debug_img.save(buffered, format="PNG")
83|        debug_base64 = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
84|        
85|        return jsonify({
86|            'prediction': prediction,
87|            'confidence': [round(float(p), 3) for p in probs],
88|            'debug_image': debug_base64
89|        })
90|    except Exception as e:
91|        return jsonify({'error': str(e)}), 500
92|
93|if __name__ == '__main__':
94|    app.run(host='0.0.0.0', port=5050)
95|