import random
import copy
import re
import json
import pandas as pd
from typing import List, Tuple, Dict, Any
import calendar
from sklearn.model_selection import train_test_split
from transformers import PreTrainedTokenizerFast

# --- Tokenizer setup ---
chat_template = """
{%- set default_system = 'Hãy thực hiện theo yêu cầu' -%}
{%- set ns = namespace(system=default_system) -%}
{%- if messages[0]['role'] == 'system' -%}{%- set ns.system = messages[0]['content'] -%}{%- endif -%}
{{- '<|im_start|>system\n' -}}
{{- ns.system }}
{%- if tools %}
Bạn có thể dùng các công cụ sau:
<tools>
{%- for tool in tools %}
{{- '\n' + (tool | tojson) }}
{%- endfor %}
</tools>
Khi cần gọi công cụ, trả về:
<tool_call>
{"name": <tên-hàm>, "arguments": <tham-số>}
</tool_call>
{%- endif %}
{{- '<|im_end|>\n' }}
{%- for message in messages %}
{%- if loop.first and message['role'] == 'system' %}
{%- continue %}
{%- endif %}
{%- if message['role'] == 'tool' %}
{%- if loop.first or messages[loop.index0-1]['role'] != 'tool' %}
{{- '<|im_start|>user\n' }}
{%- endif %}
{{- '<tool_response>\n' + message['content'] + '\n</tool_response>' }}
{%- if loop.last or messages[loop.index0+1]['role'] != 'tool' %}
{{- '<|im_end|>\n' }}
{%- endif %}
{%- elif message['role'] == 'assistant' %}
{{- '<|im_start|>assistant' }}
{%- if message.get('content') %}{{- '\n' + message['content'] }}{% endif %}
{%- for tc in message.get('tool_calls', []) %}
{%- set f = tc.get('function', tc) %}
{{- '\n<tool_call>\n{"name": "' + f['name'] + '", "arguments": ' + (f['arguments'] | tojson) + '}\n</tool_call>' }}
{%- endfor %}
{{- '<|im_end|>\n' }}
{%- else %}
{{- '<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>\n' }}
{%- endif %}
{%- endfor %}
{%- if add_generation_prompt %}{{- '<|im_start|>assistant\n' }}{% endif %}
""".strip()

# --- Helper ---
def _random_quantity(original: int, *, low: int = 1, high: int = 1000) -> int:
    candidate = random.randint(low, high)
    while candidate == original:
        candidate = random.randint(low, high)
    return candidate

def _random_date_pair(year: int = 2026, month: int = None) -> Tuple[str, str]:
    if month is None:
        month = random.randint(1, 12)
    _, max_days = calendar.monthrange(year, month)
    day1 = random.randint(1, max_days)
    day2 = random.randint(1, max_days)
    start_day = min(day1, day2)
    end_day = max(day1, day2)
    return f"{year}-{month:02d}-{start_day:02d}", f"{year}-{month:02d}-{end_day:02d}"

