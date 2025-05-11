// @ts-nocheck - Disable TypeScript checking for this file due to complex react-table typing issues
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { toast } from 'react-toastify';
import api from '../services/authService';
import { 
  useTable, 
  usePagination, 
  useSortBy, 
  useFilters,
  Column,
  TableInstance,
  UsePaginationInstanceProps,
  UseSortByInstanceProps,
  UseFiltersInstanceProps,
  Row
} from 'react-table';
import { TASK_REFRESH_INTERVAL } from '../config';

// Define the data type for our table
interface ProductData {
  sku: string;
  title: string;
  price: number;
  quantity: number;
  status: string;
}

const ProductsContainer = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
`;

const Title = styled.h2`
  margin: 0;
`;

const Button = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #16213e;
  }
  
  &:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
  }
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  
  th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #eee;
  }
  
  th {
    background-color: #f9f9f9;
    font-weight: 500;
  }
  
  tr:hover {
    background-color: #f5f5f5;
  }
`;

const Pagination = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
`;

const PageInfo = styled.span`
  color: #666;
`;

const PageButtons = styled.div`
  display: flex;
  gap: 5px;
`;

// Fixed isActive prop warning by using $isActive (transient prop)
const PageButton = styled.button<{ $isActive?: boolean }>`
  background-color: ${props => props.$isActive ? '#0f3460' : 'white'};
  color: ${props => props.$isActive ? 'white' : '#333'};
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 5px 10px;
  cursor: pointer;
  
  &:hover {
    background-color: ${props => props.$isActive ? '#0f3460' : '#f5f5f5'};
  }
  
  &:disabled {
    background-color: #f9f9f9;
    color: #ccc;
    cursor: not-allowed;
  }
`;

const FilterInput = styled.input`
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-right: 10px;
  width: 200px;
`;

const LoadingOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10;
`;

const LoadingSpinner = styled.div`
  border: 4px solid #f3f3f3;
  border-top: 4px solid #0f3460;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const EditableCell = styled.div`
  padding: 0;
  
  input {
    width: 100%;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
  }
`;

// Fixed status prop warning by using $status (transient prop)
const StatusBadge = styled.span<{ $status: string }>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  
  ${props => {
    switch (props.$status.toLowerCase()) {
      case 'active':
        return 'background-color: #e8f5e9; color: #2e7d32;';
      case 'inactive':
        return 'background-color: #ffebee; color: #c62828;';
      case 'draft':
        return 'background-color: #e3f2fd; color: #1565c0;';
      default:
        return 'background-color: #f5f5f5; color: #616161;';
    }
  }}
`;

// Define a default UI for filtering
function DefaultColumnFilter({
  column: { filterValue, setFilter },
}: {
  column: {
    filterValue: string | undefined;
    preFilteredRows: any[];
    setFilter: (filterValue: string | undefined) => void;
  };
}) {
  return (
    <FilterInput
      value={filterValue || ''}
      onChange={e => {
        setFilter(e.target.value || undefined);
      }}
      placeholder="Search..."
    />
  );
}

// Define the table instance type with all the hooks
type TableInstanceWithHooks = 
  TableInstance<ProductData> & 
  UsePaginationInstanceProps<ProductData> & 
  UseSortByInstanceProps<ProductData> & 
  UseFiltersInstanceProps<ProductData>;

// Define the table state type with pagination properties
interface TableState extends Record<string, any> {
  pageIndex: number;
  pageSize: number;
}

