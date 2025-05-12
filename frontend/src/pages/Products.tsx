import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/authService';
import ProductTable from '../components/ProductTable';
import ProductEditModal from '../components/ProductEditModal';
import ImageModal from '../components/ImageModal';
import Pagination from '../components/Pagination';

const ProductsContainer = styled.div`
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
`;

const Title = styled.h1`
  margin: 0;
  color: #0f3460;
`;

const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 200px;
  width: 100%;
  gap: 16px;
`;

const LoadingSpinner = styled.div`
  border: 4px solid #f3f3f3;
  border-top: 4px solid #0f3460;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const LoadingText = styled.div`
  font-size: 16px;
  color: #333;
  text-align: center;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 40px;
  color: #666;
`;

const PaginationContainer = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
`;

const PageSizeSelector = styled.div`
  display: flex;
  align-items: center;
`;

const PageSizeLabel = styled.label`
  margin-right: 10px;
  font-size: 14px;
  color: #666;
`;

const PageSizeSelect = styled.select`
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ddd;
`;

const ActionsContainer = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
`;

const FetchButton = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(15, 52, 96, 0.2);
  
  &:hover {
    background-color: #16213e;
    transform: translateY(-2px);
    box-shadow: 0 6px 8px rgba(15, 52, 96, 0.3);
  }
  
  &:active {
    transform: translateY(0);
    box-shadow: 0 2px 4px rgba(15, 52, 96, 0.2);
  }
  
  &:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  
  svg {
    width: 20px;
    height: 20px;
  }
`;

const DataSourceInfo = styled.div`
  font-size: 14px;
  color: #666;
  font-style: italic;
  background-color: #f9f9f9;
  padding: 8px 12px;
  border-radius: 6px;
  border-left: 4px solid #0f3460;
`;

const SearchContainer = styled.div`
  margin-bottom: 20px;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
  
  &:focus {
    outline: none;
    border-color: #0f3460;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.1);
  }
`;

interface Product {
  sku: string;
  data: {
    title?: string;
    price?: number;
    quantity?: number;
    status?: string;
    image_url?: string;
    [key: string]: any;
  };
  platforms?: string[];
}

interface ProductUpdateData {
  sku: string;
  data?: Record<string, any>;
  platforms?: string[];
}

