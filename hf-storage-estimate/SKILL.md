---
name: hf-storage-estimate
description: This skill should be used when the user asks to "estimate storage", "how much disk space", "HuggingFace storage", "model storage requirements", "analyze models in log", "storage for test collection", or discusses calculating storage needed for machine learning models from test logs.
version: 1.0.0
---

# HuggingFace Storage Estimator

Estimates HuggingFace model storage requirements from test collection log files.

## When to Use This Skill

Use this skill when the user wants to:
- Estimate storage needed for HuggingFace models
- Analyze test collection logs for model storage requirements
- Plan disk space for model testing
- Generate reports on model sizes and categories
- Get CSV exports of model storage data

## Usage

Analyze a log file containing model test collection output:

```bash
~/.claude/skills/hf-storage-estimate/estimate_storage.py /path/to/logfile.log
```

## Input Format

The tool expects log files containing pytest test paths with model identifiers, such as:

```
tests/runner/test_models.py::test_all_models_torch[llama/causal_lm/pytorch-llama_3_8b-single_device-inference]
tests/runner/test_models.py::test_all_models_torch[qwen_2_5/causal_lm/pytorch-7b-single_device-inference]
tests/runner/test_models.py::test_all_models_torch[resnet/pytorch-resnet50-single_device-inference]
```

The tool automatically extracts model identifiers from these test paths.

## Output Reports

Generates four comprehensive reports in the same directory as the input log file:

### 1. `<logname>_STORAGE_SUMMARY.md`
- Executive summary with total storage requirements
- Storage breakdown by category (LLM, Vision, CNN, etc.)
- Distribution by size range
- Top 20 largest models
- Markdown format for easy viewing

### 2. `<logname>_storage_estimate.txt`
- Detailed text report
- Complete list of all models sorted by size
- Category breakdowns with percentages
- Human-readable format

### 3. `<logname>_storage_estimate.csv`
- Spreadsheet-friendly CSV format
- Columns: Rank, Model Path, Size (GB), Category
- Easy to import into Excel/Google Sheets for further analysis

### 4. `<logname>_storage_breakdown.txt`
- Visual ASCII bar charts showing storage by category
- Quick overview of distribution
- Terminal-friendly format

## Model Coverage

The estimator includes size data for 100+ model families:

- **LLMs**: Llama, Qwen, Mistral, Phi, OPT, GPT-Neo, Gemma, Falcon, Mamba, etc.
- **Vision-Language**: OpenVLA, Fuyu, Flux, CLIP, SigLIP
- **BERT-like**: BERT, ALBERT, RoBERTa, DistilBERT
- **Vision Transformers**: ViT, DINOv2, DeiT, BEiT, Swin
- **CNNs**: ResNet, EfficientNet, MobileNet, RegNet, VGG, DenseNet, etc.
- **Object Detection**: YOLO variants, RetinaNet, SSD, DETR, etc.
- **Segmentation**: UNet, SegFormer, MaskFormer
- **Specialized**: 100+ other model families

## Model Size Estimation

Sizes are estimated based on:
- **Parameter counts**: Models categorized by parameter counts (e.g., 7B, 14B, 125M)
- **Model family patterns**: Different families have known typical sizes
- **Historical data**: Based on actual HuggingFace model sizes

## Example Output

```
Total Models: 414
Total Storage: 836.76 GB (0.82 TB)
Recommended (30% buffer): 1,087.79 GB (1.06 TB)

Storage by Category:
- LLM: 625.10 GB (74.7%) - 109 models
- Vision-Language: 133.50 GB (16.0%) - 17 models
- CNN: 17.01 GB (2.0%) - 102 models
```

## Common Use Cases

### Analyze Current Test Collection
```bash
~/.claude/skills/hf-storage-estimate/estimate_storage.py entry_1_collect.log
```

### Estimate Storage Before Running Tests
```bash
# First collect without running
pytest --collect-only > test_collection.log
# Then estimate
~/.claude/skills/hf-storage-estimate/estimate_storage.py test_collection.log
```

### Compare Different Test Configurations
```bash
~/.claude/skills/hf-storage-estimate/estimate_storage.py nightly_tests.log
~/.claude/skills/hf-storage-estimate/estimate_storage.py weekly_tests.log
# Compare the generated CSV files
```

## Customization

To add or modify model size estimates, edit the `MODEL_SIZES` dictionary in `estimate_storage.py`:

```python
MODEL_SIZES = {
    'new_model_pattern': 10.5,  # Size in GB
    'another_model.*7b': 14.0,   # Regex patterns supported
}
```

## Understanding Results

### Total Storage
- **Total Storage**: Sum of all estimated model sizes
- **Recommended**: Includes 30% safety buffer for caching, temporary files, etc.

### Categories
Models are automatically categorized:
- **LLM**: Large Language Models (typically largest)
- **VISION_LANGUAGE**: Multi-modal models
- **BERT_LIKE**: BERT and variants
- **VISION_TRANSFORMER**: Vision Transformers
- **CNN**: Convolutional Neural Networks
- **OBJECT_DETECTION**: Detection models
- **SEGMENTATION**: Segmentation models
- **SPECIALIZED**: Other specialized models
- **OTHER**: Uncategorized models

### Size Ranges
- `<100MB`: Small models
- `100MB-1GB`: Medium models
- `1-5GB`: Large transformers, some LLMs
- `5-10GB`: Large LLMs (3B-7B range)
- `10-20GB`: Very large LLMs (7B-14B range)
- `>20GB`: Huge models (14B+, multimodal)

## Tips

1. **Buffer space**: Always allocate the "Recommended" amount
2. **Cache management**: HuggingFace caches models in `~/.cache/huggingface/`
3. **Storage monitoring**: Monitor disk usage with `df -h`
4. **Cleanup**: Use `huggingface-cli delete-cache` to remove unused models

## Implementation Notes

When the user asks to estimate storage, invoke the Python script with the Bash tool, passing the log file path as an argument.

Example:
- User: "Estimate storage for entry_1_collect.log"
- Action: Execute `~/.claude/skills/hf-storage-estimate/estimate_storage.py entry_1_collect.log`
- Then read and present the generated STORAGE_SUMMARY.md file to the user
