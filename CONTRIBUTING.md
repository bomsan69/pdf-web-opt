# Contributing to PDF Web Optimizer

Thank you for your interest in contributing to PDF Web Optimizer! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming and inclusive community.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/pdf-web-opt/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Docker version, etc.)
   - Relevant logs

### Suggesting Features

1. Check [Issues](https://github.com/yourusername/pdf-web-opt/issues) for existing feature requests
2. Create a new issue with:
   - Clear description of the feature
   - Use cases and benefits
   - Possible implementation approach (optional)

### Submitting Code

1. **Fork the repository**

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the existing code style
   - Add type hints to all functions
   - Add docstrings (Google style) to public functions
   - Update tests if applicable
   - Update documentation if needed

4. **Test your changes**
   ```bash
   # Build and run services
   docker compose up --build -d

   # Check logs
   docker compose logs -f

   # Test the API
   curl http://localhost/health
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: Brief description of your changes"
   ```

   Commit message format:
   - `Add: ` for new features
   - `Fix: ` for bug fixes
   - `Update: ` for updates to existing features
   - `Refactor: ` for code refactoring
   - `Docs: ` for documentation changes

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure all checks pass

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all function parameters and return values
- Add docstrings to all public functions (Google style)
- Keep functions focused and under 50 lines when possible
- Use meaningful variable names

Example:
```python
def process_pdf(job_id: str, dpi: int = 150, jpegq: int = 70) -> dict:
    """
    Optimize a PDF file using Ghostscript.

    Args:
        job_id: Unique job identifier
        dpi: Image resolution (96, 120, or 150)
        jpegq: JPEG quality (40-85 recommended)

    Returns:
        Dict containing job status and output path

    Raises:
        ValueError: If parameters are invalid
        RuntimeError: If processing fails
    """
    # Implementation
```

### Security Considerations

When contributing code:
- Never commit sensitive information (API keys, passwords, etc.)
- Validate all user inputs
- Use parameterized queries/commands to prevent injection
- Follow principle of least privilege
- Add logging for security-relevant events

### Testing

- Test manually with Docker Compose
- Verify health check endpoint works
- Test with various PDF files and sizes
- Check error handling and edge cases
- Review logs for any errors or warnings

### Documentation

Update documentation when you:
- Add new features
- Change API behavior
- Add configuration options
- Fix important bugs

Documentation to update:
- README.md for user-facing changes
- CLAUDE.md for developer guidance
- Code comments for complex logic
- API endpoint docstrings

## Project Structure

```
pdf-web-opt/
├── api/                 # FastAPI service
│   └── app/
│       ├── main.py      # API endpoints
│       ├── settings.py  # Configuration
│       ├── queue.py     # Queue management
│       └── storage.py   # File operations
├── worker/              # RQ worker
│   └── worker.py        # PDF processing logic
├── nginx/               # Nginx config
└── docker-compose.yml   # Service orchestration
```

## Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged

Please be patient - reviews may take a few days.

## Questions?

Feel free to:
- Open an issue for questions
- Start a discussion in the Discussions tab
- Reach out to maintainers

Thank you for contributing! 🎉
