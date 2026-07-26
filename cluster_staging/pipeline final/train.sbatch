#!/bin/bash

#SBATCH --partition main
#SBATCH --time 0-00:45:00                       ### --quick on 8B incl. first-time ~5.5GB download; bump to 3-4h for full run
#SBATCH --job-name qwen3-lora-train
#SBATCH --output train-job-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=32G                               ### bumped from 20G for the 8B checkpoint save
#SBATCH --cpus-per-task=4

##SBATCH --mail-user=user@bgu.ac.il
##SBATCH --mail-type=ALL

echo `date`
echo -e "\nSLURM_JOBID:\t\t" $SLURM_JOBID
echo -e "SLURM_JOB_NODELIST:\t" $SLURM_JOB_NODELIST "\n"

### Activate environment (same 'gsm8k_lora' unsloth env as before) ###
### Qwen3 needs transformers >= 4.51.0 — your env already has 4.57.x, so fine.
module load anaconda
source activate gsm8k_lora

echo "=== sanity ==="
which python
python -c "import torch; print('torch', torch.__version__, 'cuda?', torch.cuda.is_available())"
python -c "import transformers; print('transformers', transformers.__version__)"
echo "=============="

export HF_HOME=~/.cache/huggingface
# export HF_TOKEN="hf_your_token_here"    # not needed for unsloth/... pre-quantized repos

#cd ~/gsm8k_lora_v2       # or wherever train.py lives

### Quick sanity check (--quick = 200 train / 1 epoch / 50 val, ~10-20 min on 8B):
python train.py --quick \
    --model_name unsloth/Qwen3-8B-bnb-4bit \
    --output_dir ./qwen3_8b_lora_model

### Full training run (uncomment after --quick passes):
#python train.py \
#    --model_name unsloth/Qwen3-8B-bnb-4bit \
#    --num_train 0 \
#    --val_size 300 \
#    --epochs 3 \
#    --batch_size 4 \
#    --grad_accum 4 \
#    --lora_r 16 \
#    --lora_alpha 32 \
#    --max_seq_len 512 \
#    --seed 42 \
#    --output_dir ./qwen3_8b_lora_model

### ─── NOTES ──────────────────────────────────────────────────────────
### Model string options (all Qwen3-8B, all 4-bit):
###   unsloth/Qwen3-8B-bnb-4bit             ← default here; plain bnb, most predictable through merge->GGUF
###   unsloth/Qwen3-8B-unsloth-bnb-4bit     ← Dynamic 2.0 quant (slightly better accuracy)
###   unsloth/Qwen3-8B-Base-bnb-4bit        ← BASE model; cleaner fit for the plain build_prompt format (no chat priors)
###
### Qwen3-8B has tie_word_embeddings = false → structurally immune to the
### Llama-3.2 tied-embedding merge corruption. The merge_export.py fidelity
### gate should PASS cleanly here.
###
### Downstream must point at the NEW adapter dir:
###   merge:   sbatch merge.sbatch ./qwen3_8b_lora_model ./merged_16bit
###   gguf:    sbatch gguf.sbatch  ./merged_16bit Q8_0        # Q8_0 for the agreement baseline
###   serve:   set MODEL_TAG (e.g. qwen3-8b-gsm8k) and Modelfile FROM to the Q8_0 blob,
###            then compare_base_vs_lora.py --merged ./merged_16bit --ollama-model <tag>
### ────────────────────────────────────────────────────────────────────

echo -e "\nTraining finished at:" `date`