# --- Augmentation logic ---
def augment(sample: Dict[str, Any], addresses: List[str], n_variations: int = 5) -> List[Dict[str, Any]]:
    augmented_samples = []
    for i in range(n_variations):
        new_sample = copy.deepcopy(sample)
        new_sample["id"] = f"{sample['id']}_aug_{i}"
        messages = new_sample["messages"]

        user_msg_idx = next((j for j, m in enumerate(messages) if m.get("role") == "user"), None)
        assistant_tool_idx = next((j for j, m in enumerate(messages) if m.get("role") == "assistant" and m.get("tool_calls")), None)
        tool_result_idx = next((j for j, m in enumerate(messages) if m.get("role") == "tool"), None)
        final_assistant_idx = next((j for j, m in enumerate(messages) if m.get("role") == "assistant" and not m.get("tool_calls")), None)

        if user_msg_idx is None or assistant_tool_idx is None:
            break

        tool_calls = messages[assistant_tool_idx].get("tool_calls")
        if not tool_calls:
            break

        args: dict = tool_calls[0].get("arguments", {})
        user_msg: str = messages[user_msg_idx].get("content") or ""

        tool_result_data = {}
        if tool_result_idx is not None and messages[tool_result_idx].get("content"):
            try:
                tool_result_data = json.loads(messages[tool_result_idx]["content"])
            except (json.JSONDecodeError, TypeError):
                pass

        replacements: List[Tuple[str, str]] = []

        if args.get("order_id") is not None:
            old_oid = str(args["order_id"])
            if old_oid in user_msg:
                prefix = re.match(r"^[A-Za-z]+", old_oid)
                prefix_str = prefix.group() if prefix else ""
                new_oid = f"{prefix_str}{random.randint(1000, 9999)}"
                args["order_id"] = new_oid
                replacements.append((old_oid, new_oid))
                if isinstance(tool_result_data, dict) and "order_id" in tool_result_data:
                    tool_result_data["order_id"] = new_oid

        if args.get("quantity") is not None:
            old_qty = str(args["quantity"])
            if old_qty in user_msg:
                new_qty = str(_random_quantity(int(old_qty)))
                args["quantity"] = int(new_qty)
                replacements.append((old_qty, new_qty))

        if args.get("product_id") is not None:
            old_pid = str(args["product_id"])
            if old_pid in user_msg:
                prefix = re.match(r"^[A-Za-z]+", old_pid)
                prefix_str = prefix.group() if prefix else ""
                new_pid = f"{prefix_str}{random.randint(1000, 9999)}"
                args["product_id"] = new_pid
                replacements.append((old_pid, new_pid))
                if isinstance(tool_result_data, dict) and "product_id" in tool_result_data:
                    tool_result_data["product_id"] = new_pid

        if args.get("address") is not None and addresses:
            old_addr = str(args["address"])
            if old_addr in user_msg:
                choices = [a for a in addresses if a != old_addr] or addresses
                new_addr = random.choice(choices)
                args["address"] = new_addr
                replacements.append((old_addr, new_addr))
                if isinstance(tool_result_data, dict) and "address" in tool_result_data:
                    tool_result_data["address"] = new_addr

        if args.get("start_date") is not None:
            old_start = str(args["start_date"])
            if old_start in user_msg:
                old_end = args.get("end_date") or ""
                new_start, new_end = _random_date_pair()
                args["start_date"] = new_start
                replacements.append((old_start, new_start))
                if args.get("end_date") and old_end:
                    args["end_date"] = new_end
                    replacements.append((str(old_end), new_end))

        if not replacements:
            break

        def apply_replacements(text: str) -> str:
            if not text:
                return text
            sorted_replacements = sorted(replacements, key=lambda x: len(str(x[0])), reverse=True)
            for old_val, new_val in sorted_replacements:
                old_str = str(old_val)
                new_str = str(new_val)
                if re.match(r'^[\w\-]+$', old_str):
                    pattern = rf"(?<![\w\-]){re.escape(old_str)}(?![\w\-])"
                    text = re.sub(pattern, new_str, text)
                else:
                    text = text.replace(old_str, new_str)
            return text

        messages[user_msg_idx]["content"] = apply_replacements(user_msg)
        if tool_result_idx is not None:
            if tool_result_data:
                messages[tool_result_idx]["content"] = json.dumps(tool_result_data, ensure_ascii=False)
            else:
                messages[tool_result_idx]["content"] = apply_replacements(messages[tool_result_idx].get("content", ""))
        if final_assistant_idx is not None and messages[final_assistant_idx].get("content"):
            messages[final_assistant_idx]["content"] = apply_replacements(messages[final_assistant_idx]["content"])

        augmented_samples.append(new_sample)

    return augmented_samples

