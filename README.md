# local-model

Notebooks for running and fine-tuning AI models on a **Google Colab** GPU.

## How to run one

1. Tap a notebook link below (sign in with your Google account that has Colab).
   If Colab can't find it, the repo is private — authorize GitHub when it asks.
2. *Runtime → Change runtime type* → pick a GPU (T4 works; L4 / A100 are faster).
3. *Runtime → Run all*.

On a phone, switch the browser to *Desktop site* if Colab's menus are missing, and keep the tab
in front while it runs.

## Notebooks

| Notebook | What it does |
|---|---|
| [Run a model](https://colab.research.google.com/github/akshargupta/workout-bot/blob/local-model/notebooks/run_a_model.ipynb) | Downloads an open chat model (Qwen3-4B by default) to the GPU and lets you chat with it |
| [Text in boxes](https://colab.research.google.com/github/akshargupta/workout-bot/blob/local-model/notebooks/text_in_boxes.ipynb) | MOSS-Image: give a scene + boxes of exact text / objects, get an image with each placed in its box. **A100** (or L4) |
