########################################################################################################
# The RWKV v2-RNN Language Model - https://github.com/BlinkDL/RWKV-LM
########################################################################################################

from torch.utils.data.dataloader import DataLoader
from torch.optim.lr_scheduler import LambdaLR
from torch.nn import functional as F
import torch.nn as nn
import torch.optim as optim
import torch
from tqdm.auto import tqdm
import numpy as np
import logging
from src.spikingjelly.clock_driven import functional
import os
import datetime
import sys
import math
import pdb
from accelerate import Accelerator
from src.model import L2Wrap

accelerator = Accelerator()

logger = logging.getLogger(__name__)
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cuda.matmul.allow_tf32 = True

log_file = open("wik8-0.01.txt", "a")


class TrainerConfig:
    max_epochs = 10
    batch_size = 64
    learning_rate = 4e-4
    betas = (0.9, 0.99)
    eps = 1e-8
    grad_norm_clip = 1.0
    lr_decay = True 
    warmup_tokens = 0
    final_tokens = 0
    epoch_save_frequency = 0
    epoch_save_path = 'trained-'
    num_workers = 0  # for DataLoader

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class Trainer:

    def __init__(self, model, train_dataset, valid_dataset, test_dataset, config):
        self.model = model
        self.train_dataset = train_dataset
        self.test_dataset = test_dataset
        self.valid_dataset = valid_dataset
        self.config = config
        self.avg_loss = -1
        self.steps = 0
        self.lr = config.learning_rate

        # Validation tracking
        self.train_loss_history = []
        self.val_loss_history = []
        self.min_val_loss = float('inf')

        self.device = 'cpu'
        if torch.cuda.is_available():
            self.device = torch.cuda.current_device()

    def get_run_name(self):
        raw_model = self.model.module if hasattr(self.model, "module") else self.model
        cfg = raw_model.config
        run_name = (
            str(cfg.vocab_size) + '-' + str(cfg.ctx_len) + '-' +
            cfg.model_type + '-' + str(cfg.n_layer) + '-' + str(cfg.n_embd)
        )
        return run_name

    def train(self):
        model, config = self.model, self.config
        raw_model = model.module if hasattr(self.model, "module") else model
        optimizer = raw_model.configure_optimizers(config)
        optimizer = accelerator.prepare(optimizer)
        model = accelerator.prepare(model)

        def run_epoch(split):
            is_train = split == 'train'

            # FIX 1: Correctly select dataset for each split
            if split == 'train':
                data = self.train_dataset
            elif split == 'valid':
                data = self.valid_dataset
            else:  # 'test'
                data = self.test_dataset

            model.train(is_train)

            loader = DataLoader(
                data,
                shuffle=is_train,           # FIX 2: Shuffle only during training
                pin_memory=(config.num_workers > 0),
                batch_size=config.batch_size,
                num_workers=config.num_workers,
            )
            loader = accelerator.prepare(loader)

            pbar = (
                tqdm(
                    enumerate(loader),
                    total=len(loader),
                    bar_format='{l_bar}{bar:10}{r_bar}{bar:-10b}',
                    disable=not accelerator.is_local_main_process,
                )
                if is_train else enumerate(loader)
            )

            loss_sum = 0.0
            loss_count = 0

            for it, (x, y) in pbar:
                with torch.set_grad_enabled(is_train):
                    loss = model(x, y)
                    functional.reset_net(model)

                if is_train:
                    model.zero_grad()
                    accelerator.backward(loss)

                    if config.grad_norm_clip > 0:
                        torch.nn.utils.clip_grad_norm_(
                            model.parameters(), config.grad_norm_clip
                        )

                    optimizer.step()

                    # Learning rate schedule
                    if config.lr_decay:
                        self.tokens += (y >= 0).sum()
                        lr_final_factor = config.lr_final / config.learning_rate
                        if self.tokens < config.warmup_tokens:
                            lr_mult = lr_final_factor + (1 - lr_final_factor) * float(
                                self.tokens
                            ) / float(config.warmup_tokens)
                            progress = 0
                        else:
                            progress = float(
                                self.tokens - config.warmup_tokens
                            ) / float(max(1, config.final_tokens - config.warmup_tokens))
                            lr_mult = (0.5 + lr_final_factor / 2) + (
                                0.5 - lr_final_factor / 2
                            ) * math.cos(math.pi * progress)
                        self.lr = config.learning_rate * lr_mult
                        for param_group in optimizer.param_groups:
                            param_group['lr'] = self.lr
                    else:
                        progress = 0

                    now_loss = loss.item()
                    self.steps += 1

                    if self.avg_loss < 0:
                        self.avg_loss = now_loss
                    else:
                        factor = 1 / (it + 1)
                        self.avg_loss = self.avg_loss * (1.0 - factor) + now_loss * factor

                    pbar.set_description(
                        f"epoch {epoch + 1} prog {progress * 100.0:.2f}% "
                        f"iter {it}: ppl {math.exp(self.avg_loss):.2f} "
                        f"loss {self.avg_loss:.4f} lr {self.lr:e}"
                    )

                else:
                    # FIX 3: Accumulate validation loss properly across all batches
                    loss_sum += loss.item()
                    loss_count += 1

            # FIX 4: Return average loss for non-training splits
            if not is_train:
                avg_eval_loss = loss_sum / max(loss_count, 1)
                return avg_eval_loss
            return None

        self.tokens = 0
        for epoch in range(config.max_epochs):

            # --- Training ---
            self.avg_loss = -1  # FIX 5: Reset per-epoch smoothed loss each epoch
            run_epoch('train')
            self.train_loss_history.append(self.avg_loss)

            log_file.write(
                f'train epoch={epoch + 1} loss={self.avg_loss:.6f} '
                f'ppl={math.exp(self.avg_loss):.4f} lr={self.lr:.8f} '
                f'time={datetime.datetime.now()}\n'
            )
            log_file.flush()

            # --- Validation ---
            # FIX 6: Run validation every epoch (was commented out) and log it
            if self.valid_dataset is not None:
                val_loss = run_epoch('valid')
                self.val_loss_history.append(val_loss)

                if accelerator.is_local_main_process:
                    print(
                        f"[epoch {epoch + 1}] val_loss={val_loss:.6f} "
                        f"val_ppl={math.exp(val_loss):.4f}"
                    )

                log_file.write(
                    f'valid epoch={epoch + 1} loss={val_loss:.6f} '
                    f'ppl={math.exp(val_loss):.4f} '
                    f'time={datetime.datetime.now()}\n'
                )
                log_file.flush()

                if val_loss < self.min_val_loss:
                    self.min_val_loss = val_loss
                    accelerator.wait_for_everyone()
                    unwrapped_model = accelerator.unwrap_model(model)
                    raw_model = (
                        unwrapped_model.module
                        if hasattr(unwrapped_model, "module")
                        else unwrapped_model
                    )
                    best_path = self.config.epoch_save_path + f'(best).pth'
                    torch.save(raw_model.state_dict(), best_path)
                    if accelerator.is_local_main_process:
                        print(f"  --> New best val_loss={val_loss:.6f}, saved to {best_path}")

            # --- Periodic / final checkpoint ---
            if (
                self.config.epoch_save_frequency > 0
                and epoch % self.config.epoch_save_frequency == 0
            ) or (epoch == config.max_epochs - 1):
                accelerator.wait_for_everyone()
                unwrapped_model = accelerator.unwrap_model(model)
                raw_model = (
                    unwrapped_model.module
                    if hasattr(unwrapped_model, "module")
                    else unwrapped_model
                )
                ckpt_path = self.config.epoch_save_path + f'{epoch + 1}.pth'
                torch.save(raw_model.state_dict(), ckpt_path)