# Contributing to Apigee Migration Assessment Tooling

First off, thank you for considering contributing to Apigee Migration Assessment Tooling ! We appreciate your time and effort. 

Here's how you can get involved:

## Reporting Bugs

* **Check existing issues:** Before submitting a new bug report, please search the [Issues](link to your project's issues page) to see if the issue has already been reported.
* **Provide detailed information:** When reporting a bug, please include:
    * **Clear and concise description:** Explain the problem you encountered.
    * **Steps to reproduce:** Provide detailed steps to reproduce the bug.
    * **Expected behavior:** Describe what you expected to happen.
    * **Actual behavior:** Describe what actually happened.
    * **Environment details:** Include information about your operating system, Python version, and any relevant dependencies.
    * **Screenshots or code snippets:** If applicable, include screenshots or code snippets to illustrate the issue.

## Suggesting Enhancements

We welcome suggestions for new features or improvements to existing functionality. When suggesting an enhancement:

* **Provide a clear description:** Explain the enhancement you're proposing.
* **Explain the benefits:** Describe how the enhancement would benefit users.
* **Consider alternatives:** If possible, suggest alternative approaches or solutions.

## Submitting Code Changes

We welcome code contributions! Here's how to submit a pull request:

1. **Fork the repository:** Click the "Fork" button in the top right corner of the repository page.
2. **Clone the forked repository:** `git clone https://github.com/your-username/your-forked-repo.git`
3. **Create a new branch:** `git checkout -b my-new-branch`
4. **Make your changes:** Implement your bug fix or enhancement.
5. **Commit your changes:** `git commit -am "Fix: Issue with [issue number]"`
6. **Push to your forked repository:** `git push origin my-new-branch`
7. **Create a pull request:** Go to the original repository and click the "New pull request" button. Select your forked repository and branch.
8. **Provide a detailed description:** Explain the changes you made and why.

## Local Development Setup

This project includes a `Makefile` to streamline common development tasks.

### Prerequisites

- Python 3.12
- `make`

### Installation

To set up your local development environment, run the following command:

```bash
make install
```

This will create a Python virtual environment in `venv/`, and install all the required dependencies from `requirements.txt` and `test-requirements.txt`.

### Running Tests

To run the full suite of unit tests, use the following command:

```bash
make test
```

You can also run specific tests by passing the `TESTS` variable:

```bash
make test TESTS=tests/test_scripts.py
```

### Running the Tool

For instructions on how to run the tool using the `make` commands, please refer to the [MFA Token Generation Instructions](MFA_TOKEN_INSTRUCTIONS.md).

## Code Style

* **Follow PEP 8:** Adhere to the [PEP 8 style guide](https://www.python.org/dev/peps/pep-0008/) for Python code.
* **Use meaningful names:** Choose descriptive names for variables, functions, and classes.
* **Write clear comments:** Explain the purpose and functionality of your code.
* **Keep functions short:** Break down complex tasks into smaller, more manageable functions.

## Testing

* **Write unit tests:** Ensure your code changes are well-tested by writing unit tests.
* **Run existing tests:** Before submitting a pull request, make sure all existing tests pass.

## Code of Conduct

We expect all contributors to adhere to our [Code of Conduct](link to your project's code of conduct). Please treat everyone with respect and courtesy.

## Questions

If you have any questions or need help getting started, feel free to [open an issue](link to your project's issues page) or contact us.

Thank you for your contributions!