def preprocessing(ds: pd.DataFrame, tokenizer: Any, addresses: List[str], max_tokens: int = 700, n_variations: int = 10) -> pd.DataFrame:
    def token_count(messages: List[Dict[str, Any]]) -> int:
        token_ids = tokenizer.apply_chat_template(messages, tokenize=True)
        return len(token_ids)

    rows: List[Dict[str, Any]] = []
    total = len(ds)
    
    # Use standard python dictionary loop for better performance over iterrows
    for i, sample in enumerate(ds.to_dict('records')):
        if i % 100 == 0:
            print(f"Processing row {i}/{total}...")
        
        if token_count(sample["messages"]) <= max_tokens:
            rows.append(sample)
            samples = augment(sample, addresses=addresses, n_variations=n_variations)
            if samples:
                rows.extend(samples)

    return pd.DataFrame(rows)

def save_jsonl(df, path: str, tokenizer) -> int:
    skipped = 0
    written = 0
    with open(path, "w", encoding="utf-8") as f:
        for _, example in df.iterrows():
            try:
                text = tokenizer.apply_chat_template(
                    example["messages"],
                    tokenize=False,
                    add_generation_prompt=False,
                )
                if not text or not text.strip():
                    skipped += 1
                    continue
                json.dump({"text": text}, f, ensure_ascii=False)
                f.write("\n")
                written += 1
            except Exception as e:
                skipped += 1
    print(f"[INFO] Saved {written} examples to {path} | Skipped: {skipped}")
    return skipped