const Products: React.FC = () => {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [fetchingFromApi, setFetchingFromApi] = useState<boolean>(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [dataSource, setDataSource] = useState<'api' | 'db'>('db');
  const [searchTerm, setSearchTerm] = useState<string>('');
  
  // Fetch products from all platforms
  useEffect(() => {
    fetchAllProducts(false);
  }, []);
  
  // Update filtered products when products or search term changes
  useEffect(() => {
    filterProducts();
  }, [products, searchTerm]);
  
  // Update displayed products when page or pageSize changes
  useEffect(() => {
    updateDisplayedProducts();
  }, [filteredProducts, currentPage, pageSize]);
  
  const fetchAllProducts = async (forceRefresh: boolean = false) => {
    setLoading(true);
    if (forceRefresh) {
      setFetchingFromApi(true);
    }
    
    try {
      // Make the API request
      const response = await api.get('/products/all', { 
        params: { force_refresh: forceRefresh } 
      });
      const taskId = response.data.task_id;
      
      // Poll for task completion
      const checkTask = async () => {
        try {
          const taskResponse = await api.get(`/tasks/${taskId}`);
          
          if (taskResponse.data.status === 'completed') {
            // Get the products from the task result
            const result = taskResponse.data.result || {};
            
            // Update state with the products
            if (result.items && Array.isArray(result.items)) {
              setProducts(result.items);
              setTotalItems(result.total || result.items.length);
              setDataSource(forceRefresh ? 'api' : 'db');
            } else {
              // Handle case where result is directly an array of products
              const productArray = Array.isArray(result) ? result : [];
              setProducts(productArray);
              setTotalItems(productArray.length);
              setDataSource(forceRefresh ? 'api' : 'db');
            }
            
            setLoading(false);
            setFetchingFromApi(false);
          } else if (taskResponse.data.status === 'failed') {
            console.error(`Failed to fetch products: ${taskResponse.data.error}`);
            setLoading(false);
            setFetchingFromApi(false);
          } else {
            // Still running, check again in 2 seconds
            setTimeout(checkTask, 2000);
          }
        } catch (error) {
          console.error('Error checking task status:', error);
          setLoading(false);
          setFetchingFromApi(false);
        }
      };
      
      checkTask();
    } catch (error) {
      console.error('Error fetching products:', error);
      setLoading(false);
      setFetchingFromApi(false);
    }
  };
  
  const filterProducts = () => {
    if (!searchTerm) {
      setFilteredProducts(products);
      return;
    }
    
    const term = searchTerm.toLowerCase();
    const filtered = products.filter(product => {
      const sku = product.sku?.toLowerCase() || '';
      const title = product.data?.title?.toLowerCase() || '';
      const barcode = product.data?.barcode?.toLowerCase() || '';
      
      return sku.includes(term) || 
             title.includes(term) || 
             barcode.includes(term);
    });
    
    setFilteredProducts(filtered);
    setCurrentPage(1); // Reset to first page when filtering
  };
  
  const updateDisplayedProducts = () => {
    // Update total items count
    setTotalItems(filteredProducts.length);
  };
  
  // Handle edit button click
  const handleEditClick = (product: Product) => {
    setSelectedProduct(product);
    setIsEditModalOpen(true);
  };
  
  // Handle image click to enlarge
  const handleImageClick = (imageUrl: string) => {
    setSelectedImage(imageUrl);
  };
  
  // Handle product update
  const handleProductUpdate = async (updatedProduct: ProductUpdateData) => {
    if (!updatedProduct.platforms || updatedProduct.platforms.length === 0) {
      console.error('No platforms specified for update');
      return;
    }
    
    try {
      // Update product across all platforms
      await api.post('/products/update/across-platforms', updatedProduct);
      
      // Update local state
      setProducts(prev => {
        const updatedProducts = [...prev];
        const index = updatedProducts.findIndex(p => p.sku === updatedProduct.sku);
        if (index !== -1) {
          // Create a new product object with updated data
          const newProduct = { ...updatedProducts[index] };
          
          // Update all fields from updatedProduct.data
          if (updatedProduct.data) {
            Object.entries(updatedProduct.data).forEach(([key, value]) => {
              newProduct.data[key] = value;
            });
          }
          
          updatedProducts[index] = newProduct;
        }
        return updatedProducts;
      });
      
      setIsEditModalOpen(false);
      setSelectedProduct(null);
    } catch (error) {
      console.error('Error updating product:', error);
    }
  };
  
  // Handle page change
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };
  
  // Handle page size change
  const handlePageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSize = parseInt(e.target.value);
    setPageSize(newSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };
  
  // Handle fetch from API button click
  const handleFetchFromAPI = () => {
    fetchAllProducts(true);
  };
  
  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };
  
  // Get loading message
  const getLoadingMessage = () => {
    if (fetchingFromApi) {
      return "Fetching products from all platforms...";
    } else {
      return "Loading products from database...";
    }
  };
  
  // Get paginated products
  const getPaginatedProducts = () => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return filteredProducts.slice(start, end);
  };
  
  return (
    <ProductsContainer>
      <Header>
        <Title>Unified Products</Title>
      </Header>
      
      <ActionsContainer>
        {products.length > 0 && (
          <DataSourceInfo>
            Data source: {dataSource === 'api' ? 'API (live data)' : 'Database (cached data)'}
          </DataSourceInfo>
        )}
        <FetchButton 
          onClick={handleFetchFromAPI} 
          disabled={fetchingFromApi}
        >
          {fetchingFromApi ? 'Fetching from API...' : 'Fetch from API'}
          {fetchingFromApi && (
            <LoadingSpinner style={{ width: '20px', height: '20px' }} />
          )}
          {!fetchingFromApi && (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 4V2.21c0-.45-.54-.67-.85-.35l-2.8 2.79c-.2.2-.2.51 0 .71l2.79 2.79c.32.31.86.09.86-.36V6c3.31 0 6 2.69 6 6 0 .79-.15 1.56-.44 2.25-.15.36-.04.77.23 1.04.51.51 1.37.33 1.64-.34.37-.91.57-1.91.57-2.95 0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-.79.15-1.56.44-2.25.15-.36.04-.77-.23-1.04-.51-.51-1.37-.33-1.64.34C4.2 9.96 4 10.96 4 12c0 4.42 3.58 8 8 8v1.79c0 .45.54.67.85.35l2.79-2.79c.2-.2.2-.51 0-.71l-2.79-2.79c-.31-.31-.85-.09-.85.36V18z"/>
            </svg>
          )}
        </FetchButton>
      </ActionsContainer>
      
      <SearchContainer>
        <SearchInput
          type="text"
          placeholder="Search by SKU, title, or barcode..."
          value={searchTerm}
          onChange={handleSearchChange}
        />
      </SearchContainer>
      
      {loading ? (
        <LoadingContainer>
          <LoadingSpinner />
          <LoadingText>{getLoadingMessage()}</LoadingText>
        </LoadingContainer>
      ) : filteredProducts.length > 0 ? (
        <>
          <ProductTable 
            products={getPaginatedProducts()} 
            onEditClick={handleEditClick}
            onImageClick={handleImageClick}
            showPlatforms={true}
          />
          
          <PaginationContainer>
            <PageSizeSelector>
              <PageSizeLabel>Items per page:</PageSizeLabel>
              <PageSizeSelect value={pageSize} onChange={handlePageSizeChange}>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
              </PageSizeSelect>
            </PageSizeSelector>
            
            <Pagination 
              currentPage={currentPage}
              totalItems={totalItems}
              pageSize={pageSize}
              onPageChange={handlePageChange}
            />
          </PaginationContainer>
        </>
      ) : (
        <EmptyState>
          <p>No products found</p>
          <p>Click "Fetch from API" to load products from all platforms.</p>
        </EmptyState>
      )}
      
      {isEditModalOpen && selectedProduct && (
        <ProductEditModal
          product={selectedProduct}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleProductUpdate}
          platforms={selectedProduct.platforms || []}
        />
      )}
      
      {selectedImage && (
        <ImageModal
          imageUrl={selectedImage}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </ProductsContainer>
  );
};

export default Products;