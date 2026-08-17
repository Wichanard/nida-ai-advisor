"""
tests/test_pipeline_runner.py
Unit tests for Automated Data Pipeline & Spam Filtering.
"""
import pytest
from social_listening.pipeline_runner import is_spam_or_noise, NIDADataPipelineRunner


class TestPipelineRunner:

    def test_spam_detection(self):
        assert is_spam_or_noise("สมัครเล่นบาคาร่า รับเครดิตฟรี 100") is True
        assert is_spam_or_noise("กู้เงินด่วน อนุมัติไว ดอกเบี้ยถูก") is True
        assert is_spam_or_noise("") is True
        assert is_spam_or_noise("สนใจเรียนต่อ MBA นิด้า เสาร์อาทิตย์ครับ") is False
        assert is_spam_or_noise("อาจารย์นิด้าสอนดีไหม คณะสถิติประยุกต์") is False

    def test_pipeline_runner_execution(self):
        result = NIDADataPipelineRunner.run_full_pipeline(
            max_results_per_source=2,
            target_platforms=["pantip"],
        )
        assert result["status"] == "success"
        assert "batch_stats" in result
        assert "warehouse_total_mentions" in result
