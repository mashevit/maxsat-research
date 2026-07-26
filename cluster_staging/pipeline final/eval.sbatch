#!/bin/bash

#SBATCH --partition main
#SBATCH --time 0-00:30:00                       ### --quick greedy on 8B; bump to 2-4h for full / self-consistency
#SBATCH --job-name qwen3-lora-eval
#SBATCH --output eval-job-%J.out
#SBATCH --gpus=rtx_6000:1                        ### <- see "SMALLER GPU" note below
#SBATCH --mem=16G
#SBATCH --cpus-per-task=2

echo `date`
echo -e "\nSLURM_JOBID:\t\t" $SLURM_JOBID
echo -e "SLURM_JOB_NODELIST:\t" $SLURM_JOB_NODELIST "\n"

module load anaconda
source activate gsm8k_lora

echo "=== sanity ==="
which python
python -c "import torch; print('torch', torch.__version__, 'cuda?', torch.cuda.is_available())"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
echo "=============="

export HF_HOME=~/.cache/huggingface

### base-vs-LoRA accuracy on the 4-bit path (TEST split only).
### --quick = 30 examples, greedy. evaluate.py loads the base, frees it, then
### loads the adapter, so only ONE 8B 4-bit model is resident at a time (~8-10GB).
python evaluate.py --quick \
    --model_name unsloth/Qwen3-8B-bnb-4bit \
    --adapter_path ./qwen3_8b_lora_model

### GREEDY full eval (200 examples, 1 sample) after --quick passes:
#python evaluate.py \
#    --model_name unsloth/Qwen3-8B-bnb-4bit \
#    --adapter_path ./qwen3_8b_lora_model \
#    --num_test 200 \
#    --num_samples 1 \
#    --show_examples 8 \
#    --seed 42 \
#    --output_file eval_results_greedy.json

### SELF-CONSISTENCY eval (8 samples + majority vote; ~8x slower, +5-15pp typical):
#python evaluate.py \
#    --model_name unsloth/Qwen3-8B-bnb-4bit \
#    --adapter_path ./qwen3_8b_lora_model \
#    --num_test 100 \
#    --num_samples 8 \
#    --temperature 0.7 \
#    --show_examples 8 \
#    --seed 42 \
#    --output_file eval_results_sc8.json

### --- SMALLER GPU ----------------------------------------------------
### Inference is lighter than training - a single 8B 4-bit model + KV cache.
### 24GB is ample; ~16GB works for greedy. Swap the --gpus line for a smaller
### card your partition offers (list them: sinfo -o "%P %G" | sort -u), e.g.
###   #SBATCH --gpus=rtx_3090:1   or   --gpus=a5000:1
### --------------------------------------------------------------------

### NOTE: this is the 4-bit accuracy, not the deploy-lineage number. The model
### you actually serve is the merged fp16 -> Q8_0 GGUF; its accuracy comes from
### the Q8_0 side of compare_base_vs_lora.py in serve.sbatch, not from here.

echo -e "\nEvaluation finished at:" `date`
