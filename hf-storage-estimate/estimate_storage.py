#!/usr/bin/env python3
"""
HuggingFace Model Storage Estimator
Analyzes log files containing model test collections and estimates storage requirements.
"""

import re
import sys
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import csv


class ModelStorageEstimator:
    """Estimates HuggingFace model storage requirements."""

    # Model size estimates in GB based on parameter counts and typical sizes
    MODEL_SIZES = {
        # LLMs by parameter count
        'qwen_2_5.*14b': 28.0,
        'qwen_2_5.*7b': 14.5,
        'qwen_2_5.*3b': 6.5,
        'qwen_2_5.*1[._]5b': 3.2,
        'qwen_2_5.*0[._]5b': 1.0,
        'qwen_1_5.*0[._]5b': 1.0,
        'qwen_3.*4b': 8.0,
        'qwen_3.*1[._]7b': 3.5,
        'qwen_3.*0[._]6b': 1.2,
        'llama.*8b': 16.0,
        'llama.*7b': 14.0,
        'llama.*3b': 6.5,
        'llama.*1b': 2.5,
        'tinyllama': 0.9,
        'mistral.*8b': 16.0,
        'mistral.*7b': 14.5,
        'mistral.*3b': 6.5,
        'phi-4': 14.0,
        'phi.*3.*5': 7.8,
        'phi.*3': 7.5,
        'phi.*2': 5.5,
        'phi.*1.*5': 2.8,
        'phi.*1': 2.5,
        'opt.*1.3b': 2.7,
        'opt.*350m': 0.7,
        'opt.*125m': 0.5,
        'albert.*xxlarge': 0.9,
        'albert.*xlarge': 0.6,
        'albert.*large': 0.35,
        'albert.*base': 0.2,
        'gemma.*7b': 14.5,
        'gemma.*4b': 8.0,
        'gemma.*2b': 5.0,
        'falcon.*mamba.*7b': 14.5,
        'falcon.*7b': 14.5,
        'falcon.*1b': 2.5,
        'gpt.*neo.*2.7b': 5.5,
        'gpt.*neo.*1.3b': 2.7,
        'gpt.*neo.*125m': 0.5,
        'gpt2': 1.5,
        'bloom': 1.1,
        'xglm.*1.7b': 3.5,
        'xglm.*564m': 1.2,
        'bart.*large': 1.6,
        't5.*large': 3.0,
        't5.*base': 0.9,
        't5.*small': 0.3,
        'flan.*t5.*large': 3.0,
        'flan.*t5.*base': 0.9,
        'flan.*t5.*small': 0.3,
        'codegen.*350m': 0.7,
        'deepseek.*1.3b': 2.7,
        'deepcogito.*3b': 6.5,
        'nanogpt': 0.1,
        'mamba.*2.8b': 5.6,
        'mamba.*1.4b': 2.9,
        'mamba.*790m': 1.6,
        'mamba.*370m': 0.8,

        # Vision-Language Models
        'openvla': 15.0,
        'fuyu.*8b': 16.0,
        'flux.*dev': 23.8,
        'flux.*schnell': 23.8,

        # BERT-like models
        'bert.*large': 1.3,
        'bert.*base': 0.4,
        'roberta.*base': 0.5,
        'distilbert': 0.3,

        # Vision Transformers
        'vit.*huge': 2.5,
        'vit.*giant': 2.0,
        'vit.*large': 1.2,
        'vit.*base': 0.35,
        'dinov2.*giant': 4.4,
        'dinov2.*large': 1.2,
        'dinov2.*base': 0.35,
        'deit.*base': 0.35,
        'deit.*small': 0.2,
        'deit.*tiny': 0.06,
        'beit.*large': 1.2,
        'beit.*base': 0.35,
        'swin.*base': 0.35,
        'swin.*tiny': 0.1,
        'swin.*small': 0.2,

        # CNNs - typically smaller
        'resnet.*152': 0.23,
        'resnet.*101': 0.17,
        'resnet.*50': 0.1,
        'resnet.*34': 0.08,
        'resnet.*18': 0.04,
        'resnext.*101': 0.35,
        'resnext.*50': 0.1,
        'efficientnet.*b7': 0.27,
        'efficientnet.*b6': 0.17,
        'efficientnet.*b5': 0.12,
        'efficientnet.*b4': 0.08,
        'efficientnet.*b3': 0.05,
        'efficientnet.*b2': 0.04,
        'efficientnet.*b1': 0.03,
        'efficientnet.*b0': 0.02,
        'efficientnet.*lite': 0.02,
        'mobilenet.*v3': 0.02,
        'mobilenet.*v2': 0.014,
        'mobilenet.*v1': 0.017,
        'regnet.*128gf': 0.55,
        'regnet.*32gf': 0.14,
        'regnet.*16gf': 0.07,
        'regnet.*8gf': 0.04,
        'regnet.*3.2gf': 0.02,
        'regnet.*1.6gf': 0.012,
        'regnet.*': 0.01,  # fallback for smaller regnets
        'vgg.*19': 0.55,
        'vgg.*16': 0.53,
        'vgg.*13': 0.51,
        'vgg.*11': 0.51,
        'densenet.*201': 0.08,
        'densenet.*169': 0.057,
        'densenet.*161': 0.11,
        'densenet.*121': 0.032,
        'alexnet': 0.23,
        'googlenet': 0.05,
        'inception.*v4': 0.17,
        'xception': 0.09,
        'wide.*resnet.*101': 0.25,
        'wide.*resnet.*50': 0.13,

        # Object Detection / Segmentation
        'yolo.*world.*xlarge': 0.4,
        'yolo.*world.*large': 0.3,
        'yolo.*world.*medium': 0.2,
        'yolo.*world.*small': 0.1,
        'yolox.*x': 0.38,
        'yolox.*l': 0.2,
        'yolox.*m': 0.1,
        'yolox.*s': 0.04,
        'yolox.*tiny': 0.02,
        'yolox.*nano': 0.008,
        'yolov9.*e': 0.23,
        'yolov9.*c': 0.1,
        'yolov9.*s': 0.03,
        'yolov6.*l': 0.23,
        'yolov6.*m': 0.14,
        'yolov6.*s': 0.07,
        'yolov6.*n': 0.02,
        'yolov3': 0.24,
        'yolos': 0.35,
        'retinanet': 0.15,
        'ssd300': 0.1,
        'unet': 0.5,
        'segformer.*b4': 0.25,
        'segformer.*b3': 0.18,
        'segformer.*b2': 0.11,
        'segformer.*b1': 0.055,
        'segformer.*b0': 0.015,
        'detr': 0.17,
        'maskformer': 0.35,

        # Specialized models
        'musicgen': 1.5,
        'clip': 0.6,
        'siglip.*so400m': 1.7,
        'siglip.*large': 1.4,
        'siglip.*base': 0.35,
        'perceiver': 0.2,
        'glpn': 0.12,
        'monodepth2': 0.06,
        'hardnet': 0.015,
        'ghostnet': 0.02,
        'vovnet.*99b': 0.19,
        'vovnet.*39b': 0.08,
        'vovnet.*27s': 0.015,
        'vovnet.*19b': 0.01,
        'dla.*169': 0.054,
        'dla.*102': 0.034,
        'dla.*60': 0.02,
        'dla.*46': 0.015,
        'dla.*34': 0.016,
        'hrnet.*w64': 0.13,
        'hrnet.*w48': 0.095,
        'hrnet.*w44': 0.085,
        'hrnet.*w40': 0.075,
        'hrnet.*w32': 0.055,
        'hrnet.*w30': 0.048,
        'hrnet.*w18': 0.022,
        'fpn': 0.11,
        'centernet': 0.08,
        'bevformer': 0.15,
        'openpose': 0.2,
        'ultra.*fast.*lane': 0.05,
        'autoencoder': 0.01,
        'stereo': 0.05,
        'mgp_str': 0.15,
        'mlp_mixer.*l': 0.8,
        'mlp_mixer.*b': 0.25,
        'mlp_mixer.*s': 0.07,
        'rcnn': 0.23,
        'dpr': 0.5,
        'bge.*large': 1.34,
        'bge.*m3': 2.24,
        'monodle': 0.08,
        'arnold': 0.01,
    }

    # Category mappings
    CATEGORIES = {
        'llm': ['llama', 'mistral', 'qwen', 'phi', 'opt', 'gpt', 'falcon', 'gemma',
                'deepseek', 'deepcogito', 'mamba', 'bloom', 'xglm', 'codegen', 'nanogpt',
                't5', 'flan', 'bart'],
        'vision_language': ['openvla', 'fuyu', 'flux', 'clip', 'siglip'],
        'bert_like': ['bert', 'albert', 'roberta', 'distilbert'],
        'vision_transformer': ['vit', 'dinov2', 'deit', 'beit', 'swin'],
        'cnn': ['resnet', 'resnext', 'efficientnet', 'mobilenet', 'regnet', 'vgg',
                'densenet', 'alexnet', 'googlenet', 'inception', 'xception', 'wide_resnet'],
        'object_detection': ['yolo', 'retinanet', 'ssd', 'detr', 'centernet', 'rcnn'],
        'segmentation': ['unet', 'segformer', 'maskformer', 'glpn'],
        'specialized': ['musicgen', 'perceiver', 'monodepth', 'hardnet', 'ghostnet',
                       'vovnet', 'dla', 'hrnet', 'fpn', 'bevformer', 'openpose',
                       'autoencoder', 'stereo', 'mgp_str', 'mlp_mixer', 'dpr', 'bge',
                       'monodle', 'arnold', 'ultra_fast_lane'],
    }

    def __init__(self):
        self.models = []
        self.model_sizes = {}

    def extract_models_from_log(self, log_path: str) -> List[str]:
        """Extract model identifiers from a log file."""
        models = []

        with open(log_path, 'r') as f:
            content = f.read()

        # Pattern for pytest test names
        pattern = r'test_all_models_(?:torch|jax)\[([^\]]+)\]'
        matches = re.findall(pattern, content)

        for match in matches:
            # Extract model identifier from test path
            # Format: model_family/variant/framework-model_name-parallelism-mode
            models.append(match)

        return sorted(set(models))

    def estimate_model_size(self, model_path: str) -> float:
        """Estimate size for a single model in GB."""
        model_lower = model_path.lower()

        # Try to match against known patterns
        for pattern, size in self.MODEL_SIZES.items():
            if re.search(pattern, model_lower):
                return size

        # Default fallback based on model family
        if any(x in model_lower for x in ['llama', 'mistral', 'falcon']):
            return 14.0  # Assume 7B model
        elif any(x in model_lower for x in ['qwen', 'phi']):
            return 7.0
        elif any(x in model_lower for x in ['bert', 'roberta', 'distilbert', 'albert']):
            return 0.4
        elif any(x in model_lower for x in ['vit', 'deit', 'beit', 'swin', 'dinov2']):
            return 0.35
        elif any(x in model_lower for x in ['resnet', 'efficientnet', 'mobilenet']):
            return 0.1
        elif any(x in model_lower for x in ['yolo', 'retinanet', 'ssd']):
            return 0.15
        else:
            return 0.5  # Conservative default

    def categorize_model(self, model_path: str) -> str:
        """Categorize a model by type."""
        model_lower = model_path.lower()

        for category, keywords in self.CATEGORIES.items():
            if any(keyword in model_lower for keyword in keywords):
                return category

        return 'other'

    def analyze(self, log_path: str) -> Dict:
        """Perform complete analysis on a log file."""
        self.models = self.extract_models_from_log(log_path)

        results = {
            'total_models': len(self.models),
            'models': [],
            'by_category': defaultdict(lambda: {'count': 0, 'size': 0.0}),
            'by_size_range': defaultdict(lambda: {'count': 0, 'size': 0.0}),
            'total_size': 0.0,
        }

        for model in self.models:
            size = self.estimate_model_size(model)
            category = self.categorize_model(model)

            model_info = {
                'path': model,
                'size_gb': size,
                'category': category,
            }
            results['models'].append(model_info)

            results['by_category'][category]['count'] += 1
            results['by_category'][category]['size'] += size
            results['total_size'] += size

            # Size ranges
            if size < 0.1:
                size_range = '<100MB'
            elif size < 1.0:
                size_range = '100MB-1GB'
            elif size < 5.0:
                size_range = '1-5GB'
            elif size < 10.0:
                size_range = '5-10GB'
            elif size < 20.0:
                size_range = '10-20GB'
            else:
                size_range = '>20GB'

            results['by_size_range'][size_range]['count'] += 1
            results['by_size_range'][size_range]['size'] += size

        # Sort models by size
        results['models'].sort(key=lambda x: x['size_gb'], reverse=True)

        return results

    def generate_reports(self, results: Dict, output_dir: str, base_name: str):
        """Generate comprehensive reports."""

        # 1. Summary markdown report
        md_path = os.path.join(output_dir, f'{base_name}_STORAGE_SUMMARY.md')
        self._generate_markdown_report(results, md_path)

        # 2. Detailed text report
        txt_path = os.path.join(output_dir, f'{base_name}_storage_estimate.txt')
        self._generate_text_report(results, txt_path)

        # 3. CSV export
        csv_path = os.path.join(output_dir, f'{base_name}_storage_estimate.csv')
        self._generate_csv_report(results, csv_path)

        # 4. Breakdown text
        breakdown_path = os.path.join(output_dir, f'{base_name}_storage_breakdown.txt')
        self._generate_breakdown_report(results, breakdown_path)

        return {
            'markdown': md_path,
            'text': txt_path,
            'csv': csv_path,
            'breakdown': breakdown_path,
        }

    def _generate_markdown_report(self, results: Dict, path: str):
        """Generate markdown summary report."""
        with open(path, 'w') as f:
            f.write("# HuggingFace Model Storage Analysis\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Models**: {results['total_models']}\n")
            f.write(f"- **Total Storage**: {results['total_size']:.2f} GB ({results['total_size']/1024:.2f} TB)\n")
            f.write(f"- **Recommended (30% buffer)**: {results['total_size']*1.3:.2f} GB ({results['total_size']*1.3/1024:.2f} TB)\n")
            f.write(f"- **Average per Model**: {results['total_size']/max(results['total_models'],1):.2f} GB\n\n")

            # By Category
            f.write("## Storage by Category\n\n")
            f.write("| Category | Models | Storage (GB) | % of Total |\n")
            f.write("|----------|--------|--------------|------------|\n")

            for cat, data in sorted(results['by_category'].items(),
                                   key=lambda x: x[1]['size'], reverse=True):
                pct = (data['size'] / results['total_size'] * 100) if results['total_size'] > 0 else 0
                f.write(f"| {cat.upper()} | {data['count']} | {data['size']:.2f} | {pct:.1f}% |\n")

            # By Size Range
            f.write("\n## Distribution by Size Range\n\n")
            f.write("| Size Range | Models | Storage (GB) |\n")
            f.write("|------------|--------|-------------|\n")

            size_order = ['<100MB', '100MB-1GB', '1-5GB', '5-10GB', '10-20GB', '>20GB']
            for range_name in size_order:
                if range_name in results['by_size_range']:
                    data = results['by_size_range'][range_name]
                    f.write(f"| {range_name} | {data['count']} | {data['size']:.2f} |\n")

            # Top 20 Largest Models
            f.write("\n## Top 20 Largest Models\n\n")
            f.write("| Rank | Model | Size (GB) | Category |\n")
            f.write("|------|-------|-----------|----------|\n")

            for i, model in enumerate(results['models'][:20], 1):
                f.write(f"| {i} | {model['path']} | {model['size_gb']:.2f} | {model['category']} |\n")

            f.write("\n---\n")
            f.write(f"*Analysis of {results['total_models']} models*\n")

    def _generate_text_report(self, results: Dict, path: str):
        """Generate detailed text report."""
        with open(path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("HuggingFace Model Storage Estimation Report\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Total Models Analyzed: {results['total_models']}\n")
            f.write(f"Total Storage Required: {results['total_size']:.2f} GB ({results['total_size']/1024:.2f} TB)\n")
            f.write(f"Recommended with Buffer: {results['total_size']*1.3:.2f} GB ({results['total_size']*1.3/1024:.2f} TB)\n")
            f.write(f"Average Model Size: {results['total_size']/max(results['total_models'],1):.2f} GB\n\n")

            f.write("-" * 80 + "\n")
            f.write("BREAKDOWN BY CATEGORY\n")
            f.write("-" * 80 + "\n\n")

            for cat, data in sorted(results['by_category'].items(),
                                   key=lambda x: x[1]['size'], reverse=True):
                pct = (data['size'] / results['total_size'] * 100) if results['total_size'] > 0 else 0
                f.write(f"{cat.upper():20s}: {data['count']:4d} models, {data['size']:8.2f} GB ({pct:5.1f}%)\n")

            f.write("\n" + "-" * 80 + "\n")
            f.write("ALL MODELS (sorted by size)\n")
            f.write("-" * 80 + "\n\n")

            for i, model in enumerate(results['models'], 1):
                f.write(f"{i:4d}. {model['size_gb']:6.2f} GB - {model['category']:20s} - {model['path']}\n")

    def _generate_csv_report(self, results: Dict, path: str):
        """Generate CSV export."""
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Rank', 'Model Path', 'Size (GB)', 'Category'])

            for i, model in enumerate(results['models'], 1):
                writer.writerow([i, model['path'], f"{model['size_gb']:.2f}", model['category']])

    def _generate_breakdown_report(self, results: Dict, path: str):
        """Generate visual breakdown report."""
        with open(path, 'w') as f:
            f.write("HuggingFace Storage Breakdown\n")
            f.write("=" * 80 + "\n\n")

            # ASCII bar chart for categories
            f.write("Storage by Category (GB):\n\n")
            max_size = max([data['size'] for data in results['by_category'].values()]) if results['by_category'] else 1

            for cat, data in sorted(results['by_category'].items(),
                                   key=lambda x: x[1]['size'], reverse=True):
                bar_length = int((data['size'] / max_size) * 50)
                bar = '█' * bar_length
                f.write(f"{cat:20s} {bar} {data['size']:7.2f} GB ({data['count']} models)\n")

            f.write(f"\nTotal: {results['total_size']:.2f} GB across {results['total_models']} models\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: estimate_storage.py <log_file_path>")
        sys.exit(1)

    log_path = sys.argv[1]

    if not os.path.exists(log_path):
        print(f"Error: Log file not found: {log_path}")
        sys.exit(1)

    # Setup output
    log_dir = os.path.dirname(os.path.abspath(log_path))
    log_name = Path(log_path).stem

    print(f"Analyzing models from: {log_path}")
    print(f"Output directory: {log_dir}")
    print()

    # Run analysis
    estimator = ModelStorageEstimator()
    results = estimator.analyze(log_path)

    # Generate reports
    report_paths = estimator.generate_reports(results, log_dir, log_name)

    # Print summary
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nTotal Models: {results['total_models']}")
    print(f"Total Storage: {results['total_size']:.2f} GB ({results['total_size']/1024:.2f} TB)")
    print(f"Recommended: {results['total_size']*1.3:.2f} GB ({results['total_size']*1.3/1024:.2f} TB)")
    print(f"\nReports generated:")
    for report_type, report_path in report_paths.items():
        print(f"  - {report_type:12s}: {report_path}")
    print()


if __name__ == '__main__':
    main()
