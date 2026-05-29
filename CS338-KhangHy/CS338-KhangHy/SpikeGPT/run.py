########################################################################################################
# The RWKV/SpikeGPT Language Model - Inference Script with HeadQK & Tool Calling Support
########################################################################################################

import os, sys, glob
import torch
import torch.nn.functional as F
import numpy as np
import json

# Cấu hình môi trường
try:
    os.environ["CUDA_VISIBLE_DEVICES"] = sys.argv[1]
except:
    pass
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cuda.matmul.allow_tf32 = True
np.set_printoptions(precision=4, suppress=True, linewidth=200)

os.environ["RWKV_HEAD_QK_DIM"] = "256"

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.model import GPT, GPTConfig
from src.utils import TOKENIZER
from src.spikingjelly.clock_driven import functional

# 1. CẤU HÌNH MÔ HÌNH VÀ TẢI CHECKPOINT
n_layer = 18
n_embd = 768
ctx_len = 1024
vocab_size = 50277

# Tìm checkpoint
best_ckpt = '/content/drive/MyDrive/UIT/HK6/CS338-NhanDang/SpikeGPT/256(best).pth'
if not os.path.exists(best_ckpt):
    ckpt_dir = "updated_2_model_weights"
    files = glob.glob(os.path.join(ckpt_dir, "*.pth"))
    if files:
        best_ckpt = max(files, key=os.path.getmtime)
    else:
        print(f"Cảnh báo: Không tìm thấy checkpoint ở {best_ckpt}. Sẽ tạo mạng rỗng (chỉ để test code).")
        best_ckpt = None

config = GPTConfig(vocab_size=vocab_size, ctx_len=ctx_len, model_type='RWKV', n_layer=n_layer, n_embd=n_embd)
model = GPT(config)

if os.path.exists(best_ckpt):
    w = torch.load(best_ckpt, map_location='cpu')
    model.load_state_dict(w)
else:
    print(f"[CẢNH BÁO] Không tìm thấy file {best_ckpt}. Đang chạy với tạ (weights) ngẫu nhiên!")

model = model.cuda()
model.eval()

# 2. TẢI TOKENIZER
WORD_NAME = ["20B_tokenizer.json", "20B_tokenizer.json"]
tokenizer = TOKENIZER(WORD_NAME, UNKNOWN_CHAR=None)

def build_prompt(user_input):
    prompt = f"<|im_start|>system\nHãy thực hiện theo yêu cầu<|im_end|>\n<|im_start|>user\n{user_input}<|im_end|>\n<|im_start|>assistant\n"
    return prompt

test_cases = [
    "Hủy cho mình cái đơn hàng mã #99812 nhé.",
    "Mình muốn đặt 5 cái điện thoại iPhone-15-Pro, giao đến số 10 Phạm Ngọc Thạch, Quận 3, TP.HCM.",
    "Thống kê doanh thu từ ngày 2024-01-01 đến 2024-03-31 cho sếp xem nha.",
    "Chào em, hôm qua chị có đặt đơn ORD-776, nhưng chị nhập sai địa chỉ. Đổi lại số lượng thành 2 cho chị nhé.",
    "Kiểm tra xem mã SP-990 còn hàng không em?"
]

MAX_NEW_TOKENS = 200

print(f"\nBắt đầu chạy test {len(test_cases)} kịch bản (HeadQK, $O(N^2)$ Inference)...\n")
print("="*50)

with torch.no_grad():
    for i, user_input in enumerate(test_cases, 1):
        prompt = build_prompt(user_input)
        ctx = tokenizer.tokenizer.encode(prompt)
        
        generated_text = ""
        
        # BƯỚC SINH VĂN BẢN TỰ ĐỘNG
        for step in range(MAX_NEW_TOKENS):
            # Cắt bớt nếu vượt ngưỡng cửa sổ
            ctx_crop = ctx[-ctx_len:]
            idx = torch.tensor([ctx_crop], dtype=torch.long).cuda()
            
            # QUAN TRỌNG: Phải reset trạng thái mạng Spiking Neural Network cho mỗi bước chạy lại từ đầu!
            functional.reset_net(model)
            
            logits = model(idx) # Logits có chiều: (Batch, Time, Vocab)
            
            # Greedy search: Lấy token cuối cùng
            next_token = int(torch.argmax(logits[0, -1, :]))
            ctx.append(next_token)

            # Giải mã
            char = tokenizer.tokenizer.decode([next_token])
            if '\ufffd' not in char: # Kiểm tra Unicode
                generated_text += char
                
                # Điều kiện dừng
                if "<|im_end|>" in generated_text:
                    generated_text = generated_text.replace("<|im_end|>", "").strip()
                    break
        
        print(f"TEST {i}: {user_input}")
        print(f"AI TRẢ LỜI:\n{generated_text.strip()}")
        print("-" * 50)

print("\nĐã test xong toàn bộ!")