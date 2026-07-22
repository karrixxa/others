# MNIST Digit Identifier Summery

**Document:** `Documents/Paper/Mnist_Summery.md`
**Period covered:** 2026-06-09 → 2026-06-10 (primary); secondary exploration per `Summeries/summery.txt`
**Scope:** Canvas drawing UI + FastAPI inference for handwritten digit classification — not production promotion docs.

**Cross-reference:** Brief mention in **`Internship_Summery.md`** Era 2 (2026-06-09) as secondary exploration alongside Ping-PONG web pivot.

## 1. Title / meta

| Field | Value |
|---|---|
| Document name | **MNIST Digit Identifier Summery** (intentional spelling: Summery) |
| Period | 2026-06-09 → 2026-06-10 |
| Primary workspace | `/home/prodrig/Documents/Mnist_project` |
| Path note | User typo **Minst** → actual folder **`Mnist_project`** |
| Version control | None (no git repository) |
| Source authority | Project files + `Internship_Summery.md` Era 2 cross-reference |
| Internship context | Started briefly 2026-06-09 during Ping-PONG Era 2; no follow-up in internship daily summaries |

## 2. Introduction

The MNIST Digit Identifier is a small, end-to-end machine-learning demo built during the internship as a side exploration on the same day the Ping-PONG project pivoted to a web architecture (**2026-06-09**). Its purpose is straightforward: a person draws a digit in a browser, the drawing is sent to a Python server, and a neural network returns which digit (0–9) it thinks was drawn, along with confidence scores.

**What problem it solves.** Classical MNIST classification is usually studied as a notebook exercise—load the dataset, train a model, print accuracy. This project turns that into something you can *use*: a white drawing pad, a Predict button, and live results. It answers “can we take a trained digit model and serve it over HTTP on the Hermes cluster so a human can probe it interactively?”

**How the pieces fit together.** There are three layers:

1. **Frontend** (`frontend/index.html`) — a 280×280 HTML5 canvas with mouse and touch drawing, Clear / Predict controls, and a results panel. Strokes are black ink on a deliberately white background (transparent canvas would look black to the server).
2. **API** (`app/main.py`) — a **FastAPI** app on port **10000** that serves the HTML at `/`, accepts `POST /predict` with a base64 PNG, and exposes `GET /last_processed` so you can inspect the exact 28×28 image the model saw.
3. **Model** (`model/mlp_model.py` + `data/mlp_mnist.pth`) — a three-layer multilayer perceptron (**MNIST_MLP**) trained offline by `model/train.py` on the official torchvision MNIST train set, then loaded once at server startup for CPU inference.

**Where it sits in the internship.** It was never the main line of work. `Summeries/summery.txt` and `Internship_Summery.md` list it as a secondary exploration beside Ping-PONG’s web pivot and hardware audits. There is no git history, no README, an empty `requirements.txt`, and no follow-up entries in later daily/weekly summaries. The surviving tree under `/home/prodrig/Documents/Mnist_project` is the full story: train script, weights, FastAPI server, and canvas UI.

**What a reader should take away.** This is a compact “draw → preprocess → classify → explain” loop. It teaches the practical gap between clean MNIST training tensors and messy user drawings—especially the **train vs serve preprocessing mismatch** documented in §3—and shows a minimal FastAPI + PyTorch serving pattern on cluster IP **10.30.0.39:10000** (hardcoded in the frontend’s `fetch` URL).

## 3. ML specification

The learning side of the project is intentionally simple: a fully connected network on flattened 28×28 grayscale digits, trained for a few epochs with Adam, then frozen for the web demo.

**Model architecture (`MNIST_MLP`).**  
Each input image is treated as a vector of **784** pixels (28×28). The network is three linear stages:

- **fc1:** 784 → **512**, followed by **ReLU**
- **fc2:** 512 → **256**, followed by **ReLU**
- **fc3:** 256 → **10** logits (one per digit 0–9), **no** activation on the output

The forward pass flattens batched tensors with `view(-1, 784)` so both `(batch, 1, 28, 28)` training batches and a single flattened inference vector work. Training uses **`CrossEntropyLoss`**, which applies log-softmax internally; at inference time `app/main.py` applies **`softmax`** explicitly to turn logits into probabilities for the UI.

**Training procedure (`model/train.py`).**  
Hyperparameters are fixed in the script: **batch size 64**, **Adam** with learning rate **0.001**, **5 epochs**, device auto-selected (`cuda` if available, else `cpu`). Data comes from **`torchvision.datasets.MNIST`** under `./data_temp`, with train and test splits. The only transform is **`transforms.ToTensor()`**, which maps pixel values into **[0, 1]**—there is no random crop, no inversion, and no OpenCV pipeline at train time. After each training run the script evaluates on the full test set, prints **“Final Accuracy on Test Set: …”** to stdout, and saves weights to **`data/mlp_mnist.pth`**. That accuracy number is **not written to a file**; re-running train is the only way to recover it from this tree.

