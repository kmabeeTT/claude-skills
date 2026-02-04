# HuggingFace Storage Estimator Skill

Estimates HuggingFace model storage requirements from test collection log files.

## Description

This skill analyzes pytest collection logs (or similar log files) that contain model test paths and estimates the total HuggingFace storage required for all models listed. It's particularly useful for planning disk space requirements before running large test suites with many ML models.

## Usage

### As a Skill (Recommended)

```bash
/hf-storage-estimate log_file=/path/to/logfile.log
```

### Direct Script Execution

```bash
python ~/.claude/skills/hf-storage-estimate/estimate_storage.py /path/to/logfile.log
```

## Input Format

The skill expects log files containing pytest test paths with model identifiers, such as:

```
tests/runner/test_models.py::test_all_models_torch[llama/causal_lm/pytorch-llama_3_8b-single_device-inference]
tests/runner/test_models.py::test_all_models_torch[qwen_2_5/causal_lm/pytorch-7b-single_device-inference]
tests/runner/test_models.py::test_all_models_torch[resnet/pytorch-resnet50-single_device-inference]
```

The skill automatically extracts model identifiers from these test paths.

## Output

The skill generates four comprehensive reports in the same directory as the input log file:

### 1. `<logname>_STORAGE_SUMMARY.md`
- Executive summary with total storage requirements
- Storage breakdown by category (LLM, Vision, CNN, etc.)
- Distribution by size range
- Top 20 largest models
- Formatted as Markdown for easy viewing

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

## Model Size Estimation

The skill estimates model sizes based on:

- **Parameter counts**: Models are categorized by their parameter counts (e.g., 7B, 14B, 125M)
- **Model family patterns**: Different model families have known typical sizes
- **Historical data**: Based on actual HuggingFace model sizes

### Coverage

The estimator includes size data for:
- **LLMs**: Llama, Qwen, Mistral, Phi, OPT, GPT-Neo, Gemma, Falcon, Mamba, etc.
- **Vision-Language**: OpenVLA, Fuyu, Flux, CLIP, SigLIP
- **BERT-like**: BERT, ALBERT, RoBERTa, DistilBERT
- **Vision Transformers**: ViT, DINOv2, DeiT, BEiT, Swin
- **CNNs**: ResNet, EfficientNet, MobileNet, RegNet, VGG, DenseNet, etc.
- **Object Detection**: YOLO variants, RetinaNet, SSD, DETR, etc.
- **Segmentation**: UNet, SegFormer, MaskFormer
- **Specialized**: 100+ other model families

## Examples

### Example 1: Analyze a test collection log

```bash
/hf-storage-estimate log_file=test_matrix_analysis_20260203_190204/entry_1_collect.log
```

Output:
```
Total Models: 405
Total Storage: 825.72 GB (0.81 TB)
Recommended: 1073.43 GB (1.05 TB)

Reports generated:
  - markdown    : entry_1_collect_STORAGE_SUMMARY.md
  - text        : entry_1_collect_storage_estimate.txt
  - csv         : entry_1_collect_storage_estimate.csv
  - breakdown   : entry_1_collect_storage_breakdown.txt
```

### Example 2: Analyze weekly test models

```bash
/hf-storage-estimate log_file=weekly_tests_collect.log
```

### Example 3: Direct Python execution

```bash
cd ~/.claude/skills/hf-storage-estimate
python estimate_storage.py ~/tt-xla/nightly_collect.log
```

## Understanding the Results

### Total Storage
- The **Total Storage** is the sum of all estimated model sizes
- **Recommended** includes a 30% safety buffer for caching, temporary files, etc.

### Categories
Models are automatically categorized as:
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
Models are binned by size for easy planning:
- `<100MB`: Small models (CNNs, small transformers)
- `100MB-1GB`: Medium models
- `1-5GB`: Large transformers, some LLMs
- `5-10GB`: Large LLMs (3B-7B parameter range)
- `10-20GB`: Very large LLMs (7B-14B range)
- `>20GB`: Huge models (14B+, multimodal)

## Tips

1. **Buffer space**: Always allocate the "Recommended" amount, not just the "Total Storage"
2. **Cache management**: HuggingFace caches downloaded models in `~/.cache/huggingface/`
3. **Parallel downloads**: If downloading many models, consider using `huggingface-cli download --cache-dir`
4. **Storage monitoring**: Monitor disk usage during test runs with `df -h`
5. **Cleanup**: Use `huggingface-cli delete-cache` to remove unused cached models

## Customization

To add or modify model size estimates, edit the `MODEL_SIZES` dictionary in `estimate_storage.py`:

```python
MODEL_SIZES = {
    'new_model_pattern': 10.5,  # Size in GB
    'another_model.*7b': 14.0,   # Regex patterns supported
}
```

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

## Version

1.0.0

## Author

Created for TT-XLA project model testing infrastructure.
