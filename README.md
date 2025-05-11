# E-commerce Integration System

This project is an e-commerce integration system that allows for seamless interaction with multiple e-commerce platforms.

## Features

- Support for multiple e-commerce platforms (N11, Hepsiburada, Amazon, etc.)
- Product synchronization across platforms
- Inventory and price updates
- Asynchronous operations for improved performance
- Streamlit-based user interface

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ecommerce-integration.git
   cd ecommerce-integration
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Copy the `.env.example` file to `.env` and fill in your API keys:
   ```
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

## Configuration

The application uses environment variables for configuration. The following variables are required:

### Authentication
- `JWT_SECRET_KEY`: Secret key for JWT token generation (for simple auth)

### WordPress/WooCommerce
- `WP_SITE_URL`: Your WordPress site URL
- `WC_CONSUMER_KEY`: WooCommerce consumer key
- `WC_CONSUMER_SECRET`: WooCommerce consumer secret

### Other Platforms
- See the `.env` file for all required API keys for each platform

## Usage

To run the application:

```
streamlit run app.py
```

The default login credentials are:
- Username: admin
- Password: admin

## Project Structure

```
quanitity_automation_tool/
├── api/                  # API clients for different platforms
├── auth/                 # Authentication modules
├── config/               # Configuration files
├── core/                 # Core functionality
├── logs/                 # Log files
├── pages/                # Streamlit pages
├── services/             # Business logic services
├── tests/                # Test files
├── ui/                   # UI components
├── utils/                # Utility functions
├── .env                  # Environment variables
├── app.py                # Main application file
├── main.py               # Entry point
└── requirements.txt      # Dependencies
```

## Running Tests

To run the test suite:
```
pytest
```

## Troubleshooting

### Authentication Issues
If you encounter authentication errors:
1. Check that your API credentials are correctly set in the `.env` file
2. For simple authentication, make sure `JWT_SECRET_KEY` is set
3. For AWS Cognito authentication, uncomment and set the Cognito variables in `.env`

### API Connection Issues
1. Verify your internet connection
2. Check that the API endpoints are accessible
3. Verify that your API credentials have the necessary permissions

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.