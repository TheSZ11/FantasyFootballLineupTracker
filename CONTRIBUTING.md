# 🤝 Contributing to LineupTracker

Thank you for your interest in contributing to LineupTracker! We welcome contributions from developers of all skill levels.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Areas for Contribution](#areas-for-contribution)

---

## 📜 Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code:

- **Be respectful** and inclusive
- **Be constructive** in discussions and code reviews
- **Focus on the best** outcome for the community
- **Show empathy** towards other community members

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Node.js 18+ (for dashboard development)
- Git
- Basic knowledge of fantasy football (helpful but not required)

### First Contribution Ideas

Looking for a good first contribution? Check out issues labeled:
- `good-first-issue` - Perfect for newcomers
- `help-wanted` - We'd love community help on these
- `documentation` - Help improve our docs

---

## 🛠️ Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # If available, or:
pip install pytest pytest-asyncio pytest-cov black flake8 mypy
```

### 3. Set Up Configuration

```bash
# Copy example environment
cp env.example .env

# Create test squad file
cp examples/sample_roster.csv my_roster.csv

# Run setup script to verify everything works
python setup.py
```

### 4. Set Up Dashboard (Optional)

If you're contributing to the web dashboard:

```bash
# Navigate to dashboard directory
cd dashboard

# Install Node.js dependencies
npm install

# Export sample data for dashboard
cd ..
python export_squad_only.py

# Start dashboard development server
cd dashboard
npm run dev
# Dashboard will be available at http://localhost:5173/
```

### 5. Verify Installation

```bash
# Run tests
pytest

# Run the application
python main.py
```

---

## 🎯 How to Contribute

### Reporting Bugs

Before creating a bug report:
1. **Search existing issues** to avoid duplicates
2. **Use the latest version** to ensure the bug still exists
3. **Provide detailed information** including:
   - Python version
   - Operating system
   - Error messages/logs
   - Steps to reproduce

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
1. **Check existing issues** for similar suggestions
2. **Provide clear use cases** and benefits
3. **Consider implementation complexity**
4. **Include mockups or examples** if applicable

### Code Contributions

1. **Create an issue** or comment on existing one
2. **Fork the repository**
3. **Create a feature branch**: `git checkout -b feature/amazing-feature`
4. **Make your changes**
5. **Add tests** for new functionality
6. **Update documentation** if needed
7. **Commit with clear messages**
8. **Push to your fork**
9. **Create a Pull Request**

---

## 📚 Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:

```python
# Line length: 100 characters (not 79)
# Use Black for formatting
# Use type hints for all functions

def process_lineup(match: Match, squad: Squad) -> List[Alert]:
    """
    Process lineup and generate alerts.
    
    Args:
        match: The match to process
        squad: User's squad
        
    Returns:
        List of alerts generated
    """
    pass
```

### Code Organization

```python
# Standard library imports
import os
import logging
from typing import List, Optional

# Third-party imports
import pandas as pd
import requests

# Local imports
from .domain.models import Player, Match
from .services.notification_service import NotificationService
```

### Docstring Format

Use Google-style docstrings:

```python
def send_notification(alert: Alert, urgency: AlertUrgency) -> bool:
    """
    Send notification for an alert.
    
    Args:
        alert: The alert to send
        urgency: How urgent the alert is
        
    Returns:
        True if notification sent successfully, False otherwise
        
    Raises:
        NotificationError: If notification fails to send
    """
```

### Error Handling

```python
# Use specific exception types
try:
    result = api_call()
except ConnectionError:
    logger.error("API connection failed")
    raise APIConnectionError("Failed to connect to API")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

---

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/               # Unit tests
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/        # Integration tests
│   ├── test_api.py
│   └── test_notifications.py
└── fixtures/          # Test data
    ├── sample_data.json
    └── mock_responses.py
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch

from src.lineup_tracker.services.lineup_monitoring_service import LineupMonitoringService

class TestLineupMonitoringService:
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_api = Mock()
        self.mock_notifier = Mock()
        self.service = LineupMonitoringService(self.mock_api, self.mock_notifier)
    
    def test_process_lineup_with_benched_player(self):
        """Test processing lineup when expected starter is benched."""
        # Arrange
        expected_starter = create_test_player(name="Salah", status="starter")
        lineup = create_test_lineup(starters=["Other Player"])
        
        # Act
        alerts = self.service.process_lineup(lineup, [expected_starter])
        
        # Assert
        assert len(alerts) == 1
        assert alerts[0].alert_type == "benched_player"
    
    @pytest.mark.asyncio
    async def test_async_notification_sending(self):
        """Test async notification functionality."""
        alert = create_test_alert()
        
        result = await self.service.send_alert(alert)
        
        assert result is True
        self.mock_notifier.send_alert.assert_called_once_with(alert)
```

### Test Categories

- **Unit Tests**: Test individual functions/methods in isolation
- **Integration Tests**: Test interaction between components
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Test system performance under load

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/lineup_tracker

# Run specific test file
pytest tests/unit/test_models.py

# Run tests matching pattern
pytest -k "test_notification"

# Run tests with verbose output
pytest -v
```

---

## 🔄 Pull Request Process

### Before Submitting

1. **Run the full test suite**: `pytest`
2. **Check code formatting**: `black --check src/`
3. **Run linting**: `flake8 src/`
4. **Type checking**: `mypy src/`
5. **Update documentation** if needed

### PR Requirements

- [ ] **Clear description** of what the PR does
- [ ] **Link to related issues** using "Fixes #123" or "Closes #123"
- [ ] **Tests added/updated** for new functionality
- [ ] **Documentation updated** if needed
- [ ] **No breaking changes** without discussion
- [ ] **Clean commit history** (squash if needed)

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows the style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainer(s)
3. **Testing** by reviewers
4. **Final approval** and merge

---

## 🎯 Areas for Contribution

### 🌟 High Priority

- **🐛 Bug Fixes**: Always welcome!
- **📚 Documentation**: Improve setup guides, add examples
- **🧪 Testing**: Increase test coverage
- **🔧 Configuration**: Make setup even easier

### 🚀 New Features

- **🌍 Multi-League Support**: Add La Liga, Serie A, Bundesliga
- **📱 New Notification Providers**: Slack, Telegram, SMS, Push notifications
- **🤖 AI Features**: Lineup predictions, transfer suggestions
- **📊 Analytics**: Player performance tracking, form analysis

### 🎨 Dashboard Features

- **📈 Data Visualization**: Charts, graphs, performance trends
- **🔔 Browser Notifications**: Real-time alerts in the dashboard
- **⚙️ Settings Panel**: Customizable themes, refresh intervals, filters
- **📱 Mobile Improvements**: Enhanced mobile experience, PWA features
- **🎮 Fantasy Integration**: Direct platform connections (FPL, Fantrax)
- **🔄 Real-time Updates**: WebSocket integration for live data
- **🗂️ Data Export**: CSV/PDF exports of player data and analytics

### 🛠️ Infrastructure

- **🐳 Docker Support**: Containerization for easy deployment
- **☁️ Cloud Deployment**: AWS/Azure/GCP deployment guides
- **📈 Monitoring**: Health checks, metrics, alerting
- **🔄 CI/CD**: Automated testing and deployment

### 📱 Platform Support

- **📱 Mobile App**: React Native or Flutter companion app
- **🖥️ Desktop App**: Electron wrapper for desktop users
- **🌐 Browser Extension**: Browser notifications and quick access

---

## 📝 Development Workflow

### Git Workflow

```bash
# Start work on new feature
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Make changes, commit frequently
git add .
git commit -m "Add: specific change description"

# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

### Commit Message Format

```
Type: Brief description (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain what and why, not how.

- Use bullet points if helpful
- Reference issues like "Fixes #123"
```

### Types:
- `Add:` New feature
- `Fix:` Bug fix
- `Update:` Modify existing feature
- `Remove:` Delete feature/code
- `Docs:` Documentation changes
- `Test:` Add or modify tests
- `Refactor:` Code restructuring without functional changes

---

## 🆘 Getting Help

### Resources

- **📖 Documentation**: Start with README.md
- **💬 Discussions**: GitHub Discussions for questions
- **🐛 Issues**: GitHub Issues for bugs and feature requests
- **📧 Email**: Contact maintainers directly for sensitive issues

### Development Help

If you're stuck:

1. **Check existing issues** for similar problems
2. **Search documentation** and code comments
3. **Ask in GitHub Discussions**
4. **Join our Discord** for real-time help
5. **Create an issue** with detailed information

### What to Include When Asking for Help

- **Clear description** of what you're trying to do
- **Error messages** or unexpected behavior
- **Steps to reproduce** the issue
- **Environment details** (OS, Python version, etc.)
- **Code snippets** or relevant configuration

---

## 🏆 Recognition

### Contributors

All contributors will be:
- **Listed in CONTRIBUTORS.md**
- **Credited in release notes**
- **Thanked on social media** for significant contributions

### Types of Contributions

We value all types of contributions:
- 💻 Code contributions
- 📚 Documentation improvements
- 🐛 Bug reports with detailed information
- 💡 Feature ideas and feedback
- 🧪 Testing and quality assurance
- 🎨 Design and user experience improvements
- 🌍 Translations (future feature)

---

## 📄 License

By contributing to LineupTracker, you agree that your contributions will be licensed under the MIT License.

---

<div align="center">

**Thank you for contributing to LineupTracker! 🎉**

Every contribution, no matter how small, helps make fantasy football more enjoyable for everyone.

</div>
