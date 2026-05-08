#!/bin/bash

#SBATCH --partition main
#SBATCH --time 0-01:00:00                       ### 4h — self-consistency is slower
#SBATCH --job-name gsm8k-lora-eval
#SBATCH --output eval-job-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=20G

echo `date`
echo -e "\nSLURM_JOBID:\t\t" $SLURM_JOBID
echo -e "SLURM_JOB_NODELIST:\t" $SLURM_JOB_NODELIST "\n"


module load anaconda
source activate gsm8k_lora
export HF_HOME=~/.cache/huggingface
#cd ~/gsm8k_lora

python evaluate.py --quick \
    --model_name unsloth/llama-3.2-3b-bnb-4bit \
    --adapter_path ./gsm8k_lora_model

### GREEDY evaluation (fast, 1 sample per question) ~30-60 min for 200 examples:
#python evaluate.py \
#   --model_name mistralai/Mistral-7B-v0.3 \
#    --adapter_path ./gsm8k_lora_model \
#    --num_test 200 \
#    --num_samples 1 \
#    --show_examples 8 \
#    --seed 42 \
#    --output_file eval_results_greedy.json

### SELF-CONSISTENCY evaluation (slower, 8 samples + majority vote)
### Uncomment to run after greedy baseline. Time: 8x slower than greedy.
### Usually yields +5-15pp accuracy improvement on math reasoning.
# python evaluate.py \
#     --model_name mistralai/Mistral-7B-v0.3 \
#     --adapter_path ./gsm8k_lora_model \
#     --num_test 100 \
#     --num_samples 8 \
#     --temperature 0.7 \
#     --show_examples 8 \
#     --seed 42 \
#     --output_file eval_results_sc8.json

echo -e "\nEvaluation finished at:" `date`
