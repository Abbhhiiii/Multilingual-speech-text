"""Summarize completed sequential benchmark trials without hiding failures."""
import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

from jiwer import cer, wer

from benchmark import normalize


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def describe(rows, key):
    values = [float(row[key]) for row in rows if row.get(key) not in (None, '')]
    return {'count': len(values), 'median': quantile(values, .5),
            'p90': quantile(values, .9), 'min': min(values) if values else None,
            'max': max(values) if values else None}


def summarize(rows):
    output = {}
    for language in ('en', 'zh', 'id'):
        selected = [row for row in rows if row['language'] == language]
        passed = [row for row in selected if row['status'] == 'done']
        references = [normalize(row['reference']) for row in passed]
        predictions = [normalize(row['prediction']) for row in passed]
        metric = None
        if passed:
            if language == 'zh':
                metric = cer([s.replace(' ', '') for s in references],
                             [s.replace(' ', '') for s in predictions])
            else:
                metric = wer(references, predictions)
        output[language] = {
            'clips': len(selected), 'completed': len(passed),
            'status_counts': dict(Counter(row['status'] for row in selected)),
            'error_counts': dict(Counter(row['error_code'] for row in selected if row['error_code'])),
            'total_audio_seconds': sum(float(row['audio_seconds']) for row in selected),
            'metric': 'CER' if language == 'zh' else 'WER',
            'corpus_error_rate': metric,
            'per_clip_error_rate': describe(passed, 'cer' if language == 'zh' else 'wer'),
            'first_text_ms': describe(passed, 'first_text_ms'),
            'first_visible_client_ms': describe(passed, 'first_visible_client_ms'),
            'final_latency_ms': describe(passed, 'final_latency_ms'),
            'session_elapsed_ms': describe(passed, 'session_elapsed_ms'),
            'worker_mean_cpu_percent': describe(passed, 'worker_mean_cpu_percent'),
            'worker_peak_cpu_percent': describe(passed, 'worker_peak_cpu_percent'),
            'worker_peak_rss_bytes': describe(passed, 'worker_peak_rss_bytes'),
            'worker_peak_uss_bytes': describe(passed, 'worker_peak_uss_bytes'),
            'system_mean_cpu_percent': describe(passed, 'system_mean_cpu_percent'),
            'system_min_available_bytes': describe(passed, 'system_min_available_bytes'),
            'incremental_count': sum(row['incremental'] == 'True' for row in passed),
            'revisions_total': sum(int(row['revisions']) for row in passed),
            'revisions_per_clip': describe(passed, 'revisions'),
            'final_delay_over_5s_count': sum(float(row['final_latency_ms']) > 5000 for row in passed),
            'final_delay_over_10s_count': sum(float(row['final_latency_ms']) > 10000 for row in passed),
        }
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('summary_csv')
    parser.add_argument('--output')
    arguments = parser.parse_args()
    with Path(arguments.summary_csv).open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    result = summarize(rows)
    data = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if arguments.output:
        Path(arguments.output).write_text(data)
    else:
        print(data, end='')
