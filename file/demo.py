import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import re
import json

# Import your ToolUseAgent and helper functions
# Make sure these are available in your environment
# from your_agent_module import ToolUseAgent, parse_tool_call_from_text
# from your_tools_module import WikipediaRetriever, evaluate, solve_equation, convert_units


import json
import re
import torch
import random # Thêm import random ở đầu file

def execute_tool_logic(tool_name, tool_args):
    """
    Xử lý thực thi giả lập cho 6 E-commerce tools.
    """
    t_name = tool_name.lower().strip()
    
    try:
        # 1. TẠO ĐƠN HÀNG (create_order)
        if t_name == "create_order":
            # Thử lấy thông tin sản phẩm và địa chỉ từ args (nếu AI bóc tách được)
            product = tool_args.get("product_id", tool_args.get("product", "Sản phẩm không xác định"))
            qty = tool_args.get("quantity", 1)
            address = tool_args.get("address", "Địa chỉ mặc định")
            
            # Giả lập tạo mã đơn hàng ngẫu nhiên
            order_id = f"ORD-{random.randint(10000, 99999)}"
            
            return {
                "status": "success",
                "action": "Tạo đơn hàng mới",
                "order_id": order_id,
                "details": f"Đã đặt {qty}x {product}",
                "delivery_to": address,
                "message": "Đơn hàng đã được ghi nhận vào hệ thống thành công."
            }

        # 2. KIỂM TRA TRẠNG THÁI ĐƠN (get_order)
        elif t_name == "get_order":
            order_id = tool_args.get("order_id", "Không xác định")
            
            # Giả lập random trạng thái
            statuses = ["Đang xử lý", "Đã lấy hàng", "Đang giao hàng", "Giao hàng thành công"]
            current_status = random.choice(statuses)
            
            return {
                "status": "success",
                "action": "Kiểm tra đơn hàng",
                "order_id": order_id,
                "current_status": current_status,
                "last_update": "2 giờ trước",
                "message": f"Đơn hàng {order_id} hiện đang ở trạng thái: {current_status}."
            }

        # 3. HỦY ĐƠN HÀNG (delete_order)
        elif t_name == "delete_order":
            order_id = tool_args.get("order_id", "Không xác định")
            
            # Logic giả lập: Nếu mã đơn dài hơn 3 ký tự thì cho hủy, không thì báo lỗi
            if len(str(order_id)) >= 3:
                return {
                    "status": "success",
                    "action": "Hủy đơn hàng",
                    "order_id": order_id,
                    "refund_status": "Đang xử lý hoàn tiền (1-3 ngày làm việc)",
                    "message": f"Đã tiếp nhận yêu cầu hủy đơn {order_id}."
                }
            else:
                return {
                    "status": "error",
                    "action": "Hủy đơn hàng",
                    "message": "Mã đơn hàng không hợp lệ. Không thể hủy."
                }

        # 4. CẬP NHẬT ĐƠN HÀNG (update_order)
        elif t_name == "update_order":
            order_id = tool_args.get("order_id", "Không xác định")
            
            # Tập hợp các trường cần update (ví dụ: address, quantity...)
            updated_fields = {k: v for k, v in tool_args.items() if k != "order_id"}
            
            return {
                "status": "success",
                "action": "Cập nhật thông vị",
                "order_id": order_id,
                "updated_fields": updated_fields if updated_fields else "Không có thay đổi",
                "message": f"Hệ thống đã cập nhật thông tin cho đơn {order_id}."
            }

        # 5. KIỂM TRA TỒN KHO (check_inventory)
        elif t_name == "check_inventory":
            product_id = tool_args.get("product_id", tool_args.get("item", "Sản phẩm không xác định"))
            
            # Giả lập số lượng ngẫu nhiên
            stock = random.randint(0, 150)
            in_stock = stock > 0
            
            return {
                "status": "success",
                "action": "Kiểm tra tồn kho",
                "product_id": product_id,
                "in_stock": in_stock,
                "quantity_available": stock,
                "warehouse_location": "Kho Tổng TP.HCM",
                "message": f"Kho còn {stock} sản phẩm." if in_stock else "Sản phẩm hiện đang tạm hết hàng."
            }

        # 6. THỐNG KÊ DOANH THU (revenue_analysis)
        elif t_name == "revenue_analysis":
            start_date = tool_args.get("start_date", "Đầu kỳ")
            end_date = tool_args.get("end_date", "Hiện tại")
            
            # Giả lập số liệu
            revenue = f"{random.randint(500, 5000):,}000 VND"
            total_orders = random.randint(100, 999)
            
            return {
                "status": "success",
                "action": "Trích xuất báo cáo doanh thu",
                "period": f"{start_date} đến {end_date}",
                "total_orders": total_orders,
                "total_revenue": revenue,
                "message": "Báo cáo doanh thu đã được tạo thành công."
            }

        # Tool không khớp
        else:
            return {
                "status": "error",
                "message": f"Hệ thống Backend không nhận diện được Tool: '{t_name}'."
            }
            
    except Exception as e:
        return {"status": "error", "message": f"Lỗi thực thi trong hệ thống giả lập: {str(e)}"}

