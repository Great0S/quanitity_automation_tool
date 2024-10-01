# E-commerce Integration System

This project is an e-commerce integration system that allows for seamless interaction with multiple e-commerce platforms.

## Features

- Support for multiple e-commerce platforms (N11, Hepsiburada, Amazon, etc.)
- Product synchronization across platforms
- Inventory and price updates
- Asynchronous operations for improved performance

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ecommerce-integration.git
   cd ecommerce-integration
   ```

2. Install Poetry (if not already installed):
   ```
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies:
   ```
   poetry install
   ```

4. Set up environment variables:
   Create a `.env` file in the project root and add your API keys:
   ```
   N11_API_KEY=your_n11_api_key
   HEPSIBURADA_API_KEY=your_hepsiburada_api_key
   # Add other API keys as needed
   ```

## Usage

To run the application:

```
poetry run python app.py
```


## Running Tests

To run the test suite:
```
poetry run pytest
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.