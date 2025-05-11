# Enhanced Quantity Automation Tool

A comprehensive tool for managing product inventory across multiple e-commerce platforms.

## Features

- **Multi-Platform Support**: Manage products across N11, Trendyol, Hepsiburada, and more
- **Real-time Synchronization**: Keep inventory quantities in sync across all platforms
- **Database Persistence**: Store product data and sync history in a local database
- **Background Processing**: Handle long-running operations without blocking the UI
- **Caching**: Improve performance with intelligent caching
- **Error Resilience**: Circuit breaker pattern to prevent cascading failures
- **Enhanced Reporting**: Detailed reports and visualizations
- **Bulk Operations**: Update multiple products at once
- **Modern Architecture**: FastAPI backend with React frontend

## Architecture

The application follows a modern architecture:

- **Backend**: FastAPI-based REST API
- **Frontend**: React with TypeScript
- **Database**: SQLite for data persistence
- **API Layer**: Platform-specific API clients
- **Service Layer**: Business logic and operations
- **Data Layer**: Database access and repositories

## Installation

### Backend

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/quantity_automation_tool.git
   cd quantity_automation_tool
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

4. Create a `.env` file with your API credentials:
   ```
   # N11
   N11_APP_KEY=your_app_key
   N11_APP_SECRET=your_app_secret

   # Trendyol
   TRENDYOL_API_KEY=your_api_key
   TRENDYOL_API_SECRET=your_api_secret

   # Hepsiburada
   HEPSIBURADA_USERNAME=your_username
   HEPSIBURADA_PASSWORD=your_password

   # JWT Secret (for authentication)
   JWT_SECRET_KEY=your_jwt_secret
   ```

5. Start the backend server:
   ```
   uvicorn api_server:app --reload
   ```

### Frontend

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:5173`

## Usage

1. Log in with the default credentials:
   - Username: admin
   - Password: admin

2. Use the sidebar to navigate between different sections:
   - **Dashboard**: Overview of all platforms and key metrics
   - **Products**: View and edit products for each platform
   - **Sync**: Synchronize products between platforms
   - **Tasks**: Monitor background tasks
   - **Settings**: Configure application settings

## Key Components

### Enhanced Product Service

The `EnhancedProductService` extends the basic `ProductService` with:
- Database persistence
- Caching
- Circuit breaker pattern
- Enhanced error handling
- Bulk operations

### Background Task Manager

The `BackgroundTaskManager` allows for:
- Asynchronous processing of long-running tasks
- Progress tracking
- Task cancellation
- Detailed task history

### Database Integration

The application uses SQLite for data persistence:
- Product data
- Platform configurations
- Sync history
- User settings

### Caching System

The caching system improves performance by:
- Caching API responses
- Persisting cache to disk
- Intelligent cache invalidation
- TTL-based expiration

## API Documentation

The API documentation is available at `http://localhost:8000/docs` when the backend server is running.

## Project Structure

```
quantity_automation_tool/
├── api/                  # API clients for each platform
├── core/                 # Core functionality
├── data/                 # Data access layer
│   ├── repositories/     # Data repositories
│   └── database.py       # Database connection
├── frontend/             # React frontend
│   ├── public/           # Static assets
│   └── src/              # React components and logic
├── services/             # Business logic services
├── utils/                # Utility functions
├── tests/                # Tests
├── api_server.py         # FastAPI server
└── requirements.txt      # Python dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.