**Inference preprocessing (`preprocess_image` in `app/main.py`).**  
User drawings are not MNIST samples. The server therefore runs a heavier pipeline before the MLP:

1. Strip an optional `data:image/...;base64,` prefix and decode the PNG.  
2. Convert to grayscale (**PIL** `L` mode).  
3. If the mean pixel value is **> 127** (light background), **invert** so ink is bright on dark—closer to MNIST’s usual polarity.  
4. Find the non-zero bounding box, **crop** to the stroke, and **pad to a square** centered in a zero canvas.  
5. **Resize** to 28×28 with `cv2.INTER_AREA`.  
6. **Gaussian blur** (3×3), then **binary threshold** at 127.  
7. Save that binary image to **`data/last_processed.png`** for debugging.  
8. Convert to **float32 / 255**, flatten, and wrap as a batch tensor of shape `(1, 784)`.

**Train vs serve gap.** Training sees clean, centered MNIST digits via ToTensor only. Serving sees freehand strokes that are inverted, cropped, padded, blurred, and thresholded. That gap is intentional for usability (drawings look nothing like the dataset otherwise), but it means test-set accuracy from `train.py` does **not** guarantee canvas accuracy. Readers debugging wrong predictions should inspect `/last_processed` before blaming the MLP weights.

**Stack.** Training and inference depend on **PyTorch**, **torchvision**, **NumPy**, **OpenCV (`cv2`)**, **Pillow**, **FastAPI**, **Uvicorn**, and **Pydantic**. Those packages are used in code but not listed in the empty `requirements.txt`.

## 4. Features & API

The product surface is a single-page drawing tool backed by three HTTP endpoints on **`0.0.0.0:10000`**.

**Drawing experience.**  
The page title is “MNIST Identifier.” The canvas is **280×280** pixels with a green border and white fill. Line style is round caps, width **15**, black stroke—thick enough that after downsampling to 28×28 the digit remains visible. Mouse and touch events drive the same draw path (`touch-action: none` avoids scroll while drawing). **Clear** repaints white and resets the result panel to “?”. **Predict** freezes the UI briefly (“Thinking…”), posts the canvas as a PNG data URL, then shows the top digit and a top-3 breakdown.

**`GET /`**  
Returns `frontend/index.html` as a static file. Opening the server root loads the full UI without a separate static file server.

**`POST /predict`**  
Body is JSON matching Pydantic model `ImageRequest`: `{ "image": "<base64 or data-URL string>" }`. The handler runs `preprocess_image`, evaluates the MLP under `torch.no_grad()`, applies softmax, and uses `topk(..., 3)`. Response shape:

- `prediction` — integer best digit  
- `top_3` — list of `{ "digit": int, "confidence": float }` for the three highest probabilities  

Failures in decode or preprocess surface as HTTP **400** with the exception message. The frontend currently posts to the hardcoded cluster URL **`http://10.30.0.39:10000/predict`**, so local browsing only works when that host/port is reachable (or the URL is edited).

**`GET /last_processed`**  
If `data/last_processed.png` exists (written on every successful preprocess), returns that PNG; otherwise **404**. This is the main debugging feature: compare what you drew to the binary 28×28 the network actually classified.

**Operational details.**  
CORS is configured with **`allow_origins=["*"]`** (and allow-credentials / all methods and headers)—appropriate for a short-lived cluster demo, not for production. The `__main__` block registers **SIGINT/SIGTERM** handlers so Uvicorn exits cleanly, then binds **`host="0.0.0.0"`** and **`port=10000`** so other machines on the cluster network can hit the API.

**End-to-end flow.**  
Draw on canvas → `canvas.toDataURL('image/png')` → `POST /predict` → invert/crop/pad/blur/threshold → `MNIST_MLP` → softmax top-3 → UI shows “Digit: N” and confidence percentages. Optionally open `/last_processed` to verify preprocessing.

## 5. Source appendix

| Path | Role |
|---|---|
| `app/main.py` | FastAPI server, `preprocess_image`, `/predict`, `/last_processed` |
| `model/mlp_model.py` | `MNIST_MLP` (784→512→256→10) |
| `model/train.py` | 5-epoch Adam training; saves `data/mlp_mnist.pth` |
| `frontend/index.html` | Canvas UI; fetch to `10.30.0.39:10000/predict` |
| `data/mlp_mnist.pth` | Trained weights |
| `data/last_processed.png` | Last inference debug image (created at runtime) |
| `data_temp/MNIST/` | Downloaded torchvision MNIST raw files |
| `requirements.txt` | Present but **empty** |
| `Internship_Summery.md` Era 2 | Internship mention as secondary exploration |

**Known gaps:** no README, no git, test accuracy not persisted, no internship follow-up after Jun 9–10.

*End of Mnist_Summery. Filename spelling intentional. Do not treat as authoritative for Ping-PONG or D&D work — see sibling Summery documents.*