if __name__ == "__main__":
    print("Loading tokenizer and data...")
    tokenizer = PreTrainedTokenizerFast(tokenizer_file="./SpikeGPT/20B_tokenizer.json", chat_template=chat_template)
    ds = pd.read_json("./data/agent_data1.json")

    addresses = [
        "12 Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
        "45 Lê Lợi, Phường Bến Thành, Quận 1, TP. Hồ Chí Minh",
        "78 Trần Hưng Đạo, Phường Cầu Kho, Quận 1, TP. Hồ Chí Minh",
        "23 Võ Văn Tần, Phường 6, Quận 3, TP. Hồ Chí Minh",
        "101 Đinh Tiên Hoàng, Phường 3, Quận Bình Thạnh, TP. Hồ Chí Minh",
        "56 Phan Văn Trị, Phường 10, Quận Gò Vấp, TP. Hồ Chí Minh",
        "88 Nguyễn Thị Thập, Phường Tân Phú, Quận 7, TP. Hồ Chí Minh",
        "34 Lê Văn Việt, Phường Hiệp Phú, Quận 9, TP. Hồ Chí Minh",
        "210 Quang Trung, Phường 10, Quận Gò Vấp, TP. Hồ Chí Minh",
        "67 Âu Cơ, Phường 14, Quận Tân Bình, TP. Hồ Chí Minh",
        "15 Hàng Bài, Phường Hàng Bài, Quận Hoàn Kiếm, Hà Nội",
        "92 Nguyễn Chí Thanh, Phường Láng Thượng, Quận Đống Đa, Hà Nội",
        "38 Trần Duy Hưng, Phường Trung Hoà, Quận Cầu Giấy, Hà Nội",
        "5 Kim Mã, Phường Kim Mã, Quận Ba Đình, Hà Nội",
        "120 Lê Duẩn, Phường Khâm Thiên, Quận Đống Đa, Hà Nội",
        "77 Xuân Thủy, Phường Dịch Vọng Hậu, Quận Cầu Giấy, Hà Nội",
        "49 Hoàng Quốc Việt, Phường Nghĩa Đô, Quận Cầu Giấy, Hà Nội",
        "22 Bạch Đằng, Phường Hải Châu 1, Quận Hải Châu, Đà Nẵng",
        "88 Nguyễn Văn Linh, Phường Nam Dương, Quận Hải Châu, Đà Nẵng",
        "14 Lê Duẩn, Phường Thạch Thang, Quận Hải Châu, Đà Nẵng",
        "66 Trần Phú, Phường Phước Ninh, Quận Hải Châu, Đà Nẵng",
        "31 Phan Chu Trinh, Phường Thạch Thang, Quận Hải Châu, Đà Nẵng",
        "9 Đại lộ Bình Dương, Phường Hiệp Thành, TP. Thủ Dầu Một, Bình Dương",
        "203 Nguyễn Văn Tiết, Phường Lái Thiêu, TP. Thuận An, Bình Dương",
        "57 Trần Văn Ơn, Phường Phú Lợi, TP. Thủ Dầu Một, Bình Dương",
        "18 Phạm Văn Thuận, Phường Thống Nhất, TP. Biên Hòa, Đồng Nai",
        "74 Nguyễn Ái Quốc, Phường Quang Vinh, TP. Biên Hòa, Đồng Nai",
        "32 Đồng Khởi, Phường Tân Hiệp, TP. Biên Hòa, Đồng Nai",
        "10 Hòa Bình, Phường Tân An, Quận Ninh Kiều, Cần Thơ",
        "88 Trần Văn Hoài, Phường Xuân Khánh, Quận Ninh Kiều, Cần Thơ",
        "45 Nguyễn Trãi, Phường An Hội, Quận Ninh Kiều, Cần Thơ",
        "56 Điện Biên Phủ, Phường Minh Khai, Quận Hồng Bàng, Hải Phòng",
        "23 Lê Lợi, Phường Minh Khai, Quận Hồng Bàng, Hải Phòng",
        "11 Trần Phú, Phường Hoàng Diệu, Quận Dương Kinh, Hải Phòng",
        "3 Trần Phú, Phường Lộc Thọ, TP. Nha Trang, Khánh Hòa",
        "99 Nguyễn Thiện Thuật, Phường Phương Sài, TP. Nha Trang, Khánh Hòa",
        "47 Yersin, Phường Phương Sài, TP. Nha Trang, Khánh Hòa",
        "8 Trần Phú, Phường 3, TP. Đà Lạt, Lâm Đồng",
        "52 Bùi Thị Xuân, Phường 2, TP. Đà Lạt, Lâm Đồng",
        "19 Nguyễn Văn Trỗi, Phường 2, TP. Đà Lạt, Lâm Đồng",
        "20 Lê Lợi, Phường Vĩnh Ninh, TP. Huế, Thừa Thiên Huế",
        "7 Hùng Vương, Phường Phú Nhuận, TP. Huế, Thừa Thiên Huế",
        "36 Nguyễn Huệ, Phường Phú Nhuận, TP. Huế, Thừa Thiên Huế",
        "14 Nguyễn Thị Minh Khai, Phường Lê Lợi, TP. Vinh, Nghệ An",
        "88 Trường Thi, Phường Trường Thi, TP. Vinh, Nghệ An",
        "33 Lê Thánh Tông, Phường Bạch Đằng, TP. Hạ Long, Quảng Ninh",
        "71 Trần Quốc Nghiễn, Phường Hồng Gai, TP. Hạ Long, Quảng Ninh",
        "25 Trần Hưng Đạo, Phường 1, TP. Vũng Tàu, Bà Rịa - Vũng Tàu",
        "60 Lê Hồng Phong, Phường 4, TP. Vũng Tàu, Bà Rịa - Vũng Tàu",
        "12 Hùng Vương, Phường 2, TP. Tân An, Long An",
    ]

    # Target 50,000+ samples for train, and keep ~7,600 for val. 
    # With n_variations=45, we should get around 60k-65k total samples.
    n_variations = 45
    
    print(f"Starting data augmentation with n_variations={n_variations}...")
    new_data = preprocessing(ds, tokenizer, addresses=addresses, n_variations=n_variations)
    print(f"Augmentation complete. Total samples: {len(new_data)}")
    
    print("Splitting into train/valid...")
    train_df, valid_df = train_test_split(
        new_data,
        test_size=7600,
        random_state=42,
        shuffle=True,
    )
    
    print(f"Train: {len(train_df)} | Valid: {len(valid_df)}")
    
    save_jsonl(train_df, "./data/train_tool_data.jsonl", tokenizer)
    save_jsonl(valid_df, "./data/valid_tool_data.jsonl", tokenizer)
    print("Done!")
