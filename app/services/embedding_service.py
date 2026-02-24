from sentence_transformers import SentenceTransformer
from transformers import CLIPModel, AutoModel, AutoProcessor, AutoImageProcessor
import torch
from PIL import Image

class EmbeddingService:
    def __init__(self):
        self.device = "cpu"
        print("임베딩 모델 로딩 시작")
        self.bingsu_id = "Bingsu/clip-vit-large-patch14-ko"
        self.bingsu = CLIPModel.from_pretrained(self.bingsu_id).to(self.device)
        self.bingsu_processor = AutoProcessor.from_pretrained(self.bingsu_id)
        self.dino_id = "facebook/dinov2-large"
        self.dino = AutoModel.from_pretrained(self.dino_id).to(self.device)
        self.dino_processor = AutoProcessor.from_pretrained(self.dino_id)
        print("로딩 완료")

    def encode_image(self, image: Image.Image):
        with torch.no_grad():
            bingsu_input = self.bingsu_processor(image, return_tensors="pt").to(self.device)
            bingsu_outputs = self.bingsu.get_image_features(**bingsu_input)
            #print(f"Bingsu shape: {bingsu_outputs[0].shape}")
            bingsu_vec = bingsu_outputs[0][0, 0, :768].cpu().numpy().tolist()

            dino_input = self.dino_processor(image, return_tensors="pt").to(self.device)
            dino_outputs = self.dino(**dino_input)
            #print(f"DINO shape: {dino_outputs.last_hidden_state.shape}")
            dino_vec = dino_outputs.last_hidden_state[0, 0, :].cpu().numpy().tolist()
        return bingsu_vec, dino_vec

embedding_service = None

def get_embedding_service():
    global embedding_service
    if embedding_service is None:
        embedding_service = EmbeddingService()
    return embedding_service