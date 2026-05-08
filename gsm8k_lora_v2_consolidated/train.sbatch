#!/bin/bash

#SBATCH --partition main
#SBATCH --time 0-00:30:00                       ### 30 min for --quick; bump to 3h for full run
#SBATCH --job-name gsm8k-lora-train
#SBATCH --output train-job-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=20G

##SBATCH --mail-user=user@bgu.ac.il
##SBATCH --mail-type=ALL

echo `date`
echo -e "\nSLURM_JOBID:\t\t" $SLURM_JOBID
echo -e "SLURM_JOB_NODELIST:\t" $SLURM_JOB_NODELIST "\n"

### Activate environment ###
### First-time setup (on login node — no GPU compile required):
###   conda create -n gsm8k_lora python=3.11 -y
###   conda activate gsm8k_lora
###   pip install "numpy<2"
###   pip install unsloth                       # pulls compatible torch + deps
###   pip install datasets trl scipy tqdm
module load anaconda
source activate gsm8k_lora




echo "=== sanity ==="
which python
python -c "import torch; print('torch', torch.__version__, 'cuda?', torch.cuda.is_available())"
echo "=============="


export HF_HOME=~/.cache/huggingface
# export HF_TOKEN="hf_your_token_here"    # only needed for gated repos

#cd ~/gsm8k_lora

### Quick sanity check first (~5 min) — uncomment to test the pipeline:
python train.py --quick

### Full training run:
#python train.py \
#    --model_name unsloth/llama-3.2-3b-bnb-4bit \
#    --num_train 0 \
#    --val_size 300 \
#    --epochs 3 \
#    --batch_size 4 \
#    --grad_accum 4 \
#    --lora_r 16 \
#    --lora_alpha 32 \
#    --max_seq_len 512 \
#    --seed 42 \
#    --output_dir ./gsm8k_lora_model

### ─── NOTES ──────────────────────────────────────────────────────────
### Model options (all supported):
###   unsloth/llama-3.2-3b-bnb-4bit        ← default, small and fast
###   unsloth/llama-3.2-1b-bnb-4bit        ← smaller, faster tests
###   unsloth/llama-3-8b-bnb-4bit          ← stronger, slower
###   unsloth/mistral-7b-v0.3              ← Mistral alternative
###   unsloth/Qwen2.5-7B-bnb-4bit          ← Qwen (relevant for MaxSAT)
###
### num_train=0 uses all (7473 - val_size) training examples
### val_size=300 is CARVED FROM TRAIN — no test-set leakage
###
### Estimated times (RTX 6000 Ada, 48GB, full dataset, 3 epochs):
###   Llama 3.2 3B   → ~45-90 min
###   Mistral 7B     → ~90 min - 2h
###   Llama 3 8B     → ~2-3h
### ────────────────────────────────────────────────────────────────────

echo -e "\nTraining finished at:" `date`