def extract_answer(response):
    """Extract answer from response."""
    try:
        answer = response.split("\nAnswer:")[1].strip()
    except Exception:
        answer = response
    return answer


def extract_tool_usage(llm_text: str):
    """Extract tool usage patterns like ToolName[arg] from model output."""
    try:
        action = llm_text.split("\nAction:")[1].split("\nRationale:")[0]
    except Exception:
        action = llm_text
    return re.findall(r"\w+\[[^\[\]]+\]", action)


def parse_tool_call_from_text(text: str):
    """Parse <tool_call>{...}</tool_call> and return dict or None."""
    m = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception as e:
        print(f"Failed to parse tool_call JSON: {e}")
        return None




from typing import Optional, Dict, Any, List
import logging
import math
import statistics
import re
import importlib.util as importlib_util
import wikipedia

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Wikipedia language to Vietnamese
wikipedia.set_lang("vi")


def WikipediaRetriever(query: str) -> str:
    """
    Retrieve the Vietnamese summary of a Wikipedia page.

    Example:
        >>> WikipediaRetriever("Việt Nam")
    """
    try:
        page = wikipedia.page(query, auto_suggest=True)
        return page.summary

    except wikipedia.exceptions.DisambiguationError as e:
        logger.warning(f"DisambiguationError for '{query}': choosing first option.")
        try:
            page = wikipedia.page(e.options[0])
            return page.summary
        except Exception:
            return f"Nhiều kết quả: {', '.join(e.options[:5])}..."

    except wikipedia.exceptions.PageError:
        return f"Không tìm thấy bài viết cho truy vấn: {query}"

    except Exception as e:
        logger.exception("WikipediaRetriever failed")
        return f"Lỗi khi truy xuất Wikipedia: {str(e)}"


def evaluate(
    expression: str,
    variables: Optional[Dict[str, float]] = None,
    precision: int = 10
) -> Dict[str, Any]:
    """
    Evaluate a mathematical expression safely using SymPy if available,
    otherwise fall back to math-based evaluation.

    Example:
        >>> evaluate("sin(pi/4) + log(e)")
        {'result': 1.7071}
    """
    try:
        variables = variables or {}
        expression = expression.replace("^", "**").strip()

        if importlib_util.find_spec("sympy") is not None:
            import sympy as sp
            local_dict = {
                "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
                "sqrt": sp.sqrt, "log": sp.log, "exp": sp.exp,
                "pi": sp.pi, "e": sp.E, "ln": sp.log
            }

            for var in variables.keys():
                if var not in local_dict:
                    local_dict[var] = sp.Symbol(var)

            expr = sp.sympify(expression, locals=local_dict)
            if variables:
                expr = expr.subs(variables)

            result = float(sp.N(expr, precision))
            return {"result": round(result, precision)}

        else:
            # Safe fallback using math
            allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
            safe_env = {"__builtins__": None, **allowed, **variables}

            forbidden = ["__", "import", "os.", "sys.", "eval", "exec", "open"]
            if any(f in expression for f in forbidden):
                return {"error": "Unsafe expression detected."}

            result = eval(expression, safe_env, {})
            return {"result": round(float(result), precision)}

    except Exception as e:
        logger.exception("Error evaluating expression")
        return {"error": f"Error evaluating expression: {str(e)}"}