const Products: React.FC = () => {
  const { platform } = useParams<{ platform: string }>();
  const navigate = useNavigate();
  
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchingTask, setFetchingTask] = useState<string | null>(null);
  const [taskProgress, setTaskProgress] = useState(0);
  const [changedProducts, setChangedProducts] = useState<any[]>([]);
  const [savingChanges, setSavingChanges] = useState(false);
  
  // Use a ref to track the current platform
  const currentPlatform = useRef<string | null>(null);
  // Use a ref to track if a fetch is in progress
  const fetchInProgress = useRef<boolean>(false);
  
  // Effect to handle platform changes
  useEffect(() => {
    if (platform && platform !== currentPlatform.current) {
      console.log(`Platform changed from ${currentPlatform.current} to ${platform}`);
      currentPlatform.current = platform;
      
      // Reset state for new platform
      setProducts([]);
      setFetchingTask(null);
      setLoading(true);
      setChangedProducts([]);
      
      // Prevent duplicate API calls by using a flag
      fetchInProgress.current = false;
    }
  }, [platform]);
  
  // Fetch products or check task status
  useEffect(() => {
    // Skip if no platform
    if (!platform) return;
    
    const fetchProducts = async () => {
      try {
        if (fetchingTask) {
          // Check task status
          console.log(`Checking task status for ${fetchingTask}`);
          const taskResponse = await api.get(`/tasks/${fetchingTask}`);
          const task = taskResponse.data;
          
          if (task.status === 'completed') {
            // Task completed, get the result
            console.log(`Task completed with ${task.result?.length || 0} products`);
            setProducts(task.result || []);
            setFetchingTask(null);
            setTaskProgress(100);
            setLoading(false);
            toast.success(`Successfully loaded ${task.result?.length || 0} products from ${platform}`);
          } else if (task.status === 'failed') {
            // Task failed
            console.log(`Task failed: ${task.error}`);
            setFetchingTask(null);
            setLoading(false);
            toast.error(`Failed to load products: ${task.error}`);
          } else {
            // Task still running
            console.log(`Task in progress: ${task.progress * 100}%`);
            setTaskProgress(task.progress ? task.progress * 100 : 0);
          }
        } else if (loading && !fetchInProgress.current) {
          // Start a new task
          fetchInProgress.current = true;
          console.log(`Starting new task to fetch products from ${platform}`);
          try {
            const response = await api.get(`/products/${platform}`);
            console.log(`Task created: ${response.data.task_id}`);
            setFetchingTask(response.data.task_id);
          } catch (err) {
            console.error('Error starting product fetch:', err);
            setLoading(false);
            toast.error('Failed to start product fetch');
          } finally {
            fetchInProgress.current = false;
          }
        }
      } catch (err) {
        console.error('Error fetching products:', err);
        setFetchingTask(null);
        setLoading(false);
        toast.error('Failed to load products');
        fetchInProgress.current = false;
      }
    };
    
    // Run fetchProducts immediately
    fetchProducts();
    
    // Set up polling interval if we're waiting for a task
    let interval: ReturnType<typeof setInterval> | null = null;
    if (fetchingTask) {
      interval = setInterval(fetchProducts, TASK_REFRESH_INTERVAL);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [platform, fetchingTask, loading]);
  
  // Handle product changes
  const handleProductChange = (index: number, field: string, value: any) => {
    const updatedProducts = [...products];
    updatedProducts[index].data[field] = value;
    setProducts(updatedProducts);
    
    // Track changed products
    const sku = updatedProducts[index].sku;
    const existingChangeIndex = changedProducts.findIndex(p => p.sku === sku);
    
    if (existingChangeIndex >= 0) {
      // Update existing change
      const updatedChanges = [...changedProducts];
      updatedChanges[existingChangeIndex] = {
        ...updatedChanges[existingChangeIndex],
        [field]: value
      };
      setChangedProducts(updatedChanges);
    } else {
      // Add new change
      setChangedProducts([...changedProducts, { sku, [field]: value }]);
    }
  };
  
  // Save changes
  const saveChanges = async () => {
    if (changedProducts.length === 0) {
      toast.info('No changes to save');
      return;
    }
    
    try {
      setSavingChanges(true);
      
      // Format changes for API
      const updates = changedProducts.map(product => ({
        sku: product.sku,
        price: product.price,
        quantity: product.quantity,
        status: product.status
      }));
      
      // Send update request
      const response = await api.post(`/products/${platform}`, updates);
      const taskId = response.data.task_id;
      
      toast.info('Changes are being processed...');
      
      // Poll for task completion with exponential backoff
      const checkTask = async (attempt = 0) => {
        try {
          const taskResponse = await api.get(`/tasks/${taskId}`);
          const task = taskResponse.data;
          
          if (task.status === 'completed') {
            toast.success('Changes saved successfully');
            setChangedProducts([]);
            
            // Refresh products
            fetchInProgress.current = false;
            setFetchingTask(null);
            setLoading(true);
          } else if (task.status === 'failed') {
            toast.error(`Failed to save changes: ${task.error}`);
          } else {
            // Still processing - use exponential backoff
            const backoffTime = Math.min(TASK_REFRESH_INTERVAL * Math.pow(1.5, attempt), 15000); // Max 15 seconds
            setTimeout(() => checkTask(attempt + 1), backoffTime);
          }
        } catch (err) {
          console.error('Error checking task status:', err);
          toast.error('Failed to check task status');
        }
      };
      
      setTimeout(checkTask, TASK_REFRESH_INTERVAL);
    } catch (err) {
      console.error('Error saving changes:', err);
      toast.error('Failed to save changes');
    } finally {
      setSavingChanges(false);
    }
  };
  
  // Prepare table data
  const data = useMemo<ProductData[]>(() => 
    products.map(product => ({
      sku: product.sku,
      title: product.data?.title || '',
      price: product.data?.price || 0,
      quantity: product.data?.quantity || 0,
      status: product.data?.status || 'inactive'
    })),
    [products]
  );
  
  const columns = useMemo<Column<ProductData>[]>(() => [
    {
      Header: 'SKU',
      accessor: 'sku',
    },
    {
      Header: 'Title',
      accessor: 'title',
    },
    {
      Header: 'Price',
      accessor: 'price',
      Cell: ({ row, value }: { row: Row<ProductData>; value: number }) => (
        <EditableCell>
          <input
            type="number"
            value={value}
            onChange={e => handleProductChange(row.index, 'price', parseFloat(e.target.value))}
            step="0.01"
            min="0"
          />
        </EditableCell>
      )
    },
    {
      Header: 'Quantity',
      accessor: 'quantity',
      Cell: ({ row, value }: { row: Row<ProductData>; value: number }) => (
        <EditableCell>
          <input
            type="number"
            value={value}
            onChange={e => handleProductChange(row.index, 'quantity', parseInt(e.target.value))}
            step="1"
            min="0"
          />
        </EditableCell>
      )
    },
    {
      Header: 'Status',
      accessor: 'status',
      Cell: ({ value }: { value: string }) => (
        // Fixed status prop warning by using $status instead of status
        <StatusBadge $status={value}>{value}</StatusBadge>
      )
    }
  ], []);
  
  const defaultColumn = useMemo(
    () => ({
      // Let's set up our default Filter UI
      Filter: DefaultColumnFilter as unknown as React.ComponentType<any>
    }),
    []
  );
  
  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    prepareRow,
    page,
    canPreviousPage,
    canNextPage,
    pageOptions,
    pageCount,
    gotoPage,
    nextPage,
    previousPage,
    state
  } = useTable(
    {
      columns,
      data,
      defaultColumn,
      initialState: { pageIndex: 0, pageSize: 20 } as any
    },
    useFilters,
    useSortBy,
    usePagination
  ) as TableInstanceWithHooks;
  
  // Extract pagination state
  const { pageIndex } = state as TableState;
  
  if (!platform) {
    return <div>No platform selected</div>;
  }
  
  return (
    <ProductsContainer>
      <Header>
        <Title>{platform} Products</Title>
        <div>
          <Button 
            onClick={() => {
              // Prevent rapid successive refreshes
              if (loading || fetchingTask) return;
              
              // Reset fetch state
              fetchInProgress.current = false;
              setFetchingTask(null);
              setLoading(true);
            }}
            disabled={loading || !!fetchingTask}
            style={{ marginRight: '10px' }}
          >
            Refresh
          </Button>
          <Button 
            onClick={saveChanges}
            disabled={changedProducts.length === 0 || savingChanges}
          >
            {savingChanges ? 'Saving...' : ('Save Changes (' + changedProducts.length + ')')}
          </Button>
        </div>
      </Header>
      
      {loading && (
        <LoadingOverlay>
          <div>
            <LoadingSpinner />
            <div style={{ marginTop: '10px' }}>
              {fetchingTask ? ('Loading products... ' + taskProgress.toFixed(0) + '%') : 'Loading...'}
            </div>
          </div>
        </LoadingOverlay>
      )}
      
      <div style={{ position: 'relative' }}>
        <Table {...getTableProps()}>
          <thead>
            {headerGroups.map(headerGroup => {
              const { key, ...headerGroupProps } = headerGroup.getHeaderGroupProps();
              return (
                <tr key={headerGroup.id} {...headerGroupProps}>
                  {headerGroup.headers.map(column => {
                    const sortByProps = (column as any).getSortByToggleProps ? 
                      (column as any).getSortByToggleProps() : {};
                    const { key: columnKey, ...columnProps } = column.getHeaderProps(sortByProps);
                    
                    return (
                      <th key={column.id} {...columnProps}>
                        {column.render('Header')}
                        <span>
                          {(column as any).isSorted
                            ? (column as any).isSortedDesc
                              ? ' 🔽'
                              : ' 🔼'
                            : ''}
                        </span>
                        <div>{(column as any).canFilter ? column.render('Filter') : null}</div>
                      </th>
                    );
                  })}
                </tr>
              );
            })}
          </thead>
          <tbody {...getTableBodyProps()}>
            {page.map(row => {
              prepareRow(row);
              const { key: rowKey, ...rowProps } = row.getRowProps();
              return (
                <tr key={row.id} {...rowProps}>
                  {row.cells.map(cell => {
                    const { key: cellKey, ...cellProps } = cell.getCellProps();
                    return (
                      <td key={cell.id} {...cellProps}>{cell.render('Cell')}</td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </Table>
        
        <Pagination>
          <PageInfo>
            Page{' '}
            <strong>
              {pageIndex + 1} of {pageOptions.length}
            </strong>{' '}
            | Showing {page.length} of {data.length} products
          </PageInfo>
          <PageButtons>
            <PageButton onClick={() => gotoPage(0)} disabled={!canPreviousPage}>
              {'<<'}
            </PageButton>
            <PageButton onClick={() => previousPage()} disabled={!canPreviousPage}>
              {'<'}
            </PageButton>
            <PageButton onClick={() => nextPage()} disabled={!canNextPage}>
              {'>'}
            </PageButton>
            <PageButton onClick={() => gotoPage(pageCount - 1)} disabled={!canNextPage}>
              {'>>'}
            </PageButton>
          </PageButtons>
        </Pagination>
      </div>
    </ProductsContainer>
  );
};

export default Products;