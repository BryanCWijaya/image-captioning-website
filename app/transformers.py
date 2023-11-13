from transformers import pipeline
from PIL import Image

captioners = {
    "vit-indobert": pipeline("image-to-text",model="models/vit-base-patch16-224 indobert-base-p1 batch_8 epoch_3"),
    # "dinov2-indobert": pipeline("image-to-text", model="models/dinov2-base indobert-base-p1 batch_8 epoch_3"),
    # "deit-indobert": pipeline("image-to-text", model="models/deit-base-distilled-patch16-224 indobert-base-p1 batch_8 epoch_3"),
    # "vit-gpt2": pipeline("image-to-text", model="nlpconnect/vit-gpt2-image-captioning"),
}

def generate_caption(image, model):
    image = Image.open(image.stream)    # convert flask image to PIL image
    captioner = captioners[model]
    return captioner(image)[0]['generated_text']