def solve_equation(
        equation: str,
        variable: str = 'x'
    ) -> Dict[str, Any]:
        """Solve a mathematical equation."""
        try:
            if importlib_util.find_spec('sympy') is None:
                error_msg = "sympy package is not available. Please install it using: pip install sympy"
                logging.error(error_msg)
                return {"error": error_msg}

            # Import sympy only when needed
            import sympy

            # Parse equation
            if '=' in equation:
                left, right = equation.split('=')
                equation = f"({left}) - ({right})"

            # Convert to SymPy expression
            x = sympy.Symbol(variable)
            try:
                expr = sympy.sympify(equation)
            except:
                from sympy.parsing.sympy_parser import parse_expr, implicit_multiplication_application, standard_transformations
                transformations = standard_transformations + (implicit_multiplication_application,)
                expr = parse_expr(equation, transformations=transformations)

            # Solve equation
            solutions = sympy.solve(expr, x)

            # Convert complex solutions to real if possible
            real_solutions = []
            for sol in solutions:
                if sol.is_real:
                    real_solutions.append(float(sol))

            return {"solutions": real_solutions} if real_solutions else {"error": "No real solutions found"}
        except Exception as e:
            error_msg = f"Error solving equation: {str(e)}"
            logging.error(error_msg)
            return {"error": error_msg}


def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert between compatible units (length or weight).

    Supported:
      - length: m, cm, mm, km, in, ft, yd, mi
      - weight: g, kg, mg, lb, oz
    """
    length_units = {
        "m": 1.0, "cm": 0.01, "mm": 0.001, "km": 1000.0,
        "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.34
    }

    weight_units = {
        "kg": 1.0, "g": 0.001, "mg": 1e-6, "lb": 0.453592, "oz": 0.0283495
    }

    systems = [length_units, weight_units]
    for sys in systems:
        if from_unit in sys:
            if to_unit not in sys:
                raise ValueError("Incompatible units (length vs weight)")
            return value * sys[from_unit] / sys[to_unit]

    raise ValueError("Unsupported units")

from transformers import (
    TrainingArguments,
    Trainer,
    TrainerCallback,
    DataCollatorForLanguageModeling,
)
from transformers import EarlyStoppingCallback

class ToolUseAgent:
    def __init__(
        self,
        model,
        tokenizer,
        tools_metadata=None,
        generation_cfg=None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.tools = tools_metadata or []


        # Generation defaults
        self.generation_cfg = generation_cfg or {
            "max_new_tokens": 1200,
            "do_sample": False,
            "temperature": 0.0,
            "top_p": 0.95,
        }

    def invoke_tool(self, tool_name, args) -> str:
        """Invoke a tool based on the function call string."""

        # Normalize tool name
        normalized = tool_name.replace("_", "").lower()

        # Tool dispatch
        if normalized in ("wikipediaretriever", "wikipediasearch"):
            return WikipediaRetriever(**args)

        elif normalized in ("evaluate", "calculator"):  
            return evaluate(**args)

        elif normalized in ("solveequation", "solve"):
            return solve_equation(**args)

        elif normalized in ("convertunits", "unitconverter"):
            return convert_units(**args)

        # Hỗ trợ E-commerce Tools
        ecommerce_tools = ["create_order", "get_order", "delete_order", "update_order", "check_inventory", "revenue_analysis"]
        if normalized in [t.replace("_", "") for t in ecommerce_tools] or tool_name.strip() in ecommerce_tools:
            res = execute_tool_logic(tool_name, args)
            return json.dumps(res, ensure_ascii=False)

        return f"Error: tool `{tool_name}` not found."

    def call_llm(self, conversations: list, add_generation_prompt=True):
        """Call the language model with the conversation history."""
        # Render chat template
        prompt_text = self.tokenizer.apply_chat_template(
            conversations,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
            tools=self.tools if self.tools else None,
        )

        # Tokenize to tensors
        encoded = self.tokenizer(prompt_text, return_tensors="pt").to(self.model.device)
        input_ids = encoded["input_ids"]
        attention_mask = encoded.get("attention_mask", None)

        # Generation arguments
        gen_kwargs = dict(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=self.generation_cfg.get("max_new_tokens", 1500),
            do_sample=self.generation_cfg.get("do_sample", False),
            temperature=self.generation_cfg.get("temperature", 0.0),
            # top_p=self.generation_cfg.get("top_p", 0.95),
            pad_token_id=self.tokenizer.eos_token_id
        )

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(**gen_kwargs)

        # Decode
        generated = outputs[0, input_ids.shape[-1] :].cpu().numpy()
        decoded = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
        return decoded

    def inference(self, question: str):
        """Run inference with tool usage capability."""
        system_prompt = (
            "Hãy trả lời câu hỏi nhanh"
        )

        conversations = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        llm_response = self.call_llm(conversations, add_generation_prompt=True)
        conversations.append({"role": "assistant", "content": llm_response})

        # Check for tool calls
        tool_call = parse_tool_call_from_text(llm_response)

        # FIXED: Added max iterations to prevent infinite loops
        max_iterations = 5
        iteration = 0

        while tool_call is not None and iteration < max_iterations:
            iteration += 1

            if tool_call is not None:
                name = tool_call.get("name")
                args = tool_call.get("arguments", {})

                
                tool_res = self.invoke_tool(name, args)

                conversations.append({"role": "tool", "content": tool_res})
                llm_response = self.call_llm(conversations, add_generation_prompt=True)
                conversations.append({"role": "assistant", "content": llm_response})
            else:
                
                llm_response = self.call_llm(conversations, add_generation_prompt=True)
                conversations.append({"role": "assistant", "content": llm_response})

            tool_call = parse_tool_call_from_text(llm_response)

        return conversations, llm_response

    def train(self, train_dataset, eval_dataset, cfg):
        """Train the model."""
        try:
            self.model.config.use_cache = False
        except Exception:
            pass

        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer, mlm=False
        )

        # Training arguments
        training_args = TrainingArguments(
            output_dir=cfg.OUTPUT_DIR,
            num_train_epochs=cfg.EPOCHS,
            per_device_train_batch_size=cfg.BATCH_SIZE,
            per_device_eval_batch_size=cfg.PER_DEVICE_EVAL_BATCH_SIZE,
            gradient_accumulation_steps=cfg.GRADIENT_ACCUMULATION_STEPS,
            learning_rate=cfg.LEARNING_RATE,
            weight_decay=cfg.WEIGHT_DECAY,
            warmup_ratio=cfg.WARMUP_RATIO,
            lr_scheduler_type=cfg.LR_SCHEDULER_TYPE,
            fp16=cfg.FP16,
            eval_strategy=cfg.EVAL_STRATEGY,
            eval_steps=cfg.EVAL_STEPS,
            save_strategy=cfg.SAVE_STRATEGY,
            save_steps=cfg.SAVE_STEPS,
            save_total_limit=cfg.SAVE_TOTAL_LIMIT,
            logging_steps=cfg.LOGGING_STEPS,
            logging_dir=cfg.LOGGING_DIR,
            load_best_model_at_end=cfg.LOAD_BEST_MODEL_AT_END,
            metric_for_best_model=cfg.METRIC_FOR_BEST_MODEL,
            remove_unused_columns=False,
            gradient_checkpointing=True,
            report_to=cfg.REPORT_TO,
        )

        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            processing_class=self.tokenizer,
            data_collator=data_collator,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
        )

        # CHANGE: debug peak memory trước/sau train
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        # Train
        trainer.train()
        trainer.save_model(training_args.output_dir)


# Tools metadata in the correct format for your agent
TOOLS_METADATA = [
    {
        "type": "function",
        "function": {
            "name": "WikipediaRetriever",
            "description": "Return relevant Wikipedia document text for a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query topic, e.g. 'Việt Nam'",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of sentences to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate",
            "description": "Evaluate a mathematical expression with optional variables and precision control.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Expression to evaluate, e.g. 'sin(pi/4) + 2^3'.",
                    },
                    "variables": {
                        "type": "object",
                        "description": "Optional mapping of variable names to numeric values.",
                    },
                    "precision": {
                        "type": "integer",
                        "description": "Decimal precision for result rounding.",
                        "default": 10,
                    },
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "solve_equation",
            "description": "Solve a mathematical equation for a specified variable (e.g. '2*x + 3 = 7').",
            "parameters": {
                "type": "object",
                "properties": {
                    "equation": {
                        "type": "string",
                        "description": "Equation or expression to solve.",
                    },
                    "variable": {
                        "type": "string",
                        "description": "Variable to solve for (default: 'x').",
                        "default": "x",
                    },
                },
                "required": ["equation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_units",
            "description": "Convert numeric values between supported units (length or weight).",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "Numeric value to convert.",
                    },
                    "from_unit": {
                        "type": "string",
                        "description": "Source unit (e.g. 'km', 'm', 'ft', 'kg').",
                    },
                    "to_unit": {
                        "type": "string",
                        "description": "Target unit (e.g. 'm', 'cm', 'lb', 'g').",
                    },
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    }
]

class MathReasoningApp:
    def __init__(self, model_name_or_path):
        """Initialize the model and tokenizer"""
        print(f" Loading model from {model_name_or_path}...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name_or_path,
            trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name_or_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Initialize ToolUseAgent with your custom class
        self.agent = ToolUseAgent(
            model=self.model,
            tokenizer=self.tokenizer,
            tools_metadata=TOOLS_METADATA,
            generation_cfg={
                "max_new_tokens": 1200,
                "do_sample": False,
                "temperature": 0.0,
                "top_p": 0.95,
            }
        )
        
        print(" Model loaded successfully!")
    
    def format_conversation_history(self, conversations):
        """Format conversation history for display"""
        formatted_parts = []
        tool_count = 0
        
        for i, turn in enumerate(conversations):
            role = turn.get("role", "")
            content = turn.get("content", "")
            
            if role == "system":
                continue  # Skip system messages in display
            elif role == "user":
                formatted_parts.append(f"### Người dùng\n{content}")
            elif role == "assistant":
                # Check if this message contains tool calls
                if "```python" in content or "WikipediaRetriever" in content or "evaluate" in content:
                    formatted_parts.append(f"### Trợ lý (Bước {i//2 + 1}) - Gọi công cụ\n```\n{content}\n```")
                else:
                    formatted_parts.append(f"### Trợ lý (Bước {i//2 + 1})\n{content}")
            elif role == "tool":
                tool_count += 1
                formatted_parts.append(f"### Kết quả công cụ #{tool_count}\n```\n{content}\n```")
        
        return "\n\n---\n\n".join(formatted_parts), tool_count
    
    def solve_math_problem(self, question, show_reasoning=True, temperature=0.0, max_tokens=1200):
        """
        Solve a math problem with the AI model
        
        Args:
            question: The math question to solve
            show_reasoning: Whether to show step-by-step reasoning
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            answer, reasoning_steps, execution_time, tool_calls_used
        """
        if not question.strip():
            return " Vui lòng nhập câu hỏi!", "", "0.00s", "Chưa có dữ liệu"
        
        # Update generation config
        self.agent.generation_cfg.update({
            "temperature": temperature,
            "max_new_tokens": int(max_tokens),
            "do_sample": temperature > 0,
            "top_p": 0.95 if temperature > 0 else None,
        })
        
        start_time = time.time()
        
        try:
            # Run inference with your ToolUseAgent
            conversations, final_answer = self.agent.inference(question)
            
            execution_time = time.time() - start_time
            
            # Format conversation history
            if show_reasoning:
                reasoning_text, tool_count = self.format_conversation_history(conversations)
            else:
                reasoning_text = "_Quá trình suy luận đã bị ẩn. Bật 'Hiển thị quá trình suy luận' để xem chi tiết._"
                # Still count tools for metrics
                tool_count = sum(1 for turn in conversations if turn.get("role") == "tool")
            
            # Tool usage info
            if tool_count > 0:
                tool_info = f" Đã sử dụng {tool_count} công cụ"
            else:
                tool_info = " Không sử dụng công cụ"
            
            return final_answer, reasoning_text, f" {execution_time:.2f}s", tool_info
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return (
                f" Lỗi xảy ra: {str(e)}", 
                f"**Chi tiết lỗi:**\n```\n{error_detail}\n```",
                "0.00s",
                "Lỗi"
            )

# Global app instance
app = None

def initialize_app(model_path):
    """Initialize the model - called once at startup"""
    global app
    if app is None:
        app = MathReasoningApp(model_path)
    return app

def solve_wrapper(question, show_reasoning, temperature, max_tokens):
    """Wrapper function for Gradio interface"""
    global app
    if app is None:
        return (
            " Model chưa được tải. Vui lòng khởi động lại ứng dụng.", 
            "", 
            "0.00s", 
            "N/A"
        )
    
    return app.solve_math_problem(question, show_reasoning, temperature, max_tokens)

# Example problems in Vietnamese
examples = [
    ["Tính giá trị của biểu thức: 3x + 5 khi x = 7"],
    ["Giải phương trình: 2x + 10 = 30"],
    ["Một hình chữ nhật có chiều dài 12cm và chiều rộng 8cm. Tính diện tích và chu vi."],
    ["Nếu 5 quyển sách có giá 125,000 đồng, thì 8 quyển sách giá bao nhiêu?"],
    ["Chuyển đổi 100 km sang dặm (miles)"],
    ["Tìm nghiệm của phương trình bậc hai: x² - 5x + 6 = 0"],
    ["Tìm thông tin về Hồ Chí Minh trên Wikipedia"],
    ["Tính sin(π/4) + 2³"],
]

# Custom CSS
custom_css = """
#header {
    text-align: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 25px;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
#answer-box {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-left: 5px solid #3b82f6;
    padding: 20px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 500;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}
#reasoning-box {
    background-color: #57C785;
    border: 1px solid #e5e7eb;
    padding: 20px;
    border-radius: 8px;
    font-size: 14px;
    max-height: 500px;
    overflow-y: auto;
    line-height: 1.6;
}
.metric-box {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    padding: 12px;
    border-radius: 8px;
    text-align: center;
    font-weight: 600;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}
.gr-button-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
}
"""

def create_interface(model_path="your-username/your-model-name"):
    """Create and launch the Gradio interface"""
    
    # Initialize model
    print(" Initializing AI Math Reasoning App...")
    initialize_app(model_path)
    
    with gr.Blocks(css=custom_css, title="AI Math Reasoning", theme=gr.themes.Soft()) as demo:
        
        # Header
        gr.HTML("""
            <div id="header">
                <h1> AI Math Reasoning Assistant</h1>
                <p style="font-size: 18px; margin-top: 10px;">
                    Trợ lý toán học thông minh với khả năng suy luận và sử dụng công cụ
                </p>
                <p style="font-size: 14px; opacity: 0.9; margin-top: 5px;">
                    Powered by ToolUseAgent | Support: Calculator, Equation Solver, Unit Converter, Wikipedia
                </p>
            </div>
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                # Input section
                gr.Markdown("### Nhập câu hỏi của bạn")
                question_input = gr.Textbox(
                    label="Câu hỏi toán học hoặc tra cứu thông tin",
                    placeholder="Ví dụ: Giải phương trình 2x + 5 = 15\nHoặc: Tìm thông tin về Việt Nam",
                    lines=4,
                    max_lines=10
                )
                
                with gr.Row():
                    solve_btn = gr.Button(" Giải quyết", variant="primary", size="lg", scale=2)
                    clear_btn = gr.Button(" Xóa", size="lg", scale=1)
                
                # Advanced settings
                with gr.Accordion(" Cài đặt nâng cao", open=False):
                    show_reasoning = gr.Checkbox(
                        label="Hiển thị quá trình suy luận chi tiết",
                        value=True,
                        info="Xem từng bước suy luận và gọi công cụ"
                    )
                    temperature = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        value=0.0,
                        step=0.1,
                        label="Temperature",
                        info="0 = deterministic (khuyến nghị cho toán), >0 = creative"
                    )
                    max_tokens = gr.Slider(
                        minimum=256,
                        maximum=2048,
                        value=1200,
                        step=128,
                        label="Số token tối đa",
                        info="Độ dài tối đa của câu trả lời"
                    )
                
                # Examples
                gr.Markdown("### Câu hỏi mẫu")
                gr.Examples(
                    examples=examples,
                    inputs=question_input,
                    label="Nhấp để thử các ví dụ"
                )
            
            with gr.Column(scale=3):
                # Output section
                gr.Markdown("### Kết quả")
                
                answer_output = gr.Textbox(
                    label=" Đáp án cuối cùng",
                    lines=5,
                    max_lines=15,
                    elem_id="answer-box",
                    show_copy_button=True
                )
                
                with gr.Row():
                    time_output = gr.Textbox(
                        label=" Thời gian thực thi",
                        interactive=False,
                        elem_classes="metric-box",
                        scale=1
                    )
                    tools_output = gr.Textbox(
                        label=" Công cụ sử dụng",
                        interactive=False,
                        elem_classes="metric-box",
                        scale=1
                    )
                
                gr.Markdown("### Quá trình suy luận")
                reasoning_output = gr.Markdown(
                    value="_Kết quả sẽ hiển thị ở đây..._",
                    elem_id="reasoning-box"
                )
        
        # Information section
        with gr.Accordion(" Hướng dẫn sử dụng & Thông tin", open=False):
            gr.Markdown("""
            ### Cách sử dụng:
            1. **Nhập câu hỏi** toán học hoặc tra cứu thông tin vào ô bên trái
            2. **Nhấn nút "Giải quyết"** để nhận câu trả lời từ AI
            3. **Xem kết quả** ở bên phải với đáp án chi tiết và quá trình suy luận
            4. **Điều chỉnh cài đặt** nếu muốn thay đổi độ sáng tạo hoặc độ dài câu trả lời
            
            ### Tính năng:
            - **Toán học cơ bản**: Cộng, trừ, nhân, chia, lũy thừa, căn bậc
            - **Đại số**: Giải phương trình tuyến tính, bậc hai, hệ phương trình
            - **Hình học**: Tính diện tích, chu vi, thể tích các hình cơ bản
            - **Lượng giác**: Sin, cos, tan và các hàm ngược
            - **Chuyển đổi đơn vị**: Độ dài, khối lượng, nhiệt độ
            - **Tra cứu Wikipedia**: Tìm kiếm thông tin, định nghĩa
            - **Bài toán ứng dụng**: Bài toán thực tế, tỷ lệ, phần trăm
            
            ### Công cụ hỗ trợ:
            
            | Công cụ | Chức năng | Ví dụ |
            |---------|-----------|-------|
            | **evaluate** | Tính toán biểu thức toán học | `sin(π/4) + 2³` |
            | **solve_equation** | Giải phương trình | `2*x + 3 = 7` |
            | **convert_units** | Chuyển đổi đơn vị | `100 km → miles` |
            | **WikipediaRetriever** | Tra cứu thông tin | `Tìm về Việt Nam` |
            
            ### Tips:
            - Đặt câu hỏi rõ ràng, cụ thể
            - Sử dụng temperature = 0 cho bài toán toán học chính xác
            - Bật "Hiển thị quá trình suy luận" để hiểu cách AI giải quyết vấn đề
            - Model có thể tự động gọi công cụ phù hợp khi cần thiết
            """)
        
        # Event handlers
        solve_btn.click(
            fn=solve_wrapper,
            inputs=[question_input, show_reasoning, temperature, max_tokens],
            outputs=[answer_output, reasoning_output, time_output, tools_output]
        )
        
        clear_btn.click(
            fn=lambda: ("", "", "_Kết quả sẽ hiển thị ở đây..._", "0.00s", "N/A"),
            outputs=[question_input, answer_output, reasoning_output, time_output, tools_output]
        )
        
        # Auto-submit on Enter key (optional)
        question_input.submit(
            fn=solve_wrapper,
            inputs=[question_input, show_reasoning, temperature, max_tokens],
            outputs=[answer_output, reasoning_output, time_output, tools_output]
        )
    
    return demo

# Main execution
if __name__ == "__main__":
    # Replace with your actual model path from Hugging Face
    MODEL_PATH = "model_weights(qwen_agent)/agent_model_weights/checkpoint-100"
    
    # For local model path, use:
    # MODEL_PATH = "/path/to/your/local/model"
    
    # Create and launch the interface
    demo = create_interface(MODEL_PATH)
    demo.launch(
        server_name="0.0.0.0",  # Allow external connections
        server_port=7860,
        share=True,  # Create a public shareable link
        show_error=True,
        show_api=False  # Set to True if you want API documentation
    )